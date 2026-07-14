"""Gera relatórios HTML/JSON para aprovação.

Funções:
- generate_report(program, clean_wav, segments, issues, out_path) -> out_html_path
"""

from pathlib import Path
from typing import List, Dict


import json

def generate_report(program: str, clean_wav: str, segments: List[Dict], issues: List[Dict], out_path: str) -> str:
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    # Relatório mínimo: JSON embutido em HTML
    html = """
    <html><head><meta charset='utf-8'><title>Relatório</title></head><body>
    <h1>Relatório - {program}</h1>
    <p>Áudio: {clean}</p>
    <h2>Issues</h2>
    <pre>{issues}</pre>
    </body></html>
    """.format(program=program, clean=clean_wav, issues=str(issues))
    out_p.write_text(html, encoding="utf-8")
    return str(out_p)

def generate_report_multipart(program: str, cabeca_wav: str, off_wav: str, issues: List[Dict], cabeca_cuts: List[Dict], off_cuts: List[Dict], out_path: str) -> str:
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    cuts_json = json.dumps({
        "cabeca_cuts": cabeca_cuts,
        "off_cuts": off_cuts
    }, indent=2)
    
    html = f"""
    <html><head><meta charset='utf-8'><title>Relatório Multipart</title></head><body>
    <h1>Relatório Multipart - {program}</h1>
    <p><b>Cabeça:</b> {cabeca_wav}</p>
    <p><b>Off:</b> {off_wav}</p>
    <h2>Cortes Sugeridos (Copie este JSON para o Dashboard)</h2>
    <pre>{cuts_json}</pre>
    <h2>Detalhes das Issues</h2>
    <pre>{json.dumps(issues, indent=2, ensure_ascii=False)}</pre>
    </body></html>
    """
    out_p.write_text(html, encoding="utf-8")
    return str(out_p)

if __name__ == "__main__":
    print(generate_report("demo", "clean.wav", [], [], "reports/demo_report.html"))
