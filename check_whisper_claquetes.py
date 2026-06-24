import json
from voice_agent.transcriber import transcribe
from voice_agent.splitter import detect_claquetes

def run():
    print("Transcrevendo...")
    audio_path = r'processed\default\18 JUN B1-B6_clean.wav'
    s = transcribe(audio_path)
    
    claquetes, all_words = detect_claquetes(s)
    
    print("\nALL CLAQUETES FOUND:")
    for c in claquetes:
        w_idx = c['word_idx_start']
        context_start = max(0, w_idx - 5)
        context_end = min(len(all_words), w_idx + 10)
        context = " ".join([w.get('text', '') for w in all_words[context_start:context_end]])
        print(f"ID={c['id']} @ {c['start']:.2f}s | Context: {context}")

run()
