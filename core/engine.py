import os
import io
import re
import json
import asyncio
import pathlib
import shutil
import edge_tts
from pydub import AudioSegment
from .llm_factory import LLMFactory
from .models import ProgramRecipe
from .best_practices import retry_async, aplicar_pronuncia

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
    @retry_async(retries=3, backoff=1.0)
    async def synthesize_chunk(self, text: str, voice: str) -> bytes:
        # Aplicar pronúncia fonética nas siglas antes de enviar ao Edge TTS
        text_fonetizado = aplicar_pronuncia(text)
        communicate = edge_tts.Communicate(text_fonetizado, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": 
                audio_data += chunk["data"]
        if not audio_data:
            raise Exception("Nenhum dado de áudio retornado pelo Edge TTS.")
        return audio_data

    # ---------------------------------------------------------
    # 4. EDIÇÃO (Montagem Pydub - Audio as Text)
    # ---------------------------------------------------------
    async def assemble_audio(self, parsed_blocks: list, global_voice_idx: int = 0) -> AudioSegment:
        combined = AudioSegment.empty()
        
        # Carregar Perfil (JSON)
        profile = {}
        if self.recipe.assembly.profile_path and self.recipe.assembly.profile_path.exists():
            with open(self.recipe.assembly.profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                
        assets_map = profile.get("assets", {})
        trilhas_map = profile.get("trilhas", {})
        config = profile.get("configuracoes_mixagem", {
            "volume_bg_base": -5,
            "volume_bg_ducking": -18,
            "tempo_fade_in_ms": 2000,
            "tempo_fade_out_ms": 3000,
            "reduzir_bg_durante_fala": True
        })

        # Estratégia de Vozes
        voices = self.recipe.voice_strategy.voices
        is_intra = self.recipe.voice_strategy.type == 'intra_file'
        current_voice = voices[global_voice_idx % len(voices)] if not is_intra else None
        
        # Controle de Trilha de Fundo (BG)
        bg_audio = None
        bg_active = False
        speech_timeline = AudioSegment.empty() # Para calcular o tamanho exato da fala sob a trilha

        # Loop de Construção (Audio-as-Text)
        for kind, content in parsed_blocks:
            if kind == "ASSET":
                asset_key = content.strip()
                asset_path = assets_map.get(asset_key)
                
                # Se há uma trilha tocando, precisamos mixar o speech_timeline acumulado antes de colar o asset (para o asset não ficar sobre a trilha, conforme regra do usuário)
                if bg_active and len(speech_timeline) > 0:
                    # Cortar e mixar trilha
                    bg_snippet = bg_audio[:len(speech_timeline)]
                    if config["reduzir_bg_durante_fala"]:
                        bg_snippet = bg_snippet + config["volume_bg_ducking"]
                    else:
                        bg_snippet = bg_snippet + config["volume_bg_base"]
                        
                    bg_snippet = bg_snippet.fade_in(config["tempo_fade_in_ms"]).fade_out(config["tempo_fade_out_ms"])
                    mixed_speech = speech_timeline.overlay(bg_snippet)
                    combined += mixed_speech
                    
                    # Resetar state da trilha para a próxima fala
                    speech_timeline = AudioSegment.empty()
                    bg_audio = bg_audio[len(speech_timeline):] # avança a agulha da trilha
                
                # Inserir o Asset puro (sem BG por cima)
                if asset_path and os.path.exists(asset_path):
                    asset_segment = AudioSegment.from_mp3(asset_path)
                    
                    # Se não havia BG ativo, o speech acumulado vai seco mesmo
                    if not bg_active and len(speech_timeline) > 0:
                        combined += speech_timeline
                        speech_timeline = AudioSegment.empty()
                        
                    combined += asset_segment
                else:
                    print(f"      [!] Aviso: Asset '{asset_key}' não encontrado no caminho: {asset_path}")
            
            elif kind == "TRILHA":
                cmd = content.strip().upper()
                if cmd == "LIGAR":
                    bg_path = trilhas_map.get("BG_PADRAO")
                    if bg_path and os.path.exists(bg_path):
                        bg_audio = AudioSegment.from_mp3(bg_path)
                        # Loop mágico para garantir que o BG seja gigantesco
                        bg_audio = bg_audio * 10 
                        bg_active = True
                elif cmd == "DESLIGAR":
                    if bg_active and len(speech_timeline) > 0:
                        bg_snippet = bg_audio[:len(speech_timeline)]
                        bg_snippet = bg_snippet + config["volume_bg_ducking"]
                        bg_snippet = bg_snippet.fade_out(config["tempo_fade_out_ms"])
                        
                        mixed_speech = speech_timeline.overlay(bg_snippet)
                        combined += mixed_speech
                        speech_timeline = AudioSegment.empty()
                    bg_active = False
            
            elif kind == "LOC":
                if is_intra:
                    speaker_id, texto = content
                    idx = 0 if speaker_id == "speaker1" else 1
                    voz = voices[idx % len(voices)]
                else:
                    texto = content
                    voz = current_voice
                
                audio_bytes = await self.synthesize_chunk(texto, voz)
                loc_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                
                # Adiciona pequeno respiro
                silence = AudioSegment.silent(duration=500)
                loc_segment += silence
                
                if bg_active:
                    speech_timeline += loc_segment
                else:
                    combined += loc_segment

        # Limpeza final se sobrou fala solta
        if len(speech_timeline) > 0:
            if bg_active:
                bg_snippet = bg_audio[:len(speech_timeline)]
                bg_snippet = bg_snippet + config["volume_bg_ducking"]
                bg_snippet = bg_snippet.fade_out(config["tempo_fade_out_ms"])
                mixed_speech = speech_timeline.overlay(bg_snippet)
                combined += mixed_speech
            else:
                combined += speech_timeline

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
        
        clean_name = file_path.stem.replace("_bruto", "").replace("_revisado", "").strip()
        mp3_name = f"{clean_name}.mp3"
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
