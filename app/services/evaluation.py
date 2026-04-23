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
    
    # We define a strict system prompt overriding/wrapping the campaign prompt 
    # to ensure the structure is exactly what we need.
    system_message = f"""You are an Expert Quality Assurance (QA) Manager for "Citizens Debt Relief".
Your task is to evaluate a customer service call transcript between an Agent and a Customer.

### SCORING RULES (Strict Math):
Start with a base score of 100. Deduct points ONLY for the following specific infractions. Do not invent new reasons for deductions.
1. Opening & Verification (-10 points): If the agent fails to state the call is recorded, fails to say their name and company, or fails to verify the customer's identity (e.g., Date of Birth).
2. Hold Etiquette (-10 points): If the agent places the customer on hold without asking for permission, OR fails to say "thank you for your patience" when returning.
3. Empathy & De-escalation (-15 points): If the customer expresses fear or frustration about creditors calling, and the agent fails to "normalize" the situation or fails to explain *why* creditors are calling to calm them down.
4. Practical Solutions (-10 points): If the customer complains about harassing calls, and the agent fails to provide an actionable solution (e.g., suggesting a Google Voice number or explaining document upload procedures).
5. Jargon & Clarity (-5 points): If the agent uses confusing legal/financial terms without explaining them simply.
6. Professional Closing (-5 points): If the agent ends the call without asking "Is there anything else I can help you with?" or similar.

### GOLDEN STANDARDS (Strengths):
Look for these specific behaviors and highlight them in the "strengths" array if they occur:
- "Perfect Hold Etiquette": Agent asks permission and thanks the customer after holding.
- "Excellent De-escalation": Agent reassures the customer that creditor threats are normal tactics.
- "Proactive Account Expansion": Agent successfully identifies an opportunity to enroll a new debt/credit card into the program during the call.
- "Actionable Advice": Agent provides out-of-the-box solutions like using a secondary phone number.

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
