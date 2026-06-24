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
        segs = [{"start": 0.0, "end": 1.0, "text": "o o contrato"}, {"start": 1.1, "end": 2.0, "text": "o contrato"}]
        issues = error_detector.detect_issues(segs)
        self.assertTrue(any(i["type"] == "repeticao_palavra" for i in issues))

    def test_process_file_awaiting_approval(self):
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        try:
            with patch("voice_agent.runner.audio_processor.process_audio", return_value=temp_file.name), \
                 patch("voice_agent.runner.transcriber.transcribe", return_value=[{"start": 0.0, "end": 1.0, "text": "o o teste"}]), \
                 patch("voice_agent.runner.error_detector.detect_issues", return_value=[{"type": "repeticao_palavra", "start": 0.0, "end": 1.0, "text": "o", "severity": "ATENCAO"}]), \
                 patch("voice_agent.runner.report_generator.generate_report", return_value=str(temp_file.name)), \
                 patch("voice_agent.runner.notifier.send_ntfy", return_value=True):
                result = process_file(temp_file.name, auto_approve=False)
                self.assertEqual(result["status"], "awaiting_approval")
                self.assertIn("report", result)
                self.assertIn("clean_path", result)
                self.assertTrue(result["issues"])
        finally:
            Path(temp_file.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
