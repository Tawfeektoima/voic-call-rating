from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class KpiDefinition(TypedDict):
    key: str
    label: str
    unit: str
    direction: str
    description: str


_KPI_CATALOG: List[KpiDefinition] = [
    {"key": "conversion_rate", "label": "Conversion Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Share of evaluated calls that ended in a successful conversion outcome."},
    {"key": "close_rate", "label": "Close Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Share of sales-oriented calls that reached a closed outcome."},
    {"key": "total_sales", "label": "Total Sales", "unit": "count", "direction": "higher_is_better", "description": "Total number of successful sales in the selected period."},
    {"key": "total_revenue", "label": "Total Revenue", "unit": "currency", "direction": "higher_is_better", "description": "Total revenue value extracted from converted calls."},
    {"key": "average_qa_score", "label": "Average QA Score", "unit": "score", "direction": "higher_is_better", "description": "Average final QA score across evaluated calls."},
    {"key": "attendance_rate", "label": "Attendance Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Attendance percentage for scheduled shifts."},
    {"key": "punctuality_rate", "label": "Punctuality Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Share of attended shifts that started on time."},
    {"key": "follow_up_completion_rate", "label": "Follow-up Completion Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Percentage of required follow-ups completed."},
    {"key": "script_compliance_rate", "label": "Script Compliance Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Share of calls meeting script and compliance requirements."},
    {"key": "objection_handling_score", "label": "Objection Handling Score", "unit": "score", "direction": "higher_is_better", "description": "Composite score for how well objections were answered."},
    {"key": "talk_listen_ratio", "label": "Talk/Listen Ratio", "unit": "ratio", "direction": "lower_is_better", "description": "Average ratio of agent talk time to customer talk time."},
    {"key": "call_handle_time", "label": "Call Handle Time", "unit": "duration", "direction": "lower_is_better", "description": "Average handled call duration."},
    {"key": "first_call_resolution_rate", "label": "First Call Resolution Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Share of cases resolved without a follow-up interaction."},
    {"key": "upsell_rate", "label": "Upsell Rate", "unit": "percentage", "direction": "higher_is_better", "description": "Share of qualified calls that resulted in an upsell outcome."},
    {"key": "violation_rate", "label": "Violation Rate", "unit": "percentage", "direction": "lower_is_better", "description": "Percentage of calls that triggered at least one recorded violation."},
]

_KPI_BY_KEY: Dict[str, KpiDefinition] = {item["key"]: item for item in _KPI_CATALOG}


def get_kpi_catalog() -> List[KpiDefinition]:
    return [dict(item) for item in _KPI_CATALOG]


def get_kpi_definition(kpi_key: str) -> Optional[KpiDefinition]:
    item = _KPI_BY_KEY.get(kpi_key)
    return dict(item) if item else None


def is_valid_kpi_key(kpi_key: str) -> bool:
    return kpi_key in _KPI_BY_KEY
