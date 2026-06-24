"""Download audio recordings linked from a Google Sheet's ``CALL LINK`` column.

The command is intentionally independent of the web application and database: it
only reads the sheet, downloads recordings into the project's upload folder, and
persists a small local manifest so subsequent runs skip already saved links.

Example:
    python scripts/download_call_recordings.py --sheet-url "https://docs.google.com/spreadsheets/d/.../edit?gid=0"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import httpx


DEFAULT_OUTPUT_DIR = Path("uploads") / "CB calls"
DEFAULT_ALLOWED_HOSTS = ("archive.dial-fusion.com",)
DEFAULT_MAX_FILE_SIZE_MB = 100
DEFAULT_TIMEOUT_SECONDS = 45
MAX_REDIRECTS = 5

CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
}
ALLOWED_EXTENSIONS = frozenset(CONTENT_TYPE_EXTENSIONS.values())
WINDOWS_RESERVED_FILENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class DownloadError(RuntimeError):
    """A source row could not be safely downloaded."""


@dataclass(frozen=True)
class SheetCall:
    row_number: int
    call_link: str
    source_reference: str


@dataclass(frozen=True)
class DownloadResult:
    row_number: int
    source_reference: str
    status: str
    filename: str | None = None
    detail: str | None = None


def _normalise_header(header: str | None) -> str:
    return " ".join((header or "").strip().upper().split())


def build_google_csv_export_url(sheet_url: str) -> str:
    """Return the Google CSV export URL for a shared Google Sheet URL."""
    parsed = urlparse(sheet_url)
    match = re.search(r"/spreadsheets/d/([^/]+)", parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "docs.google.com" or not match:
        raise ValueError("--sheet-url must be a Google Sheets HTTPS URL.")

    sheet_id = match.group(1)
    gid = parse_qs(parsed.query).get("gid", ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def fetch_sheet_calls(client: httpx.Client, sheet_url: str) -> list[SheetCall]:
    """Read non-empty CALL LINK values from the sheet's first/header row."""
    response = client.get(build_google_csv_export_url(sheet_url), follow_redirects=True)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    if not reader.fieldnames:
        raise DownloadError("The sheet export is empty or does not contain a header row.")

    field_by_normalised_name = {
        _normalise_header(field_name): field_name for field_name in reader.fieldnames if field_name
    }
    call_link_field = field_by_normalised_name.get("CALL LINK")
    if not call_link_field:
        raise DownloadError("The sheet must contain a column named CALL LINK.")

    crdts_field = field_by_normalised_name.get("CRDTS")
    date_field = field_by_normalised_name.get("DATE")
    code_field = field_by_normalised_name.get("CODE")
    name_field = field_by_normalised_name.get("NAME")

    calls: list[SheetCall] = []
    for row_number, row in enumerate(reader, start=2):
        call_link = (row.get(call_link_field) or "").strip()
        if not call_link:
            continue

        source_reference = (row.get(crdts_field) or "").strip() if crdts_field else ""
        if not source_reference:
            identity_parts = [
                (row.get(date_field) or "").strip() if date_field else "",
                (row.get(code_field) or "").strip() if code_field else "",
                (row.get(name_field) or "").strip() if name_field else "",
                call_link,
            ]
            source_reference = "|".join(identity_parts)

        calls.append(SheetCall(row_number, call_link, source_reference))

    return calls


def _validate_recording_url(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise DownloadError("Recording link must use HTTPS.")
    if parsed.hostname.lower() not in allowed_hosts:
        raise DownloadError(f"Recording host '{parsed.hostname}' is not allowed.")


def _extension_from_response(response: httpx.Response, final_url: str) -> str:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]

    candidate = Path(urlparse(final_url).path).suffix.lower()
    if candidate in ALLOWED_EXTENSIONS:
        return candidate
    return ".audio"


def _validate_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
    if content_type and not (content_type.startswith("audio/") or content_type == "application/octet-stream"):
        raise DownloadError(f"Recording endpoint returned unsupported content type '{content_type}'.")


