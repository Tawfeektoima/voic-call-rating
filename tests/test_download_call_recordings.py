from __future__ import annotations

from pathlib import Path

import httpx

from scripts.download_call_recordings import build_google_csv_export_url, download_recordings


SHEET_URL = "https://docs.google.com/spreadsheets/d/test-sheet-id/edit?gid=0#gid=0"
RECORDING_URL = "https://archive.dial-fusion.com/archive/20260504_15030300m45s_5209776179_NoCallerOnLine_Agent17.mp3"


def test_build_google_csv_export_url_uses_sheet_id_and_gid():
    assert build_google_csv_export_url(SHEET_URL) == (
        "https://docs.google.com/spreadsheets/d/test-sheet-id/export?format=csv&gid=0"
    )


def test_downloads_call_link_and_skips_it_on_a_later_run(tmp_path: Path):
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.host == "docs.google.com":
            return httpx.Response(
                200,
                text=(
                    "DATE,CODE,CRDTS,NAME,CALL LINK,SCORE,WEAKNESS\n"
                    f"4/22/2026,489,67191,Agent One,{RECORDING_URL},91,Follow up\n"
                ),
                headers={"content-type": "text/csv"},
            )
        if str(request.url) == RECORDING_URL:
            return httpx.Response(
                200,
                content=b"ID3test-audio",
                headers={"content-type": "audio/mpeg"},
            )
        return httpx.Response(404)

    output_dir = tmp_path / "call_recordings"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first_results = download_recordings(SHEET_URL, output_dir=output_dir, client=client)
        second_results = download_recordings(SHEET_URL, output_dir=output_dir, client=client)

    assert [result.status for result in first_results] == ["downloaded"]
    assert first_results[0].filename == "20260504_15030300m45s_5209776179_NoCallerOnLine_Agent17.mp3"
    assert (output_dir / first_results[0].filename).read_bytes() == b"ID3test-audio"
    assert (output_dir / "download_state.json").is_file()
    assert [result.status for result in second_results] == ["skipped"]
    assert requested_urls.count(RECORDING_URL) == 1


def test_rejects_html_response_and_keeps_no_partial_file(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "docs.google.com":
            return httpx.Response(
                200,
                text=f"CALL LINK,CRDTS\n{RECORDING_URL},67191\n",
                headers={"content-type": "text/csv"},
            )
        return httpx.Response(
            200,
            text="Not an audio recording",
            headers={"content-type": "text/html"},
        )

    output_dir = tmp_path / "call_recordings"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = download_recordings(SHEET_URL, output_dir=output_dir, client=client)

    assert [result.status for result in results] == ["failed"]
    assert list(output_dir.glob("*.part")) == []
    assert list(output_dir.glob("*.mp3")) == []


def test_adds_a_suffix_when_two_rows_would_save_to_the_same_filename(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "docs.google.com":
            return httpx.Response(
                200,
                text=(
                    "CALL LINK,CRDTS\n"
                    f"{RECORDING_URL},67191\n"
                    f"{RECORDING_URL},67192\n"
                ),
                headers={"content-type": "text/csv"},
            )
        if str(request.url) == RECORDING_URL:
            return httpx.Response(
                200,
                content=b"ID3test-audio",
                headers={"content-type": "audio/mpeg"},
            )
        return httpx.Response(404)

    output_dir = tmp_path / "call_recordings"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = download_recordings(SHEET_URL, output_dir=output_dir, client=client)

    assert [result.status for result in results] == ["downloaded", "downloaded"]
    assert results[0].filename == "20260504_15030300m45s_5209776179_NoCallerOnLine_Agent17.mp3"
    assert results[1].filename is not None
    assert results[1].filename.startswith(
        "20260504_15030300m45s_5209776179_NoCallerOnLine_Agent17-"
    )
    assert results[1].filename.endswith(".mp3")


def test_rejects_recordings_from_hosts_outside_the_allowlist(tmp_path: Path):
    disallowed_url = "https://evil.example.com/archive/test.mp3"
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.host == "docs.google.com":
            return httpx.Response(
                200,
                text=f"CALL LINK,CRDTS\n{disallowed_url},67191\n",
                headers={"content-type": "text/csv"},
            )
        return httpx.Response(200, content=b"not-used", headers={"content-type": "audio/mpeg"})

    output_dir = tmp_path / "call_recordings"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = download_recordings(
            SHEET_URL,
            output_dir=output_dir,
            allowed_hosts=("archive.dial-fusion.com",),
            client=client,
        )

    assert [result.status for result in results] == ["failed"]
    assert "not allowed" in (results[0].detail or "").lower()
    assert requested_urls == [
        "https://docs.google.com/spreadsheets/d/test-sheet-id/export?format=csv&gid=0"
    ]
    assert not list(output_dir.glob("*.mp3"))
    assert not list(output_dir.glob("*.part"))
    assert not (output_dir / "download_state.json").exists()
