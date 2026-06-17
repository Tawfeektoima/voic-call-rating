import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.models import Call, CallStatus, EmployeeTeamAssignment
from app.schemas import CommonError
from typing import List, Optional

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


def calculate_core_kpis(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    employee_id: Optional[int] = None,
    team_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
) -> dict:
    """
    Calculates the core KPIs for the dashboard and system routers in a centralized place.
    Supports optional date range filtering and agent-scoping (by employee_id).
    """
    # 1. Total calls query (All time evaluated)
    total_calls_query = db.query(func.count(Call.id)).filter(Call.status == CallStatus.EVALUATED)
    
    # 2. Avg QA Score query
    avg_score_query = db.query(func.avg(func.coalesce(Call.overridden_score, Call.evaluation_score))).filter(
        Call.status == CallStatus.EVALUATED
    )

    # 3. Queue Depth / Processing counts
    pending_query = db.query(func.count(Call.id)).filter(Call.status == CallStatus.PENDING)
    processing_query = db.query(func.count(Call.id)).filter(Call.status == CallStatus.PROCESSING)

    # 4. Pass Rate queries
    passed_query = db.query(func.count(Call.id)).filter(
        Call.status == CallStatus.EVALUATED,
        func.coalesce(Call.overridden_score, Call.evaluation_score) >= 70
    )

    # 5. Calls today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = db.query(func.count(Call.id))

    # Apply agent-scoping
    if employee_id is not None:
        total_calls_query = total_calls_query.filter(Call.employee_id == employee_id)
        avg_score_query = avg_score_query.filter(Call.employee_id == employee_id)
        pending_query = pending_query.filter(Call.employee_id == employee_id)
        processing_query = processing_query.filter(Call.employee_id == employee_id)
        passed_query = passed_query.filter(Call.employee_id == employee_id)
        today_query = today_query.filter(Call.employee_id == employee_id)
    elif team_id is not None:
        join_condition = and_(
            Call.employee_id == EmployeeTeamAssignment.employee_id,
            EmployeeTeamAssignment.is_active == True,
        )
        total_calls_query = total_calls_query.join(EmployeeTeamAssignment, join_condition).filter(EmployeeTeamAssignment.team_id == team_id)
        avg_score_query = avg_score_query.join(EmployeeTeamAssignment, join_condition).filter(EmployeeTeamAssignment.team_id == team_id)
        pending_query = pending_query.join(EmployeeTeamAssignment, join_condition).filter(EmployeeTeamAssignment.team_id == team_id)
        processing_query = processing_query.join(EmployeeTeamAssignment, join_condition).filter(EmployeeTeamAssignment.team_id == team_id)
        passed_query = passed_query.join(EmployeeTeamAssignment, join_condition).filter(EmployeeTeamAssignment.team_id == team_id)
        today_query = today_query.join(EmployeeTeamAssignment, join_condition).filter(EmployeeTeamAssignment.team_id == team_id)
        if campaign_id is not None:
            total_calls_query = total_calls_query.filter(Call.campaign_id == campaign_id)
            avg_score_query = avg_score_query.filter(Call.campaign_id == campaign_id)
            pending_query = pending_query.filter(Call.campaign_id == campaign_id)
            processing_query = processing_query.filter(Call.campaign_id == campaign_id)
            passed_query = passed_query.filter(Call.campaign_id == campaign_id)
            today_query = today_query.filter(Call.campaign_id == campaign_id)

    # Apply date filters
    if date_from:
        total_calls_query = total_calls_query.filter(Call.created_at >= date_from)
        avg_score_query = avg_score_query.filter(Call.created_at >= date_from)
        pending_query = pending_query.filter(Call.created_at >= date_from)
        processing_query = processing_query.filter(Call.created_at >= date_from)
        passed_query = passed_query.filter(Call.created_at >= date_from)
        
    if date_to:
        total_calls_query = total_calls_query.filter(Call.created_at <= date_to)
        avg_score_query = avg_score_query.filter(Call.created_at <= date_to)
        pending_query = pending_query.filter(Call.created_at <= date_to)
        processing_query = processing_query.filter(Call.created_at <= date_to)
        passed_query = passed_query.filter(Call.created_at <= date_to)

    # Today's start logic with date_from/date_to override
    start_date = max(today_start, date_from) if date_from else today_start
    today_query = today_query.filter(Call.created_at >= start_date)
    if date_to:
        today_query = today_query.filter(Call.created_at <= date_to)

    # Execute queries
    total_calls = total_calls_query.scalar() or 0
    avg_score = avg_score_query.scalar() or 0.0
    pending_count = pending_query.scalar() or 0
    processing_count = processing_query.scalar() or 0
    passed_calls = passed_query.scalar() or 0
    total_calls_today = today_query.scalar() or 0

    total_evaluated = total_calls
    pass_rate = (passed_calls / total_evaluated * 100) if total_evaluated > 0 else 0.0

    return {
        "total_calls_today": total_calls_today,
        "total_calls": total_calls,
        "avg_qa_score": round(avg_score, 1),
        "queue_depth": pending_count + processing_count,
        "pending_count": pending_count,
        "processing_count": processing_count,
        "pass_rate": round(pass_rate, 1)
    }
