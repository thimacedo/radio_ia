import json
import os
from threading import Lock

class VoiceQueue:
    """Rotating queue for TTS voices.

    The queue cycles through the list defined in `autonomous_config.yaml`.
    It is thread‑safe and can be reset on each execution (no persistence).
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, config_path: str = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VoiceQueue, cls).__new__(cls)
                cls._instance._init(config_path)
        return cls._instance

    def _init(self, config_path: str = None):
        default_voices = [
            "pt-BR-FranciscaNeural",
            "pt-BR-AntonioNeural",
            "pt-BR-ElzaNeural",
            "pt-BR-ThalitaNeural",
        ]
        self._index = 0
        self._voices = default_voices
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._voices = cfg.get("voices", default_voices)
                self._index = cfg.get("rotation_index", 0) % len(self._voices)
            except Exception as e:
                print(f"[WARN] Failed to load autonomous_config.yaml: {e}")

    def next_voice(self) -> str:
        voice = self._voices[self._index]
        self._index = (self._index + 1) % len(self._voices)
        return voice

    def current_state(self) -> dict:
        return {"rotation_index": self._index, "voices": self._voices}
