import json
import time
import re
from groq import Groq
from app.config import get_settings
from app.schemas import EvaluationResult

settings = get_settings()
groq_client = Groq(api_key=settings.GROQ_API_KEY)


# ---------------------------------------------------------------------------
# Campaign-Specific Extraction Rules
# ---------------------------------------------------------------------------

CAMPAIGN_EXTRACTION_RULES = {
    "sales": {
        "description": "This is a SALES call. Extract all deal-related outcomes.",
        "fields": {
            "sale_closed": "boolean — Whether a sale was successfully closed",
            "deal_value": "float — Monetary value of the deal discussed (0.0 if none)",
            "objections_raised": "integer — Number of customer objections raised",
            "objections_handled": "integer — Number of objections successfully handled by the agent",
            "upsell_attempted": "boolean — Whether the agent attempted an upsell or cross-sell",
        },
        "primary_outcome_hint": "Set primary_outcome to 'Sale Closed', 'Sale Lost', or 'Follow-Up Required'.",
        "example": """{
  "primary_outcome": "Sale Closed",
  "outcome_value": 1500.00,
  "follow_up_required": false,
  "follow_up_date": null,
  "campaign_specific_data": {
    "sale_closed": true,
    "deal_value": 1500.00,
    "objections_raised": 1,
    "objections_handled": 1,
    "upsell_attempted": false
  }
}"""
    },
    "customer_service": {
        "description": "This is a CUSTOMER SERVICE call. Extract service resolution outcomes.",
        "fields": {
            "issue_resolved": "boolean — Whether the customer's issue was fully resolved",
            "resolution_type": "string — e.g. 'Refund', 'Replacement', 'Troubleshooting', 'Information'",
            "escalated": "boolean — Whether the call was escalated to a supervisor or another department",
            "customer_satisfaction": "integer 1-5 — Estimated satisfaction level of the customer",
            "repeat_call": "boolean — Whether the customer indicated this is a repeat call for the same issue",
        },
        "primary_outcome_hint": "Set primary_outcome to 'Resolved', 'Escalated', or 'Unresolved'.",
        "example": """{
  "primary_outcome": "Resolved",
  "outcome_value": 0.0,
  "follow_up_required": false,
  "follow_up_date": null,
  "campaign_specific_data": {
    "issue_resolved": true,
    "resolution_type": "Refund",
    "escalated": false,
    "customer_satisfaction": 4,
    "repeat_call": false
  }
}"""
    },
    "collections": {
        "description": "This is a COLLECTIONS call. Extract payment arrangement outcomes.",
        "fields": {
            "promise_to_pay": "boolean — Whether the customer made a promise to pay",
            "promise_amount": "float — Amount the customer promised to pay (0.0 if none)",
            "promise_date": "string — Date the customer promised to pay (ISO format or empty string)",
            "payment_arrangement": "boolean — Whether a formal payment arrangement was established",
            "customer_tone_start": "string — Customer's emotional tone at the start (e.g. 'angry', 'neutral', 'cooperative')",
            "customer_tone_end": "string — Customer's emotional tone at the end of the call",
        },
        "primary_outcome_hint": "Set primary_outcome to 'Promise to Pay', 'Payment Arranged', 'Refused', or 'Callback Scheduled'.",
        "example": """{
  "primary_outcome": "Promise to Pay",
  "outcome_value": 500.00,
  "follow_up_required": true,
  "follow_up_date": "2026-05-10T00:00:00Z",
  "campaign_specific_data": {
    "promise_to_pay": true,
    "promise_amount": 500.00,
    "promise_date": "2026-05-10T00:00:00Z",
    "payment_arrangement": true,
    "customer_tone_start": "angry",
    "customer_tone_end": "cooperative"
  }
}"""
    },
    "technical": {
        "description": "This is a TECHNICAL SUPPORT call. Extract technical resolution data.",
        "fields": {
            "ticket_id": "string — Support ticket ID if mentioned (empty string if none)",
            "technical_resolved": "boolean — Whether the technical issue was resolved during the call",
            "resolution_steps": "integer — Number of troubleshooting steps attempted",
            "escalated_to_tier2": "boolean — Whether the issue was escalated to Tier 2 support",
            "workaround_provided": "boolean — Whether a temporary workaround was provided",
        },
        "primary_outcome_hint": "Set primary_outcome to 'Resolved', 'Workaround Provided', 'Escalated to Tier 2', or 'Unresolved'.",
        "example": """{
  "primary_outcome": "Resolved",
  "outcome_value": 0.0,
  "follow_up_required": false,
  "follow_up_date": null,
  "campaign_specific_data": {
    "ticket_id": "TICKET-123",
    "technical_resolved": true,
    "resolution_steps": 3,
    "escalated_to_tier2": false,
    "workaround_provided": false
  }
}"""
    },
}


def _build_campaign_outcome_prompt(campaign_type: str) -> str:
    """Build the campaign-specific outcome extraction section for the LLM prompt."""
    rules = CAMPAIGN_EXTRACTION_RULES.get(campaign_type)
    if not rules:
        return ""

    fields_block = "\n".join(
        f'      "{k}": {v}' for k, v in rules["fields"].items()
    )

    return f"""

### BUSINESS OUTCOME EXTRACTION:
{rules["description"]}
{rules["primary_outcome_hint"]}

You MUST also populate the following fields inside the "campaign_specific_data" JSON object:
{{
{fields_block}
}}

Additionally, populate these top-level outcome fields:
- "primary_outcome": string (the main business result of this call)
- "outcome_value": float or null (monetary/numeric value if applicable)
- "follow_up_required": boolean (whether the agent needs to follow up)
- "follow_up_date": string or null (suggested follow-up date in ISO format if applicable)

### EXAMPLE OUTCOME JSON (Do not copy blindly, adapt to actual transcript):
{rules["example"]}
"""


