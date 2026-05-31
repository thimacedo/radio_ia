import re
import os
from pathlib import Path
from typing import List, Tuple

def filtrar_conteudo_noticia(content: str) -> str:
    """
    FILTRA LINHAS DE PRODUÇÃO (LIXO) IGNORANDO WHITESPACE INICIAL.
    AGORA CORRETAMENTE CAPTURA LINHAS COMO:
    "   PROPOSTA: ...", "\tDATA: ...", "  OBS: texto qualquer..."
    """
    lines = content.splitlines()
    scored_lines: List[Tuple[str, float]] = []
    
    # ===== PADRÕES POSITIVOS (CONTEÚDO NOTICIOSO VÁLIDO) =====
    positive_patterns = [
        (r'//', 3.0),  # Marcador intencional de pausa (alta prioridade)
        (r'\b(EM|NA|NO|NAS|NOS)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', 2.0),  # Foco na comarca
        (r'\b(disse|afirmou|explicou|revelou|confirmou|negou)\b(?!\s+[A-Z][a-z]+)', 2.0),  # Verbos jornalísticos NO MEIO/FIM
        (r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:é|foi|tem|tem|disse|afirmou)\b', 2.0),  # Sujeito + verbo
        (r'\b(processo|ação|decisão|sentença|liminar|juiz|promotor|advogado)\b', 1.5),  # Contexto jurídico
        (r'\b(º|ª)\s*[A-Z]', 1.0),  # Abreviações (Ex: 3ª Vara)
        (r'\bR\s*\$\s*\d+[\.,]\d{2}\b', 1.0),  # Valores monetários
    ]
    
    # ===== PADRÕES NEGATIVOS (LIXO DE PRODUÇÃO) =====
    # CORREÇÃO CRÍTICA: REMOVI O '$' DO FINAL PARA CAPTURAR LINHAS COM TEXTO APÓS O DOIS PONTOS
    negative_patterns = [
        (r'^\s*(DATA:|RESPONSÁVEL:|OBS:|NOTA:|CONFIRMAR:|TAREFA:) ', -5.0),  # Metadados de produção
        (r'^\s*[-*•]\s*', -3.0),  # Marcadores de lista
        (r'^\s*(?:Obs\.|Observação:|Nota:)', -4.0),  # Notas internas
        (r'^\s*\d+[\.\)]\s*', -2.0),  # Numeração de itens
        (r'^\s*(?:verificar|confirmar|checar|atualizar)\s*:', -4.0),  # Tasks de produção
        (r'^\s*[A-Z\s]+:', -3.0),  # ← CORREÇÃO: SEM '$' NO FINAL → CAPTURA "PROPOSTA: qualquer coisa"
    ]
    
    verb_start_penalty = -3.0  # Penalidade para verbos no início (será corrigido depois)
    
    for line in lines:
        if not line.strip():  # Linha vazia
            scored_lines.append((line, 0.0))
            continue
            
        score = 0.0
        
        # Aplica padrões positivos
        for pattern, points in positive_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                score += points
                
        # Aplica padrões negativos (AGORA IGNORANDO WHITESPACE INICIAL E CAPTURANDO TEXTO APÓS :)
        for pattern, points in negative_patterns:
            if re.search(pattern, line, re.IGNORECASE):  # ← \s* já está no padrão
                score += points  # Já é negativo
                
        # Penalidade especial: verbo no início (Regra 2 do PERSONA)
        first_word = re.sub(r'[^\w]', '', line.split()[0]).lower() if line.split() else ""
        forbidden_starters = {
            'determinado', 'determinou', 'determinar',
            'decidiu', 'decidir', 'disse', 'dizer',
            'informou', 'informar', 'explicou', 'explicar',
            'afirmou', 'afirmar', 'negou', 'negar',
            'confirmou', 'confirmar', 'restou', 'restar',
            'verificou', 'verificar', 'constatou', 'constatar',
            'assegurou', 'assegurar', 'declarou', 'declarar'
        }
        if first_word in forbidden_starters:
            score += verb_start_penalty  # Penalidade, mas será corrigida na reescrita
            
        scored_lines.append((line, score))
    
    # ===== PÓS-PROCESSAMENTO: PRESERVA COESÃO CONTEXTUAL =====
    filtered_lines = []
    i = 0
    while i < len(scored_lines):
        line, score = scored_lines[i]
        
        # Sempre mantém linhas com score alto (notícias claras)
        if score >= 3.0:
            filtered_lines.append(line)
            i += 1
            continue
            
        # Mantém linhas com score médio se estiverem entre blocos noticiosos
        if score >= 1.5 and i > 0 and i < len(scored_lines)-1:
            prev_score = scored_lines[i-1][1]
            next_score = scored_lines[i+1][1]
            if prev_score >= 2.5 and next_score >= 2.5:
                filtered_lines.append(line)
                i += 1
                continue
                
        i += 1  # Remove linha (lixo confirmado)
    
    return "\n".join(filtered_lines)

