from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.models import InterviewJob, InterviewMcqSubmission


DEFAULT_INTERVIEW_MCQ_BANK: list[dict[str, Any]] = [
    {
        "id": 1,
        "category": "iq",
        "question": "What is the next number in the sequence: 3, 6, 12, 24, ...?",
        "options": ["36", "48", "60", "72"],
        "correct": 1,
        "type": "pattern",
    },
    {
        "id": 2,
        "category": "iq",
        "question": "Which shape comes next in the pattern: Triangle, Square, Pentagon, Hexagon, ...?",
        "options": ["Heptagon", "Octagon", "Nonagon", "Circle"],
        "correct": 0,
        "type": "pattern",
    },
    {
        "id": 3,
        "category": "iq",
        "question": "If all Bloops are Razzies and all Razzies are Lurgas, which of the following MUST be true?",
        "options": ["All Bloops are Lurgas", "All Lurgas are Bloops", "Some Razzies are not Lurgas", "None of the above"],
        "correct": 0,
        "type": "logic",
    },
    {
        "id": 4,
        "category": "iq",
        "question": "Which word does not belong with the others?",
        "options": ["Leaf", "Root", "Branch", "Dirt"],
        "correct": 3,
        "type": "logic",
    },
    {
        "id": 5,
        "category": "iq",
        "question": "Book is to Reading as Fork is to:",
        "options": ["Drawing", "Writing", "Eating", "Stirring"],
        "correct": 2,
        "type": "logic",
    },
    {
        "id": 6,
        "category": "computer",
        "question": "Which component is responsible for performing calculations and executing instructions in a computer?",
        "options": ["RAM", "GPU", "CPU", "Motherboard"],
        "correct": 2,
        "type": "hardware",
    },
    {
        "id": 7,
        "category": "computer",
        "question": "What keyboard shortcut is commonly used to permanently delete a file without moving it to the Recycle Bin?",
        "options": ["Delete", "Ctrl + Delete", "Shift + Delete", "Alt + Delete"],
        "correct": 2,
        "type": "shortcut",
    },
    {
        "id": 8,
        "category": "computer",
        "question": "What does SSD stand for in the context of computer storage?",
        "options": ["Super Speed Drive", "Solid State Drive", "System Storage Device", "Secure Static Drive"],
        "correct": 1,
        "type": "hardware",
    },
    {
        "id": 9,
        "category": "computer",
        "question": "Which shortcut key combination opens the Windows Task Manager directly?",
        "options": ["Ctrl + Alt + Delete", "Ctrl + Shift + Esc", "Win + R", "Alt + F4"],
        "correct": 1,
        "type": "shortcut",
    },
    {
        "id": 10,
        "category": "computer",
        "question": "Which port is most commonly used to connect a modern mouse, keyboard, or flash drive?",
        "options": ["VGA", "HDMI", "USB", "Ethernet"],
        "correct": 2,
        "type": "hardware",
    },
    {
        "id": 11,
        "category": "soft_skills",
        "question": "A team member is consistently late with their deliverables, affecting your progress. How do you handle it?",
        "options": [
            "Offer to help them and discuss how to improve the workflow together.",
            "Wait silently and hope they catch up eventually.",
            "Publicly criticize their performance in the next team meeting.",
            "Report them to the manager immediately without talking to them.",
        ],
        "correct": 0,
        "type": "situational",
        "trait_tags": ["collaborative", "passive", "aggressive", "impulsive"],
    },
    {
        "id": 12,
        "category": "soft_skills",
        "question": "You realize you made a significant mistake in a report that was already sent to a client. What is your first action?",
        "options": [
            "Inform your manager and the team immediately to coordinate a correction.",
            "Say nothing and hope no one notices the error.",
            "Blame the person who provided the initial data for the report.",
            "Send a second, conflicting report without explaining the first one.",
        ],
        "correct": 0,
        "type": "situational",
        "trait_tags": ["collaborative", "passive", "aggressive", "impulsive"],
    },
    {
        "id": 13,
        "category": "soft_skills",
        "question": "During a brainstorming session, a colleague proposes an idea you think will not work. How do you respond?",
        "options": [
            "Acknowledge their idea and suggest exploring both the pros and cons together.",
            "Stay quiet and let others decide even if you disagree.",
            "Tell them their idea is stupid and won't work.",
            "Interrupt them immediately to propose your own better idea.",
        ],
        "correct": 0,
        "type": "situational",
        "trait_tags": ["collaborative", "passive", "aggressive", "impulsive"],
    },
    {
        "id": 14,
        "category": "soft_skills",
        "question": "You are assigned a task that you have never done before and feel overwhelmed. What do you do?",
        "options": [
            "Consult with a more experienced colleague for guidance and resources.",
            "Try to do it slowly and hope it works out without asking anyone.",
            "Complain loudly to your peers about the unfair workload.",
            "Quit the task and start something else that is easier.",
        ],
        "correct": 0,
        "type": "situational",
        "trait_tags": ["collaborative", "passive", "aggressive", "impulsive"],
    },
    {
        "id": 15,
        "category": "soft_skills",
        "question": "A client is upset with you over the phone about a delay. How do you respond?",
        "options": [
            "Listen calmly, empathize, and work with them to find a solution.",
            "Listen to the complaint and apologize without offering solutions.",
            "Raise your voice to defend yourself and your team.",
            "End the conversation immediately without resolving the issue.",
        ],
        "correct": 0,
        "type": "situational",
        "trait_tags": ["collaborative", "passive", "aggressive", "impulsive"],
    },
]


