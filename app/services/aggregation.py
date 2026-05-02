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
