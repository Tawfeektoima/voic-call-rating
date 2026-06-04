# Role Definitions & Access Control Matrix

This document defines the complete matrix of roles, permissions, and scoping rules for the Call Rating & Platform QA system. 

Canonical backend roles are documented in [authorization_matrix.md](authorization_matrix.md). The older operational examples below are kept for legacy context and should not be treated as the current supported role set.

All security and access logic relies on these strict definitions.

---

## 1. Roles Overview & Data Scope

| Role | Primary Responsibility | Data Scope |
| :--- | :--- | :--- |
| **Agent** | Receives calls, views own performance, reviews feedback. | **Self-only** (Own Employee ID) |
| **Team Leader** | Coaches agents, reviews specific team's calls, performs QA on team. | **Assigned Team** (Agents within their team) |
| **Team Manager** | Manages multiple teams and Team Leaders, tracks campaign KPIs. | **Assigned Campaign / Dept** (All teams under them) |
| **Ops Manager** | Oversees overall operations, resource allocation, and campaign success. | **Global** (All Operational Data) |
| **Recruiter** | Handles candidate screening, interviews, and initial onboarding data. | **Pre-hires & Onboarding Data** |
| **HR Manager** | Manages bulk onboarding, violations, HR alarms, and payroll compliance. | **Global Personnel** (All employee & HR data) |
| **AI Engineer** | Tunes prompts, checks AI transcripts, adjusts grading and routing logic. | **System/Config Level** (No PII modification) |
| **Admin** | Full system access, configures integrations, roles, and master settings. | **Global** (All Data) |

---

## 2. Capabilities Matrix

The following matrix maps CRUD (Create, Read, Update, Delete) and View capabilities to specific roles.

| Capability / Module | Agent | Team Leader | Team Manager | Ops Manager | Recruiter | HR Manager | AI Engineer | Admin |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Calls: View Audio/Transcript** | Own | Team | Campaign | All | None | Escalated | All | All |
| **Calls: Score Override (QA)** | None | Yes (Team) | Yes (Camp.) | Yes | None | Yes | None | Yes |
| **Calls: Bulk Upload** | None | None | None | Yes | None | None | Yes | Yes |
| **Agents: View Profile** | Own | Team | Campaign | All | Pre-hires | All | None | All |
| **Agents: Bulk Onboarding** | None | None | None | None | None | Yes | None | Yes |
| **HR: Manage Violations** | None | None | None | None | None | Yes | None | Yes |
| **HR: View Global Leaderboard** | None | None | None | Yes | None | Yes | None | Yes |
| **BI: View Analytics Dashboards**| Own | Team | Campaign | All | None | HR Only | Config | All |
| **System: Manage Campaigns** | None | None | None | Yes | None | None | None | Yes |
| **System: Edit AI Prompts** | None | None | None | None | None | None | Yes | Yes |

---

## 3. Data Scope Rules & API Filtering

Data leakage between departments or teams must be strictly prevented at the database query layer, never just hidden in the UI.

### Scope Enforcement Examples
- **Agent Scope:** `query.filter(Call.employee_id == current_user.id)`
- **Team Leader Scope:** `query.filter(Call.employee_id.in_(team_agent_ids))`
- **Team Manager Scope:** `query.filter(Call.campaign_id.in_(manager_campaign_ids))`

### Sample API Filtering Implementation

```python
from fastapi import HTTPException
from app.models import Call, UserRole

def get_scoped_calls(db: Session, current_user: Employee):
    query = db.query(Call)
    
    if current_user.role == UserRole.AGENT:
        # Strict self-scope: Agents only see their own calls
        query = query.filter(Call.employee_id == current_user.id)
        
    elif current_user.role == UserRole.TEAM_LEADER:
        # Team scope: Team Leaders only see calls for agents they manage
        agent_ids = get_team_agent_ids(db, current_user.id)
        query = query.filter(Call.employee_id.in_(agent_ids))
        
    elif current_user.role in (UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.AI_ENGINEER):
        # Global operational scope: Full view of all calls
        pass 
        
    elif current_user.role == UserRole.HR_MANAGER:
        # HR scope: May only view calls that triggered a QA alarm / HR violation
        query = query.filter(Call.qa_alarm == True)
        
    else:
        # Default deny: Fallback for unhandled roles
        raise HTTPException(status_code=403, detail="Unauthorized role access.")
        
    return query.all()
```

---

## 4. Ambiguity Resolution & Approval Workflow

In cases where an operation crosses strict boundary rules (e.g., a Team Leader attempting to manage an agent outside their team, or a Team Manager attempting to modify a global campaign constraint):

1. **Deny by Default:** The backend must return a `403 Forbidden` response.
2. **Approval Request Routing:** The UI should catch the 403 error and, if applicable, present an "Approval Required" dialog. 
3. **Escalation:** The request is routed via the internal ticketing/notification system to an **Admin** or **Ops Manager**.
4. **Temporary Grant:** Once approved, the system generates a temporary authorization token (or adds a temporary association table entry) granting the lower-level role explicit access to execute that specific operation.
