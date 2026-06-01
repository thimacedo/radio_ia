import os
from gtts import gTTS

# Diretórios
BASE_WORKSPACE = r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS"
TTS_TXT_DIR = os.path.join(BASE_WORKSPACE, "tts_txt")
OUTPUT_DIR = os.path.join(BASE_WORKSPACE, "tts_mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

for fname in os.listdir(TTS_TXT_DIR):
    if not fname.lower().endswith('.txt'):
        continue
    txt_path = os.path.join(TTS_TXT_DIR, fname)
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    # Cria áudio TTS (português brasileiro)
    # Se o arquivo .txt estiver vazio, usa texto placeholder
    if not text.strip():
        text = "Roteiro não disponível para geração de áudio."
    tts = gTTS(text=text, lang='pt')
    mp3_name = os.path.splitext(fname)[0] + '.mp3'
    mp3_path = os.path.join(OUTPUT_DIR, mp3_name)
    tts.save(mp3_path)
    print(f"Gerado TTS: {mp3_path}")