def _normalize_question(question: dict[str, Any], fallback_id: int) -> dict[str, Any]:
    options = [str(option).strip() for option in (question.get("options") or []) if str(option).strip()]
    if len(options) < 2:
        raise ValueError("Each MCQ question must contain at least two options.")
    normalized = {
        "id": int(question.get("id") or fallback_id),
        "category": str(question.get("category") or "soft_skills").strip().lower(),
        "question": str(question.get("question") or "").strip(),
        "options": options,
        "type": str(question.get("type") or "manual").strip().lower(),
    }
    if not normalized["question"]:
        raise ValueError("MCQ question text cannot be empty.")
    correct = question.get("correct")
    if correct is not None:
        correct_index = int(correct)
        if correct_index < 0 or correct_index >= len(options):
            raise ValueError("MCQ correct answer index is out of range.")
        normalized["correct"] = correct_index
    trait_tags = question.get("trait_tags") or []
    if trait_tags:
        normalized["trait_tags"] = [str(tag).strip().lower() for tag in trait_tags]
    return normalized


def normalize_mcq_bank(raw_questions: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not raw_questions:
        return deepcopy(DEFAULT_INTERVIEW_MCQ_BANK)
    normalized_questions: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for index, question in enumerate(raw_questions, start=1):
        normalized = _normalize_question(question, index)
        if normalized["id"] in seen_ids:
            normalized["id"] = max(seen_ids, default=0) + 1
        seen_ids.add(normalized["id"])
        normalized_questions.append(normalized)
    return normalized_questions


def get_job_mcq_bank(job: InterviewJob) -> list[dict[str, Any]]:
    configured_questions = job.mcq_questions if job.mcq_enabled else []
    return normalize_mcq_bank(configured_questions)


def get_safe_mcq_bank(raw_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": question["id"],
            "category": question.get("category"),
            "question": question.get("question"),
            "options": list(question.get("options") or []),
            "type": question.get("type"),
        }
        for question in raw_questions
    ]


