import pytest
from voice_agent import transcriber, audio_processor, error_detector
from pathlib import Path


def test_transcriber_fallback():
    # If whisper not installed, transcribe returns a list
    res = transcriber.transcribe.__call__ if False else transcriber.transcribe
    # call with non-existent file should raise
    with pytest.raises(FileNotFoundError):
        transcriber.transcribe("non_existent_file.wav")


def test_audio_processor_missing_file():
    with pytest.raises(Exception):
        audio_processor.process_audio("no_file.wav", "out.wav")


def test_error_detector_basic():
    segs = [{"start":0.0, "end":1.0, "text":"o o contrato"}, {"start":1.1, "end":2.0, "text":"o contrato"}]
    issues = error_detector.detect_issues(segs)
    assert any(i["type"] == "repeticao_palavra" for i in issues)
