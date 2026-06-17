from __future__ import annotations

from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET


PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
LONG_NUMBER_PATTERN = re.compile(r"\b\d{6,}\b")


def extract_text_from_document(path_value: str, content_type: str | None = None, filename: str | None = None) -> str:
    file_path = Path(path_value)
    suffix = (file_path.suffix or "").lower()
    normalized_content_type = (content_type or "").lower()

    if suffix in {".txt", ".md"} or normalized_content_type.startswith("text/"):
        return file_path.read_text(encoding="utf-8", errors="ignore").strip()

    if suffix == ".docx" or normalized_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            with zipfile.ZipFile(file_path) as archive:
                xml_content = archive.read("word/document.xml")
            root = ET.fromstring(xml_content)
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs: list[str] = []
            for paragraph in root.findall(".//w:p", namespace):
                text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
                if text:
                    paragraphs.append(text)
            return "\n".join(paragraphs).strip()
        except Exception as exc:
            raise ValueError(f"Unable to extract text from DOCX: {exc}") from exc

    if suffix == ".pdf" or normalized_content_type == "application/pdf":
        text = ""
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(file_path))
            text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
        except Exception:
            text = ""

        if text.strip():
            return text.strip()

        try:
            import fitz

            with fitz.open(str(file_path)) as doc:
                return "\n".join(page.get_text("text").strip() for page in doc).strip()
        except Exception as exc:
            raise ValueError(f"Unable to extract text from PDF: {exc}") from exc

    raise ValueError("Unsupported document format for automatic text extraction.")


def sanitize_cv_text_for_ai(extracted_text: str) -> str:
    text = " ".join((extracted_text or "").split())
    if not text:
        return ""

    sanitized = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[email]", text)
    sanitized = PHONE_PATTERN.sub("[phone]", sanitized)
    sanitized = LONG_NUMBER_PATTERN.sub("[id]", sanitized)
    return sanitized


def _normalize_excerpt(text: str, limit: int) -> str:
    cleaned = text.replace("[email]", "your background").replace("[phone]", "").replace("[id]", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .;,-")
    return cleaned[:limit].strip()


def generate_cv_questions(extracted_text: str, max_questions: int = 3) -> list[str]:
    text = sanitize_cv_text_for_ai(extracted_text)
    if not text:
        return []

    questions: list[str] = []
    cleaned_text = text

    skill_match = re.search(r"(skills?|technical skills?|core competencies)\s*[:\-]?\s*(.{20,240})", cleaned_text, re.IGNORECASE)
    if skill_match:
        skills_excerpt = _normalize_excerpt(skill_match.group(2).split("experience")[0].split("education")[0], 90)
        if skills_excerpt:
            questions.append(f"You listed {skills_excerpt}. Which of these skills have you used most recently in live work?")

    experience_match = re.search(r"(experience|employment history|work history)\s*[:\-]?\s*(.{30,260})", cleaned_text, re.IGNORECASE)
    if experience_match:
        experience_excerpt = _normalize_excerpt(experience_match.group(2), 90)
        if experience_excerpt:
            questions.append(f"Your CV mentions {experience_excerpt}. Walk me through one result you personally delivered there.")

    achievement_match = re.search(r"(achievements?|accomplishments?|projects?)\s*[:\-]?\s*(.{20,220})", cleaned_text, re.IGNORECASE)
    if achievement_match:
        achievement_excerpt = _normalize_excerpt(achievement_match.group(2), 90)
        if achievement_excerpt:
            questions.append(f"Tell me more about {achievement_excerpt}. What was your specific contribution and outcome?")

    if not questions:
        first_sentence = _normalize_excerpt(re.split(r"(?<=[.!?])\s+", cleaned_text)[0], 80)
        if first_sentence:
            questions.append(
                f"Your CV opens with experience related to {first_sentence}. "
                "Which part of that background best prepares you for this role?"
            )

    deduped: list[str] = []
    seen = set()
    for question in questions:
        normalized = question.strip().lower()
        if normalized and normalized not in seen:
            deduped.append(question.strip())
            seen.add(normalized)
        if len(deduped) >= max_questions:
            break
    return deduped