def grade_mcq_answers(raw_questions: list[dict[str, Any]], raw_answers: dict[str, Any]) -> dict[str, Any]:
    questions = normalize_mcq_bank(raw_questions)
    answers = {str(key): int(value) for key, value in (raw_answers or {}).items()}
    score = 0.0
    objective_breakdown: dict[str, int] = {}
    trait_breakdown: dict[str, int] = {"collaborative": 0, "passive": 0, "aggressive": 0, "impulsive": 0}
    results_detail: list[dict[str, Any]] = []

    for question in questions:
        question_id = str(question["id"])
        selected_index = answers.get(question_id)
        options = question.get("options") or []
        if selected_index is None or selected_index < 0 or selected_index >= len(options):
            raise ValueError(f"Answer missing or invalid for MCQ question {question_id}.")

        category = str(question.get("category") or "soft_skills").strip().lower()
        trait_tags = question.get("trait_tags") or []
        correct_answer = question.get("correct")
        is_trait_question = bool(trait_tags) or category in {"soft_skills", "situational"}

        is_correct = False
        if is_trait_question:
            is_correct = True
            score += 1
            if selected_index < len(trait_tags):
                selected_trait = str(trait_tags[selected_index]).strip().lower()
                trait_breakdown[selected_trait] = trait_breakdown.get(selected_trait, 0) + 1
        elif correct_answer is not None and selected_index == int(correct_answer):
            is_correct = True
            score += 1
            objective_breakdown[category] = objective_breakdown.get(category, 0) + 1

        results_detail.append(
            {
                "question_id": question["id"],
                "category": category,
                "user_answer": selected_index,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
            }
        )

    total_questions = len(questions)
    percentage = (score / total_questions * 100.0) if total_questions else 0.0
    return {
        "score": float(score),
        "total_questions": total_questions,
        "percentage": round(percentage, 2),
        "breakdown": {
            "objective": objective_breakdown,
            "traits": trait_breakdown,
            "details": results_detail,
        },
        "question_bank_snapshot": questions,
        "answers": answers,
    }


def format_mcq_results_for_review(
    submission: InterviewMcqSubmission,
    *,
    candidate_name: str,
) -> dict[str, Any]:
    bank = normalize_mcq_bank(submission.question_bank_snapshot or [])
    details = ((submission.breakdown or {}).get("details") or [])
    bank_lookup = {int(question["id"]): question for question in bank}

    iq_section: list[dict[str, Any]] = []
    computer_section: list[dict[str, Any]] = []
    personality_section: list[dict[str, Any]] = []

    for result in details:
        question_id = int(result.get("question_id") or 0)
        bank_question = bank_lookup.get(question_id)
        if bank_question is None:
            continue

        category = str(result.get("category") or bank_question.get("category") or "").strip().lower()
        user_answer = result.get("user_answer")
        entry = {
            "question_id": question_id,
            "question_text": bank_question.get("question"),
            "options": list(bank_question.get("options") or []),
            "user_answer": user_answer,
            "correct_answer": bank_question.get("correct"),
            "type": bank_question.get("type"),
        }

        if category == "iq":
            entry["is_correct"] = bool(result.get("is_correct"))
            iq_section.append(entry)
            continue

        if category == "computer":
            entry["is_correct"] = bool(result.get("is_correct"))
            computer_section.append(entry)
            continue

        trait_tags = list(bank_question.get("trait_tags") or [])
        chosen_trait = None
        if isinstance(user_answer, int) and 0 <= user_answer < len(trait_tags):
            chosen_trait = trait_tags[user_answer]
        entry["trait_tags"] = trait_tags
        entry["chosen_trait"] = chosen_trait
        personality_section.append(entry)

    return {
        "status": "success",
        "candidate_id": submission.candidate_id,
        "candidate_name": candidate_name,
        "score": submission.score,
        "total_questions": submission.total_questions,
        "percentage": submission.percentage,
        "completed_at": submission.completed_at,
        "iq": iq_section,
        "computer": computer_section,
        "personality": personality_section,
        "personality_breakdown": dict(((submission.breakdown or {}).get("traits") or {})),
    }