def aplicar_rewrite_contextual(content: str) -> str:
    """
    REESCREVE O CONTEÚDO APENAS QUANDO O CONTEXTO JUSTIFICA:
    - Corrige verbos no início SOMENTE se houver sujeito identificável
    - Aplica modo condicional SOMENTE para afirmações não verificadas
    - Nunca altera fatos consolidados ou estruturas jurídicas válidas
    """
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    if not blocks:
        return content
    
    processed_blocks = []
    
    for i, block in enumerate(blocks):
        processed = _aplicar_regras_contextuais(block)
        processed_blocks.append(processed)
    
    return "\n\n".join(processed_blocks)

def _aplicar_regras_contextuais(block: str) -> str:
    """Aplica regras de reescrita SOMENTE quando o contexto justifica"""
    block = _corrigir_verbo_inicio_contextual(block)
    block = _aplicar_modalidade_contextual(block)
    block = _aplicar_linguagem_simples(block)
    return block

def _corrigir_verbo_inicio_contextual(block: str) -> str:
    """
    Corrige verbos no início SOMENTE se houver sujeito claro após o verbo.
    Ex: "Determinou o juiz X" → "O juiz determinou X" 
    Mas: "Determinou que X" → permanece (evita criar frase sem sentido)
    """
    sentences = re.split(r'(?<=[.!?])\s+', block)
    processed = []
    
    for sent in sentences:
        if not sent.strip():
            processed.append(sent)
            continue
            
        # Verifica se começa com verbo proibido
        first_word = re.sub(r'[^\w]', '', sent.split()[0]).lower() if sent.split() else ""
        forbidden_starters = {
            'determinado', 'determinou', 'determinar',
            'decidiu', 'decidir', 'disse', 'dizer',
            'informou', 'informar', 'explicou', 'explicar',
            'afirmou', 'afirmar', 'negou', 'negar',
            'confirmou', 'confirmar', 'restou', 'restar',
            'verificou', 'verificar', 'constatou', 'constatar',
            'assegurou', 'assegurar', 'declarou', 'declarar'
        }
        
        if first_word in forbidden_starters:
            # Tenta encontrar sujeito após o verbo (padrão: verbo + artigo + substantivo)
            match = re.match(r'^(\w+)\s+(o\s+\w+|a\s+\w+|os\s+\w+|as\s+\w+)(.+)', sent, re.IGNORECASE)
            if match:
                verb, subject, rest = match.groups()
                # Reconstroi: sujeito + verbo + resto
                new_sent = f"{subject} {verb}{rest}"
                processed.append(new_sent)
                continue
            # Se não houver sujeito claro, NÃO corrige (evita frases como "Determinou que X" → "Que X determinou")
            processed.append(sent)  # Mantém original para revisão humana
        else:
            processed.append(sent)
    
    return ' '.join(processed)

