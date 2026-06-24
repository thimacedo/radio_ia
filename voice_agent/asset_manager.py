"""Gerenciador de assets por programa.

Funções:
- load_assets(program) -> dict de caminhos de assets
"""

from pathlib import Path
import yaml


ASSETS_ROOT = Path("assets")
CONFIGS_ROOT = Path("configs")


def load_program_config(program: str) -> dict:
    cfg_path = CONFIGS_ROOT / f"{program}.yaml"
    if not cfg_path.exists():
        default = CONFIGS_ROOT / "default.yaml"
        if default.exists():
            cfg_path = default
        else:
            return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load_assets(program: str) -> dict:
    config = load_program_config(program)
    assets = {}
    assets_cfg = config.get("assets", {}) if isinstance(config, dict) else {}
    for key, fname in assets_cfg.items():
        if fname is None:
            continue
        p = ASSETS_ROOT / program / fname
        if not p.exists():
            # fallback to global assets directory
            p = ASSETS_ROOT / fname
        assets[key] = str(p) if p.exists() else None
    return assets


if __name__ == "__main__":
    print(load_assets("giro"))
