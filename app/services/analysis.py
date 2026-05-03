import json
import time
import re
from groq import Groq
from app.config import get_settings
from app.schemas import EvaluationResult

settings = get_settings()
groq_client = Groq(api_key=settings.GROQ_API_KEY)

def evaluate_transcript(transcript: str, campaign_prompt: str) -> EvaluationResult:
    """
    Sends the transcript and the campaign-specific prompt to Groq.
    Forces JSON output adhering to the EvaluationResult schema.
    Includes robust parsing logic for Summary and Reasoning.
    """
    
    system_message = f"""You are an Expert Quality Assurance (QA) Manager. 
Your task is to evaluate a customer service call transcript between an Agent and a Customer based on the specific campaign rules provided below.

### EVALUATION GOAL:
Provide a balanced and objective assessment. You MUST identify both areas of excellence and areas for improvement.

### CAMPAIGN SPECIFIC RULES:
{campaign_prompt}

### BEHAVIOR CATEGORIZATION:
1. **Strengths**: At least 3 positive behaviors where the agent excelled or followed best practices (e.g., "Effective issue resolution", "Polite tone", "Active Listening", "Clear Greeting").
2. **Weaknesses**: Areas for improvement and critical failures with associated deductions based on the rubric.

### SANITIZED SUMMARY:
Provide a clear, objective 3-sentence summary of the call outcome, avoiding technical jargon or internal notes.

### OUTPUT FORMAT:
You MUST output ONLY valid JSON that conforms to the following schema structure. 
You MUST write the "reasoning" field FIRST before calculating the "score" to ensure logical consistency.

Schema:
{{
  "reasoning": string (Think step-by-step here. Analyze the call based on the rules, justify the deductions, and list your findings BEFORE giving the numerical score),
  "score": float (Overall call score from 0 to 100),
  "strengths": [string] (List of 2-4 positive behaviors found in the call),
  "weaknesses": [
    {{
      "issue": string (Short category label from the rules above),
      "detail": string (Explanation of what was wrong),
      "deduction": float (Points deducted for this weakness)
    }}
  ],
  "summary": string (A clear, objective 3-sentence summary of the call outcome)
}}
"""

    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Here is the transcript:\n\n{transcript}"}
                ],
                temperature=0.0, 
                top_p=1.0,
                seed=42,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            result_dict = json.loads(result_text)
            
            # --- Robust Parsing Logic ---
            # Extract reasoning and summary if they are merged or mislabeled
            reasoning = result_dict.get("reasoning", "")
            summary = result_dict.get("summary", "")

            # Regex patterns to find Summary and Reasoning sections
            summary_pattern = re.compile(r"(?:^|\n)(?:Summary|Assessment|Overall):\s*(.*)", re.IGNORECASE | re.DOTALL)
            reasoning_pattern = re.compile(r"(?:^|\n)(?:Reasoning|Logic|Analysis):\s*(.*)", re.IGNORECASE | re.DOTALL)

            # If summary is missing or too short, check reasoning
            if not summary or len(summary) < 20:
                summary_match = summary_pattern.search(reasoning)
                if summary_match:
                    summary = summary_match.group(1).split("\n\n")[0].strip()
                    # Clean up reasoning by removing the summary part
                    reasoning = summary_pattern.sub("", reasoning).strip()

            # If reasoning is missing, check summary
            if not reasoning:
                reasoning_match = reasoning_pattern.search(summary)
                if reasoning_match:
                    reasoning = reasoning_match.group(1).strip()
                    summary = reasoning_pattern.sub("", summary).strip()

            result_dict["reasoning"] = reasoning
            result_dict["summary"] = summary

            validated_result = EvaluationResult(**result_dict)
            
            # Manual Score Calculation
            total_deductions = sum(w.deduction for w in validated_result.weaknesses)
            calculated_score = max(0.0, 100.0 - total_deductions)
            validated_result.score = calculated_score
            
            return validated_result
            
        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower() and attempt < max_retries - 1:
                print(f"[!] Rate limit hit, retrying in {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2 
                continue
                
            print(f"[!] Groq error: {e}")
            raise ValueError(f"Failed to process evaluation: {str(e)}") from e

def assign_speakers(segments: list) -> dict:
    """
    Implements a keyword-based heuristic to correctly assign roles (Agent vs Customer).
    Analyzes the first 10 segments of the transcript with weighted scoring for early segments.
    """
    agent_keywords = [
        "citizens debt relief", "how can i help", "this is david", 
        "extension", "support", "transferring", "my name is", "this is",
        "this call is recorded", "for quality assurance"
    ]
    customer_keywords = [
        "my account", "refund", "summons", "calling because", 
        "disgusted", "close my account", "my money", "payment"
    ]

    scores = {} # {speaker_id: {"agent": score, "customer": score}}

    # Analyze first 10 segments
    for idx, seg in enumerate(segments[:10]):
        speaker = seg.get("speaker", "UNKNOWN")
        text = seg.get("text", "").lower()
        
        if speaker not in scores:
            scores[speaker] = {"agent": 0, "customer": 0}
            
        # Weighted scoring: earlier segments are more likely to contain introductions
        # First 3 segments get 2x weight for "Agent" keywords
        weight = 2.0 if idx < 3 else 1.0
        
        for kw in agent_keywords:
            if kw in text:
                scores[speaker]["agent"] += (1 * weight)
        
        for kw in customer_keywords:
            if kw in text:
                scores[speaker]["customer"] += 1

    # Determine which speaker is most likely the agent
    best_agent_speaker = None
    max_agent_score = -1

    print(f"[*] Speaker Identity Scores: {scores}")

    for speaker, s in scores.items():
        if speaker == "UNKNOWN":
            continue
            
        # Agent score must be higher than customer score for that speaker to be an agent candidate
        agent_prob = s["agent"] - (s["customer"] * 0.5)
        
        if agent_prob > max_agent_score:
            max_agent_score = agent_prob
            best_agent_speaker = speaker
        elif agent_prob == max_agent_score and best_agent_speaker is not None:
            # Tie breaker: if one has lower customer score, it's more likely the agent
            if s["customer"] < scores[best_agent_speaker]["customer"]:
                best_agent_speaker = speaker

    # If we couldn't decide or no clear agent found, default to SPEAKER_00
    if best_agent_speaker is None or max_agent_score <= 0:
        if any(s.get("speaker") == "SPEAKER_00" for s in segments):
            best_agent_speaker = "SPEAKER_00"
        elif segments:
            # Just pick the first speaker who isn't UNKNOWN
            for s in segments:
                if s.get("speaker") and s.get("speaker") != "UNKNOWN":
                    best_agent_speaker = s.get("speaker")
                    break

    # Map roles
    speaker_map = {}
    for seg in segments:
        speaker = seg.get("speaker")
        if speaker and speaker not in speaker_map:
            if speaker == best_agent_speaker:
                speaker_map[speaker] = "Agent"
            else:
                speaker_map[speaker] = "Customer"

    print(f"[*] Final Speaker Map: {speaker_map}")
    return speaker_map