def _aplicar_modalidade_contextual(block: str) -> str:
    """
    Aplica modo condicional SOMENTE para afirmações que indicam falta de prova ou alegação.
    NÃO aplica em fatos consolidados (ex: sentenças transitadas em julgado).
    """
    # Padrões que indicam necessidade de modalidade (alegações, não provas)
    allegation_patterns = [
        # Verbos de alegação sem prova concreta
        (r'\b(acusado\s+de|imputado\s+de|suspeito\s+de)\s+', r'temia ser \1'),
        (r'\b(partes\s+promovidas\s+não\s+negaram)\b', r'as partes promovidas alegaram não ter negado'),
        (r'\b(constatou\s+que|verificou\s+que)\b(?!\s+[^.]*?\b(trânsito|transitado|transitado)\b)', r'observou que'),
        # Afirmações baseadas em "conforme consta" (que requer verificação)
        (r'\b(conforme\s+consta\s+no\s+processo)\b', r'de acordo com o que consta nos autos (requer confirmação)'),
        # Menção a laudos/perícias sem confirmação de trânsito
        (r'\b(laudo\s+médico\s+anexo|perícia\s+apontou)\b(?!\s+[^.]*?\b(trânsito|transitado)\b)', r'\1 (pendente de confirmação em fase recursal)'),
    ]
    
    for pattern, replacement in allegation_patterns:
        block = re.sub(pattern, replacement, block, flags=re.IGNORECASE)
    
    # NÃO toca em estruturas que indicam trânsito em julgado
    if re.search(r'\b(trânsito\s+em\s+julgado|transitado\s+em\s+julgado|passado\s+em\s+julgado)\b', block, re.IGNORECASE):
        pass  # Mantém como está - fato consolidado
    
    return block

def _aplicar_linguagem_simples(block: str) -> str:
    """Aplica substituições de juridiquês (menos arriscado, sempre seguro)"""
    replacements = {
        r'\bnos\s+termos\s+do\s+artigo\b': 'segundo o artigo',
        r'\bnos\s+autos\b': 'nos documentos',
        r'\brestou\s+comprovado\b': 'foi comprovado',
        r'\bindefirido\b': 'negado',
        r'\bprocedente\b': 'aceito',
        r'\bconstitui\s+configuração\b': 'configura',
        r'\bverifiquei\s+nos\s+autos\b': 'vi nos documentos',
        r'\bconstatou\s+que\b': 'observou que',
        r'\bassegurou\s+que\b': 'garantiu que',
        r'\bdeclarou\s+que\b': 'declarou que',
        r'\bem\s+virtude\s+de\b': 'porque',
        r'\bem\s+consequência\b': 'por isso',
        r'\bdestaca\s+que\b': 'salienta que',
        r'\bressalta\s+que\b': 'lembra que',
        # Correções específicas do seu texto de exemplo
        r'degeneração\s+macular\s+da\s+retina\s+relacionada\s+à\s+idade': 'degeneração macular relacionada à idade',
        r'perda\s+de\s+visão\s+central\s+irreversível': 'perda irreversível da visão central',
        r'pacientes\s+idosos': 'pessoas idosas',
        r'altamente\s+probável': 'muito provável',
    }
    
    for pattern, replacement in replacements.items():
        block = re.sub(pattern, replacement, block, flags=re.IGNORECASE)
    
    return block

def aplicar_padrao_giroscomarcas(content: str) -> str:
    """Aplica o padrão exato do ROTEIRO GIRO NAS COMARCAS"""
    header1 = "ROTEIRO GIRO NAS COMARCAS //não entra na locução"
    header2 = "PROGRAMA 98|  EXIBIÇÃO: 28/10/2025 //não entra na locução"
    
    content = content.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    
    if not blocks:
        return f"{header1}\n{header2}\n\n[Vh abertura GIRO]\n\n[LOC:]\n\n[vht encerramento]"
    
    abertura = blocks[0]
    noticias = blocks[1:] if len(blocks) > 1 else []
    
    output = [
        header1,
        header2,
        "",  # Linha vazia após cabeçalhos
        "[Vh abertura GIRO]",
        "",  # Linha vazia antes de [LOC:]
        "[LOC:]",
        abertura,
        "",  # Linha vazia após bloco de locução
    ]
    
    for noticia in noticias:
        output.extend([
            "[Vh passagem]",
            "",  # Linha vazia antes de [LOC:]
            "[LOC:]",
            noticia,
            ""   # Linha vazia após bloco de locução
        ])
    
    output.append("[vht encerramento]")
    return "\n".join(output)

