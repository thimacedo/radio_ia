import os
import io
import re
import asyncio
import pathlib
import shutil
import edge_tts
from pydub import AudioSegment
from .llm_factory import LLMFactory
from .models import ProgramRecipe

class PipelineEngine:
    """
    Motor central unificado. Executa o ciclo de vida completo de um programa:
    1. Extração e Adaptação (Pauta -> TTS Format)
    2. Processamento IA (Reescrita Jornalística)
    3. Gravação (Síntese de Voz Edge-TTS)
    4. Edição (Montagem Pydub com Receita)
    5. Distribuição (Sincronização Drive)
    """
    def __init__(self, recipe: ProgramRecipe):
        self.recipe = recipe
        self.llm = LLMFactory()
        
        # Preparar diretórios locais
        self.txt_dir = self.recipe.local_work_dir / "1_txt_bruto"
        self.rev_dir = self.recipe.local_work_dir / "2_txt_revisado"
        self.aud_dir = self.recipe.local_work_dir / "3_audio_final"
        
        for d in [self.txt_dir, self.rev_dir, self.aud_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # 1. ADAPTAÇÃO & 2. PROCESSAMENTO (LLM)
    # ---------------------------------------------------------
    def process_text(self, raw_content: str) -> str:
        content = raw_content
        # 1. Adaptação (Hook específico do programa)
        if self.recipe.pre_process_hook:
            content = self.recipe.pre_process_hook(content)
            
        # 2. Processamento IA
        if self.recipe.system_prompt:
            print(f"    [{self.recipe.name}] Processando roteiro via IA...")
            revised_content = self.llm.ask(self.recipe.system_prompt, content)
            return revised_content
        else:
            return content

    # ---------------------------------------------------------
    # 3. GRAVAÇÃO (Síntese TTS)
    # ---------------------------------------------------------
    async def synthesize_chunk(self, text: str, voice: str) -> bytes:
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(text, voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio": 
                        audio_data += chunk["data"]
                return audio_data
            except Exception as e:
                print(f"      [!] Falha TTS ({attempt+1}/3): {e}")
                if attempt < 2: await asyncio.sleep(3 ** attempt)
        raise Exception("Falha persistente no TTS.")

    # ---------------------------------------------------------
    # 4. EDIÇÃO (Montagem Pydub)
    # ---------------------------------------------------------
    async def assemble_audio(self, parsed_blocks: list, global_voice_idx: int = 0) -> AudioSegment:
        combined = AudioSegment.empty()
        
        # Abertura
        if self.recipe.assembly.intro_vht and self.recipe.assembly.intro_vht.exists():
            combined += AudioSegment.from_mp3(str(self.recipe.assembly.intro_vht))

        # Estratégia de Vozes
        voices = self.recipe.voice_strategy.voices
        is_intra = self.recipe.voice_strategy.type == 'intra_file'
        
        current_voice = voices[global_voice_idx % len(voices)] if not is_intra else None

        for kind, content in parsed_blocks:
            if kind == "VHT":
                if content == "[Vh passagem]" and self.recipe.assembly.transition_vht:
                    combined += AudioSegment.from_mp3(str(self.recipe.assembly.transition_vht))
                # Outras vinhetas mapeadas internamente podem ser adicionadas aqui
            
            elif kind == "LOC":
                if is_intra:
                    # Alterna vozes dentro do bloco baseado na tag (ex: speaker1, speaker2)
                    speaker_id, texto = content
                    idx = 0 if speaker_id == "speaker1" else 1
                    voz = voices[idx % len(voices)]
                else:
                    # Voz única definida para o arquivo inteiro
                    texto = content
                    voz = current_voice
                
                audio_bytes = await self.synthesize_chunk(texto, voz)
                combined += AudioSegment.from_mp3(io.BytesIO(audio_bytes))

        # Encerramento
        if self.recipe.assembly.outro_vht and self.recipe.assembly.outro_vht.exists():
            combined += AudioSegment.from_mp3(str(self.recipe.assembly.outro_vht))
            
        # Trilha de Fundo (BG)
        if self.recipe.assembly.bg_music and self.recipe.assembly.bg_music.exists():
            bg = AudioSegment.from_mp3(str(self.recipe.assembly.bg_music))
            bg = bg - self.recipe.assembly.bg_volume_reduction_db
            # Loop bg se for menor que a locução
            while len(bg) < len(combined):
                bg += bg
            # Cortar BG do tamanho da locução e fazer fade out
            bg = bg[:len(combined)].fade_out(2000)
            combined = combined.overlay(bg)

        return combined

    # ---------------------------------------------------------
    # 5. DISTRIBUIÇÃO
    # ---------------------------------------------------------
    def distribute(self, local_mp3: pathlib.Path, subfolder: str = ""):
        dest_dir = self.recipe.drive_output_dir
        if subfolder:
            dest_dir = dest_dir / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / local_mp3.name
        shutil.copy2(local_mp3, dest_path)
        print(f"    [{self.recipe.name}] Distribuído para: {dest_path}")

    # ---------------------------------------------------------
    # ORQUESTRADOR
    # ---------------------------------------------------------
    async def run_file(self, file_path: pathlib.Path, file_idx: int = 0, subfolder: str = ""):
        print(f"\n[{self.recipe.name}] Iniciando: {file_path.name}")
        
        mp3_name = file_path.with_suffix(".mp3").name
        dest_dir = self.recipe.drive_output_dir
        if subfolder:
            dest_dir = dest_dir / subfolder
        dest_path = dest_dir / mp3_name

        if dest_path.exists():
            print(f"  [SKIP] {file_path.name} já existe no Drive.")
            return

        # 1 e 2
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        rev_text = self.process_text(raw_text)
        
        rev_path = self.rev_dir / file_path.name
        rev_path.write_text(rev_text, encoding="utf-8")
        
        # 3 e 4
        print(f"    [{self.recipe.name}] Gerando áudio e mixando...")
        if self.recipe.parse_hook:
            parsed_blocks = self.recipe.parse_hook(rev_text)
        else:
            parsed_blocks = [("LOC", rev_text)] # Fallback simples

        combined_audio = await self.assemble_audio(parsed_blocks, global_voice_idx=file_idx)
        
        out_path = self.aud_dir / mp3_name
        combined_audio.export(str(out_path), format="mp3", bitrate="192k")
        
        # 5. Distribuir
        self.distribute(out_path, subfolder)

    async def run_all(self):
        files = sorted([f for f in self.txt_dir.glob("*.txt") if not f.name.endswith(".bak")])
        print(f"=== {self.recipe.name}: Pipeline Integrado ===")
        print(f"Arquivos encontrados: {len(files)}\n")

        for idx, f in enumerate(files):
            # Tentar extrair subfolder (mes) do nome do arquivo, padrão Giro
            subfolder = ""
            month_match = re.search(r"-(\d{2})-", f.name)
            if month_match:
                month_map = {"01":"JAN","02":"FEV","03":"MAR","04":"ABR","05":"MAI","06":"JUN","07":"JUL","08":"AGO","09":"SET","10":"OUT","11":"NOV","12":"DEZ"}
                subfolder = month_map.get(month_match.group(1), "OUTROS")
            elif "2025" not in f.name and "2026" not in f.name:
                subfolder = "" # Padrão
            
            # Ajuste simples para o ano se estiver no nome
            year = "2025" if "2025" in f.name else ("2026" if "2026" in f.name else "")
            if year:
                subfolder = f"{year}/{subfolder}" if subfolder else year

            await self.run_file(f, file_idx=idx, subfolder=subfolder)
