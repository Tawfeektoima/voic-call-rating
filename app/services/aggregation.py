import json
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models import Call, CallStatus
from app.schemas import CommonError
from typing import List

def get_common_weaknesses(db: Session, limit: int = 10) -> List[CommonError]:
    """
    Aggregates all weaknesses from evaluated calls to find the most common errors.
    """
    # Fetch all weaknesses and associated employee_ids from all evaluated calls
    calls = db.query(Call.employee_id, Call.weaknesses).filter(Call.status == CallStatus.EVALUATED).all()
    
    if not calls:
        return []

    category_stats = {}
    
    for employee_id, weaknesses_json in calls:
        if not weaknesses_json:
            continue
            
        # weaknesses_json is a list of dicts: [{'category': '...', 'detail': '...', 'deduction': ...}]
        if isinstance(weaknesses_json, str):
            weaknesses_list = json.loads(weaknesses_json)
        else:
            weaknesses_list = weaknesses_json
            
        for w in weaknesses_list:
            cat = w.get("category", "Unknown")
            detail = w.get("detail", "")
            deduction = w.get("deduction", 0.0)
            
            if cat not in category_stats:
                category_stats[cat] = {
                    "count": 0,
                    "total_deduction": 0.0,
                    "examples": set(),
                    "affected_employees": set()
                }
                
            category_stats[cat]["count"] += 1
            category_stats[cat]["total_deduction"] += deduction
            category_stats[cat]["affected_employees"].add(employee_id)
            if detail:
                category_stats[cat]["examples"].add(detail)

    # Convert to list of CommonError schemas
    results = []
    for cat, stats in category_stats.items():
        results.append(
            CommonError(
                category=cat,
                occurrence_count=stats["count"],
                affected_employees=len(stats["affected_employees"]),
                avg_deduction=round(stats["total_deduction"] / stats["count"], 2) if stats["count"] > 0 else 0,
                example_details=list(stats["examples"])[:3] # Keep top 3 examples
            )
        )
        
    # Sort by occurrence count descending
    results.sort(key=lambda x: x.occurrence_count, reverse=True)
    return results[:limit]

def update_agent_mastery_stats(db: Session, employee_id: int):
    """
    Recalculates global skill mastery averages for an agent.
    Maps LLM deduction categories to Radar Chart Axes.
    """
    from app.models import Call, AgentMasteryStats, CallStatus
    import json

    # Fetch all evaluated calls for this employee
    calls = db.query(Call).filter(
        Call.employee_id == employee_id,
        Call.status == CallStatus.EVALUATED
    ).all()

    if not calls:
        return

    # Skill categories mapping (LLM Deduction -> Radar Axis)
    mapping = {
        "Rapport Building": ["Empathy Markers", "Rapport"],
        "Emotional Sync": ["Initial Mirroring & Tone", "Mirroring", "Tone Sync"],
        "Ownership & Trust": ["The 'Assurance' Factor", "Ownership", "Trust"],
        "Process Clarity": ["Transparency & Predictability", "Clarity", "Process"]
    }

    # Initialize accumulators
    totals = {axis: [] for axis in mapping.keys()}

    for call in calls:
        weaknesses = call.weaknesses or []
        if isinstance(weaknesses, str):
            weaknesses = json.loads(weaknesses)
        
        # Track which axes were hit in this call
        call_hits = {axis: 0.0 for axis in mapping.keys()}
        
        for w in weaknesses:
            issue = w.get("issue", "")
            deduction = float(w.get("deduction", 0.0))
            
            for axis, keywords in mapping.items():
                if any(kw.lower() in issue.lower() for kw in keywords):
                    call_hits[axis] += deduction
        
        # Add this call's performance to global totals
        for axis, deduction_sum in call_hits.items():
            totals[axis].append(deduction_sum)

    # Calculate means using formula: 100 + (sum / n)
    def calc_mean(deductions):
        if not deductions: return 100.0
        avg_deduction = sum(deductions) / len(deductions)
        # Clamped at 0 to prevent UI errors
        return max(0.0, 100.0 - avg_deduction)

    mastery_data = {
        "rapport_building": calc_mean(totals["Rapport Building"]),
        "emotional_sync": calc_mean(totals["Emotional Sync"]),
        "ownership_trust": calc_mean(totals["Ownership & Trust"]),
        "process_clarity": calc_mean(totals["Process Clarity"])
    }

    # Update or Create stats record
    stats = db.query(AgentMasteryStats).filter(AgentMasteryStats.employee_id == employee_id).first()
    if not stats:
        stats = AgentMasteryStats(employee_id=employee_id, **mastery_data)
        db.add(stats)
    else:
        for key, value in mastery_data.items():
            setattr(stats, key, value)
    
    db.commit()
