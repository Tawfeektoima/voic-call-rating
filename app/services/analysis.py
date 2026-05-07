import json
import time
import re
from groq import Groq
from app.config import get_settings
from app.schemas import EvaluationResult, SalesEvaluationResult

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


def build_system_message(
    campaign_prompt: str,
    campaign_type: str,
    agent_name: str = None,
    transfer_detected: bool = False,
    transfer_point_sec: float = None
) -> str:
    agent_label = f'"{ agent_name}"' if agent_name else '"Agent"'

    if transfer_detected and transfer_point_sec is not None:
        transfer_banner = (
            f"🔄 TRANSFER DETECTED: This call contains a call transfer.\n"
            f"⏱ TRANSFER POINT: {transfer_point_sec:.1f}s into the call.\n"
            f"⛔ HARD BOUNDARY: Do NOT evaluate ANY segment with a start "
            f"timestamp greater than {transfer_point_sec:.1f}s."
        )
    elif transfer_detected:
        transfer_banner = "🔄 TRANSFER DETECTED: This call contains a call transfer."
    else:
        transfer_banner = ""

    transfer_note = f"""⚠️ MULTI-PARTY CALLS & TRANSFERS:
{transfer_banner}
Some calls involve a transfer or conference where a third party
joins mid-call (e.g., a debt relief agent, supervisor, or vendor).
In such cases:
- The ORIGINAL agent being evaluated is: {agent_label}
- After a transfer, the new speaker labeled "Customer" may actually
  be a representative from another company (NOT the customer).
- Evaluate ONLY the original agent {agent_label} — their segments
  appear BEFORE the transfer point.
- Do NOT evaluate the third-party representative as the agent.
- Do NOT penalize the agent for what the third-party says after transfer.
- The agent's score should reflect only the pre-transfer interaction."""

    artifact_note = """⚠️ TRANSCRIPT ARTIFACTS:
WhisperX may produce repeated identical phrases during silence or hold music.
Example: the same sentence repeated 10+ times in a row = audio artifact, NOT real speech.
- Ignore any phrase repeated more than 3 times consecutively.
- Do NOT penalize the agent for transcription artifacts."""

    # ✅ Sales campaigns: prompt IS the full system message
    if campaign_type == "sales":
        return f"""{campaign_prompt}

AGENT IDENTITY: The agent being evaluated is {agent_label}.

{transfer_note}

{artifact_note}
"""

    # All other types: use existing wrapper
    outcome_extraction = _build_campaign_outcome_prompt(campaign_type)
    return f"""
You are an Expert Quality Assurance (QA) Manager evaluating a recorded customer service call.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 TRANSCRIPT UNDERSTANDING — READ FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The transcript contains segments with a "speaker" field of either "Agent" or "Customer".
The Agent being evaluated is: {agent_label}

{transfer_note}

{artifact_note}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CAMPAIGN EVALUATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{campaign_prompt}

Provide a BALANCED and OBJECTIVE assessment.
You MUST identify BOTH strengths AND areas for improvement.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 BEHAVIOR EVALUATION RUBRIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Evaluate the agent on:
1. RAPPORT BUILDING     — Greeting, warmth, name usage, empathy markers
2. EMOTIONAL SYNC       — Tone mirroring, de-escalation, emotional awareness
3. OWNERSHIP & TRUST    — Taking responsibility, assurance language, confidence
4. PROCESS CLARITY      — Clear explanations, step-by-step guidance, no jargon
5. COMPLIANCE           — Opening/closing script, identity verification
6. ACTIVE LISTENING     — Clarifying questions, not interrupting, summarizing
7. PROFESSIONALISM      — Language quality, patience, no emotional outbursts

Point Deduction Scale:
- Minor (word choice, slight tone issue):               -2 to -5 pts
- Moderate (missed step, unclear explanation):          -5 to -10 pts
- Serious (compliance failure, ignored customer anger): -10 to -20 pts
- Critical (agent outburst, abusive language):          -20 to -35 pts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 BUSINESS OUTCOME EXTRACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{outcome_extraction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT — STRICT JSON ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Output ONLY valid JSON. No markdown. No extra text before or after.
Write "reasoning" FIRST — think step-by-step before calculating score.

{{{{
  "reasoning": "Step-by-step: identify the real agent, note any transcript artifacts, justify each deduction",
  "score": 0-100,
  "strengths": ["2–4 specific positive behaviors"],
  "weaknesses": [
    {{{{"issue": "Short category label", "detail": "What went wrong", "deduction": 0.0}}}}
  ],
  "summary": "3 clear sentences: what happened, agent performance, outcome",
  "qapairs": [
    {{{{
      "objection": "Customer objection text",
      "response": "Agent response text",
      "customeremotionat": "calm|stress|agitation",
      "customeremotionafter": "calm|stress|agitation",
      "isgolden": false
    }}}}
  ],
  "openingok": false,
  "closingok": false,
  "dobverified": false,
  "primaryoutcome": "string",
  "outcomevalue": null,
  "followuprequired": false,
  "followupdate": null,
  "campaignspecificdata": {{{{}}}}
}}}}

VALIDATION CHECKLIST before responding:
✅ "reasoning" explicitly identifies who the real agent is
✅ "score" is a number between 0 and 100
✅ All "deduction" values are positive numbers
✅ "summary" contains no schema field names or internal notes
✅ No field is missing from the JSON
"""


