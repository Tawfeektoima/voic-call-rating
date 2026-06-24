from pathlib import Path


def test_recording_ingestion_fixture_pack_is_available(
    recording_ingestion_fixture_root: Path,
    recording_ingestion_fixture_paths: dict[str, Path],
    recording_ingestion_sheet_rows: list[dict[str, str]],
    recording_ingestion_fixture_bytes: dict[str, bytes],
    recording_ingestion_fixed_now,
):
    assert recording_ingestion_fixture_root.is_dir()
    assert recording_ingestion_fixture_paths["sheet_rows"].is_file()
    assert recording_ingestion_fixture_paths["valid_audio_mp3"].is_file()
    assert recording_ingestion_fixture_paths["valid_audio_wav"].is_file()
    assert recording_ingestion_fixed_now.tzinfo is not None

    assert len(recording_ingestion_sheet_rows) >= 4
    assert recording_ingestion_sheet_rows[0]["CALL LINK"].startswith("https://archive.dial-fusion.com/")
    assert recording_ingestion_sheet_rows[2]["CALL LINK"] == ""
    assert recording_ingestion_sheet_rows[3]["CALL LINK"].startswith("https://unapproved.example.com/")

    assert recording_ingestion_fixture_bytes["valid_audio_mp3"].startswith(b"ID3")
    assert recording_ingestion_fixture_bytes["valid_audio_wav"].startswith(b"RIFF")
    assert len(recording_ingestion_fixture_bytes["valid_audio_mp3"]) > 1024
    assert len(recording_ingestion_fixture_bytes["valid_audio_wav"]) > 1024
    assert recording_ingestion_fixture_bytes["malformed_bytes"].startswith(b"NOT-AUDIO-BYTES")
    assert recording_ingestion_fixture_bytes["html_audio_header"].startswith(b"ID3<html>")
