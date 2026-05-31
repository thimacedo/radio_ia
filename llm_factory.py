import os
import re
import time
import pathlib
import json
import urllib.request
import urllib.error
from openai import OpenAI

class LLMFactory:
    def __init__(self):
        self.keys = self._load_keys()
        
    def _load_keys(self):
        keys = {}
        env_path = pathlib.Path(r"E:\NJUD\.env")
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    keys[k.strip()] = v.strip()
        return keys

    def _call_openai_compatible(self, api_key, base_url, model, system_prompt, user_prompt):
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, api_key, model, system_prompt, user_prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"temperature": 0.3}
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
            # Clean markdown
            text = re.sub(r'^```[a-z]*\n', '', text, flags=re.MULTILINE)
            text = re.sub(r'\n```$', '', text, flags=re.MULTILINE)
            return text

    def ask(self, system_prompt, user_prompt):
        # Ordem de tentativa: Groq -> OpenRouter -> OpenAI -> Gemini
        providers = [
            ("GROQ", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
            ("OPENROUTER", "https://openrouter.ai/api/v1", "google/gemini-2.0-flash-001"),
            ("OPENAI", None, "gpt-4o-mini"),
            ("GEMINI", None, "gemini-1.5-flash")
        ]

        for name, base_url, model in providers:
            key_name = f"{name}_API_KEY" if name != "REPLICATE" else "REPLICATE_API_TOKEN"
            api_key = self.keys.get(key_name)
            
            if not api_key:
                continue

            print(f"    [LLM] Tentando {name} ({model})...")
            try:
                if name == "GEMINI":
                    return self._call_gemini(api_key, model, system_prompt, user_prompt)
                else:
                    return self._call_openai_compatible(api_key, base_url, model, system_prompt, user_prompt)
            except Exception as e:
                print(f"    [!] Falha em {name}: {e}")
                continue
        
        raise Exception("Todos os provedores de LLM falharam.")

if __name__ == "__main__":
    # Teste simples
    factory = LLMFactory()
    res = factory.ask("Você é um assistente útil.", "Diga 'Olá Mundo'")
    print(f"Resultado teste: {res}")