def _sanitise_filename_component(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(". ")
    if not cleaned:
        return ""
    if cleaned.upper() in WINDOWS_RESERVED_FILENAMES:
        return f"_{cleaned}"
    return cleaned


def _filename_from_url(final_url: str, extension: str, fallback_key: str) -> str:
    raw_name = Path(urlparse(final_url).path).name
    if raw_name:
        candidate_stem = _sanitise_filename_component(Path(raw_name).stem)
        candidate_extension = Path(raw_name).suffix.lower()
        if candidate_stem:
            if candidate_extension not in ALLOWED_EXTENSIONS:
                candidate_extension = extension
            return f"{candidate_stem}{candidate_extension}"
    return f"recording-{fallback_key[:20]}{extension}"


def _resolve_output_path(output_dir: Path, preferred_filename: str, fallback_key: str) -> tuple[str, Path]:
    preferred_path = output_dir / preferred_filename
    if not preferred_path.exists():
        return preferred_filename, preferred_path

    stem = Path(preferred_filename).stem
    suffix = Path(preferred_filename).suffix
    alternate_filename = f"{stem}-{fallback_key[:8]}{suffix}"
    return alternate_filename, output_dir / alternate_filename


def _safe_response_for_url(client: httpx.Client, url: str, allowed_hosts: set[str]) -> tuple[httpx.Response, str]:
    """Open a streaming response while validating every redirect destination."""
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_recording_url(current_url, allowed_hosts)
        request = client.build_request("GET", current_url)
        response = client.send(request, stream=True, follow_redirects=False)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response, current_url

        location = response.headers.get("location")
        response.close()
        if not location:
            raise DownloadError("Recording endpoint returned a redirect without a destination.")
        current_url = urljoin(current_url, location)

    raise DownloadError(f"Recording link exceeded the {MAX_REDIRECTS} redirect limit.")


def _record_key(call: SheetCall) -> str:
    material = f"{call.source_reference}\n{call.call_link}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _load_state(state_path: Path) -> dict[str, dict[str, Any]]:
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DownloadError(f"Could not read download state file: {exc}") from exc
    if not isinstance(data, dict):
        raise DownloadError("Download state file must contain a JSON object.")
    return data


def _write_state(state_path: Path, state: dict[str, dict[str, Any]]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(prefix=".download_state-", suffix=".tmp", dir=state_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_path, state_path)
    except Exception:
        Path(temporary_path).unlink(missing_ok=True)
        raise


def _download_call(
    client: httpx.Client,
    call: SheetCall,
    output_dir: Path,
    allowed_hosts: set[str],
    max_bytes: int,
) -> tuple[str, int, str]:
    response, final_url = _safe_response_for_url(client, call.call_link, allowed_hosts)
    try:
        response.raise_for_status()
        _validate_content_type(response)

        extension = _extension_from_response(response, final_url)
        record_key = _record_key(call)
        preferred_filename = _filename_from_url(final_url, extension, record_key)
        filename, final_path = _resolve_output_path(output_dir, preferred_filename, record_key)
        temporary_path = output_dir / f".{filename}.part"
        bytes_written = 0
        digest = hashlib.sha256()

        try:
            with temporary_path.open("wb") as audio_file:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise DownloadError("Recording exceeds the configured maximum file size.")
                    audio_file.write(chunk)
                    digest.update(chunk)
            if bytes_written == 0:
                raise DownloadError("Recording download was empty.")
            os.replace(temporary_path, final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        return filename, bytes_written, digest.hexdigest()
    finally:
        response.close()


def download_recordings(
    sheet_url: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    allowed_hosts: Iterable[str] = DEFAULT_ALLOWED_HOSTS,
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    limit: int | None = None,
    client: httpx.Client | None = None,
) -> list[DownloadResult]:
    """Download new recordings and return one result for each selected source row."""
    if max_file_size_mb <= 0:
        raise ValueError("max_file_size_mb must be greater than zero.")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero when supplied.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "download_state.json"
    state = _load_state(state_path)
    permitted_hosts = {host.strip().lower() for host in allowed_hosts if host.strip()}
    if not permitted_hosts:
        raise ValueError("At least one allowed recording host is required.")

    owns_client = client is None
    active_client = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))
    try:
        calls = fetch_sheet_calls(active_client, sheet_url)
        if limit is not None:
            calls = calls[:limit]

        results: list[DownloadResult] = []
        max_bytes = max_file_size_mb * 1024 * 1024
        for call in calls:
            key = _record_key(call)
            previous = state.get(key)
            if previous and (output_dir / str(previous.get("filename", ""))).is_file():
                results.append(DownloadResult(call.row_number, call.source_reference, "skipped", previous["filename"]))
                continue

            try:
                filename, byte_size, file_hash = _download_call(
                    active_client, call, output_dir, permitted_hosts, max_bytes
                )
            except (DownloadError, httpx.HTTPError, OSError) as exc:
                results.append(DownloadResult(call.row_number, call.source_reference, "failed", detail=str(exc)))
                continue

            state[key] = {
                "filename": filename,
                "source_reference": call.source_reference,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "byte_size": byte_size,
                "sha256": file_hash,
            }
            _write_state(state_path, state)
            results.append(DownloadResult(call.row_number, call.source_reference, "downloaded", filename))

        return results
    finally:
        if owns_client:
            active_client.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet-url", required=True, help="Shared Google Sheet URL containing the CALL LINK column.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Folder for downloaded audio files.")
    parser.add_argument("--allow-host", action="append", default=list(DEFAULT_ALLOWED_HOSTS), help="Allowed recording host; repeat for more hosts.")
    parser.add_argument("--max-file-size-mb", type=int, default=DEFAULT_MAX_FILE_SIZE_MB)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--limit", type=int, help="Only process the first N non-empty CALL LINK rows.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        results = download_recordings(
            sheet_url=args.sheet_url,
            output_dir=args.output_dir,
            allowed_hosts=args.allow_host,
            max_file_size_mb=args.max_file_size_mb,
            timeout_seconds=args.timeout_seconds,
            limit=args.limit,
        )
    except (DownloadError, ValueError, httpx.HTTPError) as exc:
        print(f"Download setup failed: {exc}", file=sys.stderr)
        return 2

    counts = {"downloaded": 0, "skipped": 0, "failed": 0}
    for result in results:
        counts[result.status] += 1
        reference = result.source_reference or f"row {result.row_number}"
        if result.status == "downloaded":
            print(f"Downloaded row {result.row_number} ({reference}) -> {result.filename}")
        elif result.status == "skipped":
            print(f"Skipped row {result.row_number} ({reference}); already downloaded as {result.filename}")
        else:
            print(f"Failed row {result.row_number} ({reference}): {result.detail}", file=sys.stderr)

    print(
        "Completed: "
        f"{counts['downloaded']} downloaded, {counts['skipped']} skipped, {counts['failed']} failed."
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
