import tempfile
import unittest
from unittest.mock import patch
from voice_agent import transcriber, audio_processor, error_detector
from voice_agent.runner import process_file
from pathlib import Path


class TestVoiceAgent(unittest.TestCase):

    def test_transcriber_fallback(self):
        # If whisper not installed, transcribe returns a list stub or raises if file is missing
        with self.assertRaises(FileNotFoundError):
            transcriber.transcribe("non_existent_file.wav")

    def test_audio_processor_missing_file(self):
        with self.assertRaises(Exception):
            audio_processor.process_audio("no_file.wav", "out.wav")

    def test_error_detector_basic(self):
        segs = [
            {
                "start": 0.0, "end": 5.0, "text": "o contrato de o contrato de",
                "words": [
                    {"start": 0.0, "end": 0.5, "text": "o"},
                    {"start": 0.6, "end": 1.2, "text": "contrato"},
                    {"start": 1.3, "end": 1.8, "text": "de"},
                    {"start": 2.8, "end": 3.3, "text": "o"},
                    {"start": 3.4, "end": 4.0, "text": "contrato"},
                    {"start": 4.1, "end": 4.6, "text": "de"}
                ]
            }
        ]
        issues = error_detector.detect_issues(segs)
        self.assertTrue(any(i["type"] == "retake_implicito" for i in issues))

    def test_process_file_awaiting_approval(self):
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        try:
            with patch("voice_agent.runner.audio_processor.process_audio", return_value=temp_file.name), \
                 patch("voice_agent.runner.transcriber.transcribe", return_value=[{"start": 0.0, "end": 1.0, "text": "o o teste"}]), \
                 patch("voice_agent.runner.error_detector.detect_issues", return_value=[{"type": "repeticao_palavra", "start": 0.0, "end": 1.0, "text": "o", "severity": "ATENCAO"}]), \
                 patch("voice_agent.runner.report_generator.generate_report_multipart", return_value=str(temp_file.name)), \
                 patch("voice_agent.runner.notifier.send_ntfy", return_value=True):
                result = process_file(temp_file.name, auto_approve=False)
                self.assertEqual(result["status"], "multi_jobs")
                self.assertTrue(result["jobs"])
                self.assertEqual(result["jobs"][0]["status"], "awaiting_approval")
                self.assertIn("report", result["jobs"][0])
                self.assertIn("clean_path", result["jobs"][0])
                self.assertTrue(result["jobs"][0]["issues"])
        finally:
            Path(temp_file.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
