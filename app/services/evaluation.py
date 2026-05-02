import json
import time
from groq import Groq
from app.config import get_settings
from app.schemas import EvaluationResult

settings = get_settings()
groq_client = Groq(api_key=settings.GROQ_API_KEY)

def evaluate_transcript(transcript: str, campaign_prompt: str) -> EvaluationResult:
    """
    Sends the transcript and the campaign-specific prompt to Groq.
    Forces JSON output adhering to the EvaluationResult schema.
    """
    
    # We define a strict system prompt that incorporates the dynamic campaign prompt
    # while ensuring the structure and formatting are strictly enforced.
    system_message = f"""You are an Expert Quality Assurance (QA) Manager. 
Your task is to evaluate a customer service call transcript between an Agent and a Customer based on the specific campaign rules provided below.

### CAMPAIGN SPECIFIC RULES:
{campaign_prompt}

### OUTPUT FORMAT:
You MUST output ONLY valid JSON that conforms to the following schema structure. 
You MUST write the "reasoning" field FIRST before calculating the "score" to ensure logical consistency.

Schema:
{{
  "reasoning": string (Think step-by-step here. Analyze the call based on the rules, justify the deductions, and list your findings BEFORE giving the numerical score),
  "score": float (Overall call score from 0 to 100),
  "strengths": [string],
  "weaknesses": [
    {{
      "issue": string (Short category label from the rules above),
      "detail": string (Explanation of what was wrong),
      "deduction": float (Points deducted for this weakness)
    }}
  ],
  "summary": string (One-paragraph overall assessment of the call)
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
            
            # Parse and validate with Pydantic
            result_dict = json.loads(result_text)
            validated_result = EvaluationResult(**result_dict)
            
            # --- FIX: Manual Score Calculation ---
            # AI models (especially smaller ones) often fail at simple math.
            # We force the score to be 100 - sum(deductions).
            total_deductions = sum(w.deduction for w in validated_result.weaknesses)
            calculated_score = max(0.0, 100.0 - total_deductions)
            
            # Update the score in the validated object
            validated_result.score = calculated_score
            return validated_result
            
        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower() and attempt < max_retries - 1:
                print(f"[!] Rate limit hit, retrying in {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2 # Exponential backoff
                continue
                
            print(f"[!] Groq error: {e}")
            if 'result_text' in locals():
                print(f"[!] Raw output: {result_text}")
            raise ValueError(f"Failed to process evaluation: {str(e)}") from e
