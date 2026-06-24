import pathlib
from core.models import ProgramRecipe
from core.engine import PipelineEngine


def run_pipeline(prog_id: str, logger=print):
    logger(f"[core.runner] Iniciando pipeline para {prog_id}")
    # Este runner espera que cada módulo implemente um objeto de receita `receita_<prog_id>`
    # no seu próprio namespace. Aqui suportamos Giro, Boletins e NJUD por convenção.
    try:
        if prog_id == "giro":
            from modules.giro.giro_pipeline import receita_giro
            recipe = receita_giro
        elif prog_id in ["boletins", "boletim", "noticias_da_hora"]:
            from modules.boletins.boletins_pipeline import receita_boletins
            recipe = receita_boletins
        elif prog_id in ["njud", "jornal"]:
            from modules.jornal.njud_pipeline import receita_njud
            recipe = receita_njud
        else:
            raise ImportError(f"Pipeline não configurado para '{prog_id}'")
    except Exception as e:
        logger(f"[core.runner] ERRO ao carregar pipeline: {e}")
        return

    engine = PipelineEngine(recipe)
    try:
        import asyncio
        asyncio.run(engine.run_all())
    except Exception as e:
        logger(f"[core.runner] ERRO durante execução do pipeline: {e}")
