"""Carregador de config de programa (YAML) com defaults.
"""

from pathlib import Path
import yaml

CONFIGS_ROOT = Path("configs")


def load_program(program: str) -> dict:
    p = CONFIGS_ROOT / f"{program}.yaml"
    if not p.exists():
        p = CONFIGS_ROOT / "default.yaml"
        if not p.exists():
            return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_voice_edit_config(program: str) -> dict:
    cfg = load_program(program)
    return cfg.get("voice_edit", {}) if isinstance(cfg, dict) else {}


if __name__ == "__main__":
    print(load_program("giro"))