def evaluate_transcript(transcript: str, campaign_prompt: str, campaign_type: str = "customer_service") -> EvaluationResult:
    """
    Sends the transcript and the campaign-specific prompt to Groq.
    Forces JSON output adhering to the EvaluationResult schema.
    Dynamically injects campaign-type-specific extraction rules.
    """
    
    # Build dynamic outcome extraction block
    outcome_extraction = _build_campaign_outcome_prompt(campaign_type)
    
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
{outcome_extraction}
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
  "summary": string (A clear, objective 3-sentence summary of the call outcome),
  "qa_pairs": [
    {{
      "objection": string (The customer objection or critical question),
      "response": string (The agent's response),
      "customer_emotion_at": string (Emotion during objection),
      "customer_emotion_after": string (Emotion after response),
      "is_golden": boolean (Ideal response?)
    }}
  ],
  "opening_ok": boolean (Used correct opening script?),
  "closing_ok": boolean (Used correct closing script?),
  "dob_verified": boolean (Was DOB verified?),
  "primary_outcome": string or null (Main business outcome of the call),
  "outcome_value": float or null (Monetary/numeric value of the outcome),
  "follow_up_required": boolean (Whether follow-up is needed),
  "follow_up_date": string or null (ISO date if follow-up is needed),
  "campaign_specific_data": object or null (Campaign-type-specific extracted fields as described above)
}}

### JSON VALIDATION CHECKLIST:
- Ensure `primary_outcome` is a string.
- Ensure `outcome_value` is a float.
- Ensure all keys inside `campaign_specific_data` precisely match the requested schema fields.
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

def assign_speakers(segments: list, agent_name: str = None) -> dict:
    """
    Implements a keyword-based heuristic to correctly assign roles (Agent vs Customer).
    Analyzes the first 10 segments of the transcript with weighted scoring for early segments.
    """
    # Dynamic Agent Keywords
    agent_keywords = [
        "citizens debt relief", "how can i help", "calling from", 
        "thank you for calling", "extension", "support", "transferring",
        "this call is recorded", "for quality assurance"
    ]
    
    if agent_name:
        agent_name_lower = agent_name.lower()
        agent_keywords.append(f"this is {agent_name_lower}")
        agent_keywords.append(f"i am {agent_name_lower}")
        # Add first name if it's multiple words
        parts = agent_name_lower.split()
        if len(parts) > 1:
            agent_keywords.append(f"this is {parts[0]}")
            agent_keywords.append(f"my name is {parts[0]}")

    customer_keywords = [
        "i have an account", "my name is", "inquiry", "checking status",
        "my account", "refund", "summons", "calling because", 
        "disgusted", "close my account", "my money", "payment"
    ]

    scores = {} # {speaker_id: {"agent": score, "customer": score, "first_seen": timestamp}}

    # Analyze first 10 segments
    for idx, seg in enumerate(segments[:10]):
        speaker = seg.get("speaker", "UNKNOWN")
        if speaker == "UNKNOWN":
            continue
            
        text = seg.get("text", "").lower()
        start_time = float(seg.get("start", 0.0))
        
        if speaker not in scores:
            scores[speaker] = {"agent": 0, "customer": 0, "first_seen": start_time}
            
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
    max_agent_score = -1.0

    print(f"[*] Speaker Identity Scores: {scores}")

    for speaker, s in scores.items():
        # Agent probability score
        agent_prob = s["agent"] - (s["customer"] * 0.5)
        
        if agent_prob > max_agent_score:
            max_agent_score = agent_prob
            best_agent_speaker = speaker
        elif agent_prob == max_agent_score and best_agent_speaker is not None:
            # Tie breaker 1: lower customer score
            if s["customer"] < scores[best_agent_speaker]["customer"]:
                best_agent_speaker = speaker
            # Tie breaker 2: who spoke first? (99% agent starts)
            elif s["first_seen"] < scores[best_agent_speaker]["first_seen"]:
                best_agent_speaker = speaker

    # Fallback: If no clear agent found by keywords, pick the speaker who started first
    if best_agent_speaker is None or max_agent_score <= 0:
        sorted_speakers = sorted(
            [{"id": k, "time": v["first_seen"]} for k, v in scores.items()],
            key=lambda x: x["time"]
        )
        if sorted_speakers:
            best_agent_speaker = sorted_speakers[0]["id"]
            print(f"[*] Fallback: Assigning first speaker ({best_agent_speaker}) as Agent.")

    # Map roles - ensure ALL unique speakers in the call are mapped
    speaker_map = {}
    for seg in segments:
        speaker = seg.get("speaker")
        if speaker and speaker != "UNKNOWN" and speaker not in speaker_map:
            if speaker == best_agent_speaker:
                speaker_map[speaker] = "Agent"
            else:
                speaker_map[speaker] = "Customer"

    print(f"[*] Final Speaker Map: {speaker_map}")
    return speaker_map