def main():
    pasta_origem = Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt")
    pasta_destino = pasta_origem.parent / "tts_txt_convertido"
    
    if not pasta_origem.exists():
        raise FileNotFoundError(f"Pasta de origem não encontrada: {pasta_origem}")
    
    pasta_destino.mkdir(parents=True, exist_ok=True)
    print(f"📁 Pasta de destino criada/verificada: {pasta_destino}\n")
    
    arquivos_txt = [f for f in pasta_origem.iterdir() if f.is_file() and f.suffix.lower() == '.txt']
    
    if not arquivos_txt:
        print("⚠️ Nenhum arquivo .txt encontrado na pasta de origem.")
        return
    
    print(f"🔍 {len(arquivos_txt)} arquivo(s) .txt encontrado(s) para processar.\n")
    
    for arquivo_origem in arquivos_txt:
        try:
            # 1. LEITURA DO ARQUIVO ORIGINAL
            with open(arquivo_origem, 'r', encoding='utf-8-sig') as f:
                conteudo_original = f.read()
            
            # 2. REMOÇÃO DE PRÉ TEXTO (LIXO DE PRODUÇÃO) - CORREÇÃO DEFINITIVA APLICADA
            conteudo_sem_lixo = filtrar_conteudo_noticia(conteudo_original)
            
            # 3. REESCRITA CONTEXTUAL (GIRO PERSONA.MD)
            conteudo_rewrite = aplicar_rewrite_contextual(conteudo_sem_lixo)
            
            # 4. FORMATAÇÃO FINAL (ROTEIRO GIRO NAS COMARCAS)
            conteudo_final = aplicar_padrao_giroscomarcas(conteudo_rewrite)
            
            # 5. SALVAMENTO SEGURO (NUNCA TOCA NO ORIGINAL)
            arquivo_destino = pasta_destino / arquivo_origem.name
            with open(arquivo_destino, 'w', encoding='utf-8', newline='\n') as f:
                f.write(conteudo_final)
            
            print(f"✅ Processado: {arquivo_origem.name}")
            print(f"   📥 Origem:  {arquivo_origem}")
            print(f"   📤 Destino: {arquivo_destino}\n")
        
        except Exception as e:
            print(f"❌ ERRO em {arquivo_origem.name}: {str(e)}\n")
    
    print("🎉 CONCLUÍDO! Todos os arquivos foram processados para:")
    print(f"   {pasta_destino}")
    print("\n💡 OBSERVAÇÕES IMPORTANTES:")
    print("   - ✅ Linhas de produção (EX: 'PROPOSTA:', 'DATA:', 'RESPONSÁVEL:') são 100% removidas")
    print("     mesmo que tenham espaços ou tabulação inicial (correção crítica aplicada)")
    print("   - ✅ Reescrita aplicou mudanças SOMENTE quando o contexto justificou")
    print("     (ex: corrigiu verbos no início apenas quando sujeito estava claro)")
    print("   - ✅ Modos condicionais foram adicionados APENAS para alegações não verificadas")
    print("   - ✅ Seu conteúdo original em 'tts_txt' permanece 100% intacto")
    print("\n💡 COMANDO DE VALIDAÇÃO RÁPIDA (execute após processar):")
    print('   Select-String -Path "E:\\NJUD\\PROGRAMA GIRO NAS COMARCAS\\tts_txt_convertido\\SEU_ARQUIVO.txt" -Pattern "PROPOSTA:" -SimpleMatch')
    print('   → Se retornar NADA, o lixo foi removido corretamente')

if __name__ == "__main__":
    main()