def evaluate_transcript(transcript: str, campaign_prompt: str, campaign_type: str = "customer_service", agent_name: str = None, transfer_detected: bool = False, transfer_point_sec: float = None) -> EvaluationResult:
    """
    Sends the transcript and the campaign-specific prompt to Groq.
    Forces JSON output adhering to the EvaluationResult schema.
    Dynamically injects campaign-type-specific extraction rules.
    """
    
    system_message = build_system_message(
        campaign_prompt,
        campaign_type,
        agent_name,
        transfer_detected,
        transfer_point_sec
    )

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

            # ✅ Route to correct schema
            if campaign_type == "sales":
                sales_result = SalesEvaluationResult(**result_dict)

                # Build weaknesses list from score_breakdown for DB compatibility
                breakdown = sales_result.score_breakdown
                weaknesses = []
                if breakdown:
                    for field, val in breakdown.model_dump().items():
                        max_pts = {
                            "opening": 10,
                            "script_compliance": 30,
                            "customer_handling": 20,
                            "conduct": 25,
                            "closing": 15
                        }
                        deducted = max_pts.get(field, 0) - val
                        if deducted > 0:
                            weaknesses.append({
                                "issue": field.replace("_", " ").title(),
                                "detail": f"Score: {val}/{max_pts.get(field,0)}",
                                "deduction": deducted
                            })

                # Robust extraction for opening/closing regardless if dict or object
                opening_data = sales_result.opening
                opening_ok = False
                if hasattr(opening_data, 'get'):
                    opening_ok = opening_data.get("identified_company", False)
                else:
                    opening_ok = getattr(opening_data, 'identified_company', False)

                closing_data = sales_result.closing
                closing_ok = False
                if hasattr(closing_data, 'get'):
                    closing_ok = closing_data.get("professional_farewell", False)
                else:
                    closing_ok = getattr(closing_data, 'professional_farewell', False)

                return EvaluationResult(
                    score=sales_result.score,
                    summary=sales_result.summary,
                    reasoning=sales_result.reasoning,
                    strengths=[{"issue": s, "detail": ""} for s in sales_result.strengths],
                    weaknesses=weaknesses,
                    opening_ok=opening_ok,
                    closing_ok=closing_ok,
                    raw_sales_data=sales_result.model_dump()
                )

            # Non-sales: existing parsing
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
        "for quality assurance"
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

    # Analyze first 20 segments
    for idx, seg in enumerate(segments[:20]):
        speaker = seg.get("speaker", "UNKNOWN")
        if speaker == "UNKNOWN":
            continue
            
        text = seg.get("text", "").lower()
        start_time = float(seg.get("start", 0.0))
        
        if speaker not in scores:
            scores[speaker] = {"agent": 0, "customer": 0, "first_seen": start_time}
            
        weight = 1.0
        
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

    if best_agent_speaker is None or max_agent_score <= 0:
        sorted_speakers = sorted(
            [{"id": k, "time": v["first_seen"]} for k, v in scores.items()],
            key=lambda x: x["time"]
        )
        if len(sorted_speakers) >= 2:
            # In inbound calls the agent answers second.
            # In outbound calls the agent speaks first.
            # We cannot know the direction, so we pick the speaker
            # with the HIGHER net agent score regardless of position.
            # If still tied, pick the SECOND speaker (inbound default).
            scores_by_net = sorted(
                sorted_speakers,
                key=lambda x: (
                    scores[x["id"]]["agent"] - scores[x["id"]]["customer"]
                ),
                reverse=True
            )
            best_agent_speaker = scores_by_net[0]["id"]
            # If net scores are equal, fall back to second speaker (inbound default)
            if (scores[scores_by_net[0]["id"]]["agent"] - scores[scores_by_net[0]["id"]]["customer"] ==
                scores[scores_by_net[1]["id"]]["agent"] - scores[scores_by_net[1]["id"]]["customer"]):
                best_agent_speaker = sorted_speakers[1]["id"]
            print(f"[*] Fallback: Assigning {best_agent_speaker} as Agent (net-score or inbound default).")
        elif sorted_speakers:
            best_agent_speaker = sorted_speakers[0]["id"]
            print(f"[*] Fallback: Only one speaker found, assigning {best_agent_speaker} as Agent.")

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
