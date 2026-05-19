from typing import Optional
from app.models import AgentViolation
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# VIOLATION REGISTRY — 26 violations from company policy
# ---------------------------------------------------------------------------
VIOLATION_REGISTRY = {

    # ── HIGH SEVERITY ───────────────────────────────────────────────────────
    "manipulative_leading": {
        "description": "Agent instructed the customer to choose an option in a leading or manipulative way",
        "severity": "high", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": ["Warning", "1 HR", "2 HR"],
        "llm_hint": "Flag if the agent instructs the customer to choose an option in a leading, coercive, or manipulative way (e.g. instructing them to say 'yes' or guiding their choices improperly).",
    },
    "recording_disclosure": {
        "description": "Agent did not mention calls are recorded for quality and training",
        "severity": "high", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": ["2 HR"],
        "llm_hint": "Check opening — did agent say calls are recorded for quality/training?",
    },
    "skipped_offer": {
        "description": "Agent skipped a required offer",
        "severity": "high", "category": "sales",
        "penalties": ["3 HR", "3 HR", "Half Day"],
        "auto_fail": True,
        "hr_flag_on": ["3 HR", "Half Day"],
        "llm_hint": "Verify agent presented ALL required offers per the campaign script.",
    },
    "script_skip": {
        "description": "Agent skipped required parts of the script",
        "severity": "high", "category": "compliance",
        "penalties": ["1 HR", "2 HR", "Half Day"],
        "auto_fail": False,
        "hr_flag_on": ["Half Day"],
        "llm_hint": "Check script structure: opening → body → closing. Flag missing sections.",
    },
    "ged_hsd_question": {
        "description": "Agent did not ask about GED or HSD in EDU offer",
        "severity": "high", "category": "sales",
        "penalties": ["2 HR", "3 HR", "Half Day"],
        "auto_fail": False,
        "hr_flag_on": ["Half Day"],
        "llm_hint": "EDU campaigns only: did agent ask about education level (GED or HSD)?",
    },
    "policy_misrepresentation": {
        "description": "Agent misrepresented company policy",
        "severity": "high", "category": "compliance",
        "penalties": ["1 HR", "1 HR", "2 HR"],
        "auto_fail": True,
        "hr_flag_on": ["1 HR", "2 HR"],
        "llm_hint": "Flag any incorrect policy statements or false company claims.",
    },
    "abusive_language": {
        "description": "Agent used abusive language",
        "severity": "high", "category": "behavior",
        "penalties": ["2 HR", "2 HR", "Half Day"],
        "auto_fail": True,
        "hr_flag_on": ["2 HR", "Half Day"],
        "llm_hint": "Flag any offensive, aggressive, or demeaning language from the agent.",
    },
    "false_claims": {
        "description": "Agent made false claims, false info, or false promises",
        "severity": "high", "category": "compliance",
        "penalties": ["2 HR", "3 HR", "Half Day"],
        "auto_fail": True,
        "hr_flag_on": ["2 HR", "3 HR", "Half Day"],
        "llm_hint": "Flag unverifiable promises, fabricated facts, or misleading statements.",
    },
    "avoiding_calls": {
        "description": "Agent was avoiding calls",
        "severity": "high", "category": "behavior",
        "penalties": ["Full Day", "No Show", "Termination"],
        "auto_fail": True,
        "hr_flag_on": ["Full Day", "No Show", "Termination"],
        "llm_hint": "Check for early dispositions, dropped calls without callback, or unexplained gaps.",
    },

    # ── MEDIUM SEVERITY ─────────────────────────────────────────────────────
    "confirm_name": {
        "description": "Agent did not confirm the customer's name",
        "severity": "medium", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Did agent address or confirm the customer by name during the call?",
    },
    "misleading_customer": {
        "description": "Agent misled the customer",
        "severity": "medium", "category": "compliance",
        "penalties": ["2 HR", "2 HR", "3 HR"],
        "auto_fail": False,
        "hr_flag_on": ["3 HR"],
        "llm_hint": "Flag vague promises, omitted key info, or indirect misdirection.",
    },
    "script_adherence": {
        "description": "Agent did not stick to the script",
        "severity": "medium", "category": "compliance",
        "penalties": ["2 HR", "3 HR", "Half Day"],
        "auto_fail": False,
        "hr_flag_on": ["Half Day"],
        "llm_hint": "Flag major script deviations, skipped greetings, or off-script tangents.",
    },
    "arabic_language": {
        "description": "Agent spoke in Arabic (English-only campaign)",
        "severity": "medium", "category": "behavior",
        "penalties": ["2 HR", "2 HR", "3 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Flag any Arabic words or sentences spoken by the agent.",
    },
    "forced_sale": {
        "description": "Agent forced or pressured customer after refusal",
        "severity": "medium", "category": "sales",
        "penalties": ["Warning", "2 HR", "3 HR"],
        "auto_fail": False,
        "hr_flag_on": ["3 HR"],
        "llm_hint": "Did agent continue pitching after customer explicitly said no?",
    },
    "misbehavior": {
        "description": "Agent misbehaved or was rude to the customer",
        "severity": "medium", "category": "behavior",
        "penalties": ["3 HR", "Half Day", "Full Day"],
        "auto_fail": False,
        "hr_flag_on": ["Half Day", "Full Day"],
        "llm_hint": "Flag sarcasm, dismissiveness, impatience, or disrespectful responses.",
    },
    "spam_email": {
        "description": "Agent did not mention marking email as not spam",
        "severity": "medium", "category": "compliance",
        "penalties": ["Warning", "Warning", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Did agent instruct customer to mark company email as not spam?",
    },
    "wrong_disposition": {
        "description": "Agent used wrong call disposition",
        "severity": "medium", "category": "compliance",
        "penalties": ["Warning", "Warning", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Based on call outcome, does the disposition match what actually happened?",
    },
    "outbound_script": {
        "description": "Agent did not follow the outbound call script",
        "severity": "medium", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "For outbound calls, verify agent followed the outbound-specific script.",
    },
    "guide_customer": {
        "description": "Agent did not guide the customer properly",
        "severity": "medium", "category": "sales",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Did agent clearly explain next steps and set proper expectations?",
    },
    "pitch_after_no": {
        "description": "Agent pitched a sale after customer said no",
        "severity": "medium", "category": "sales",
        "penalties": ["1 HR", "2 HR", "3 HR"],
        "auto_fail": False,
        "hr_flag_on": ["3 HR"],
        "llm_hint": "Flag continued sales pitch after explicit customer refusal.",
    },

    # ── LOW SEVERITY ────────────────────────────────────────────────────────
    "callback_time": {
        "description": "Agent did not ask for a callback time",
        "severity": "low", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Did agent confirm a specific callback time when scheduling a follow-up?",
    },
    "greeting_day": {
        "description": "Agent did not ask 'How is your day going so far'",
        "severity": "low", "category": "soft_skills",
        "penalties": ["Warning", "Warning", "1 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Check opening — did agent use rapport-building greeting phrase?",
    },
    "energy": {
        "description": "Agent was not energetic on the call",
        "severity": "low", "category": "soft_skills",
        "penalties": ["Warning", "Warning", "1 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Assess agent tone, enthusiasm, and engagement level throughout call.",
    },
    "confirm_email": {
        "description": "Agent did not confirm the customer's email",
        "severity": "low", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Did agent confirm or repeat back the customer's email address?",
    },
    "missed_callback": {
        "description": "Agent missed a previously scheduled callback",
        "severity": "low", "category": "compliance",
        "penalties": ["Warning", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Check call history — was there a prior agreed callback the agent missed?",
    },
    "dead_air": {
        "description": "Dead air or wasting time on call",
        "severity": "low", "category": "behavior",
        "penalties": ["1 HR", "2 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Flag silences >15 seconds without explanation or hold notification.",
    },
    "hangup_no_reason": {
        "description": "Agent hung up without proper reason",
        "severity": "low", "category": "behavior",
        "penalties": ["1 HR", "1 HR", "2 HR"],
        "auto_fail": False,
        "hr_flag_on": [],
        "llm_hint": "Did call end abruptly without proper closing or resolution?",
    },
}

# ---------------------------------------------------------------------------
# SCORE DEDUCTIONS — per severity × penalty tier
# ---------------------------------------------------------------------------
SCORE_DEDUCTIONS = {
    "high": {
        "Warning": 5,  "1 HR": 15, "2 HR": 20,
        "3 HR": 25,    "Half Day": 35, "Full Day": 50,
        "No Show": 70, "Termination": 100,
    },
    "medium": {
        "Warning": 0,  "1 HR": 8,  "2 HR": 12,
        "3 HR": 16,    "Half Day": 25, "Full Day": 40,
    },
    "low": {
        "Warning": 0,  "1 HR": 5,  "2 HR": 8, "3 HR": 10,
    },
}

# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def get_occurrence(db: Session, employee_id: int, violation_id: str) -> int:
    """Returns the next occurrence number for this agent+violation combo."""
    count = db.query(AgentViolation).filter(
        AgentViolation.employee_id == employee_id,
        AgentViolation.violation_id == violation_id,
    ).count()
    return count + 1  # next occurrence


def get_penalty(violation_id: str, occurrence: int) -> Optional[dict]:
    """
    Returns the full penalty dict for a violation at a given occurrence.
    occurrence: 1 = first time, 2 = second, 3+ = third
    """
    v = VIOLATION_REGISTRY.get(violation_id)
    if not v:
        return None

    idx = min(occurrence, 3) - 1
    penalty_tier = v["penalties"][idx]
    severity = v["severity"]
    score_deduction = SCORE_DEDUCTIONS[severity].get(penalty_tier, 0)
    hr_flagged = penalty_tier in v["hr_flag_on"]
    auto_fail = v["auto_fail"] and penalty_tier != "Warning"

    return {
        "violation_id":    violation_id,
        "description":     v["description"],
        "severity":        severity,
        "category":        v["category"],
        "occurrence":      occurrence,
        "penalty_tier":    penalty_tier,
        "score_deduction": score_deduction,
        "hr_flagged":      hr_flagged,
        "auto_fail":       auto_fail,
    }


def apply_violations(
    base_score: float,
    raw_violations: list,
    employee_id: int,
    call_id: int,
    campaign_id: int,
    db: Session,
) -> dict:
    """
    Processes a list of raw violations from the LLM, persists them to the DB,
    and returns the final adjusted score and HR flag status.

    raw_violations format (from LLM):
    [
      {
        "violation_id": "abusive_language",
        "severity": "high",
        "timestamp": "03:45",
        "evidence": "Agent said ..."
      }
    ]
    """
    from datetime import datetime, timezone

    total_deduction = 0.0
    any_hr_flag = False
    any_auto_fail = False
    saved_violations = []

    for raw in raw_violations:
        vid = raw.get("violation_id")
        if vid not in VIOLATION_REGISTRY:
            continue  # ignore unknown violations

        occurrence = get_occurrence(db, employee_id, vid)
        penalty = get_penalty(vid, occurrence)
        if not penalty:
            continue

        total_deduction += penalty["score_deduction"]
        if penalty["hr_flagged"]:
            any_hr_flag = True
        if penalty["auto_fail"]:
            any_auto_fail = True

        record = AgentViolation(
            employee_id=employee_id,
            call_id=call_id,
            campaign_id=campaign_id,
            violation_id=vid,
            severity=penalty["severity"],
            occurrence=occurrence,
            penalty_tier=penalty["penalty_tier"],
            score_deduction=penalty["score_deduction"],
            hr_flagged=penalty["hr_flagged"],
            auto_fail=penalty["auto_fail"],
            evidence=raw.get("evidence"),
            timestamp_in_call=raw.get("timestamp"),
        )
        db.add(record)
        saved_violations.append(penalty)

    db.flush()  # persist without committing (caller handles commit)

    final_score = max(0.0, base_score - total_deduction)
    if any_auto_fail:
        final_score = min(final_score, 49.0)  # auto-fail threshold

    return {
        "final_score":   final_score,
        "total_deduction": total_deduction,
        "hr_flag":       any_hr_flag,
        "auto_fail":     any_auto_fail,
        "violations":    saved_violations,
    }


def build_violation_prompt(campaign_type: str) -> str:
    """Builds the violation detection section for the LLM system prompt."""

    sales_only = {"skipped_offer", "ged_hsd_question", "forced_sale",
                  "guide_customer", "pitch_after_no"}

    def fmt(severity: str) -> str:
        items = [
            f"  - [{k}] {v['description']}: {v['llm_hint']}"
            for k, v in VIOLATION_REGISTRY.items()
            if v["severity"] == severity
            and (k not in sales_only or campaign_type == "sales")
        ]
        return "\n".join(items)

    return f"""
VIOLATION DETECTION:
Only flag a violation if you have DIRECT EVIDENCE (timestamp + quote or description).
If the call is clean → return "violations": []

🔴 HIGH — Always investigate:
{fmt("high")}

🟠 MEDIUM — Flag if clearly observed:
{fmt("medium")}

🟡 LOW — Flag only if noticeable:
{fmt("low")}

Return format:
"violations": [
  {{
    "violation_id": "exact_key_from_above",
    "severity": "high|medium|low",
    "timestamp": "MM:SS or null",
    "evidence": "direct quote or clear description — required"
  }}
]
If no violations detected → "violations": []
"""
