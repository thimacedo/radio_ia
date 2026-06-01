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
        
        # Fila dinâmica de provedores. A ordem inicial importa (mais rápidos/baratos primeiro).
        self.providers = [
            {"name": "GROQ", "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
            {"name": "OPENROUTER", "base_url": "https://openrouter.ai/api/v1", "model": "google/gemini-2.0-flash-001"},
            {"name": "OPENAI", "base_url": None, "model": "gpt-4o-mini"},
            {"name": "GEMINI", "base_url": None, "model": "gemini-1.5-flash"}
        ]
        
        # Rastreador de falhas consecutivas para banimento temporário na sessão
        self.consecutive_failures = {p["name"]: 0 for p in self.providers}
        
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
            text = re.sub(r'^```[a-z]*\n', '', text, flags=re.MULTILINE)
            text = re.sub(r'\n```$', '', text, flags=re.MULTILINE)
            return text

    def ask(self, system_prompt, user_prompt):
        attempts = len(self.providers)
        
        for _ in range(attempts):
            if not self.providers:
                raise Exception("CRÍTICO: Nenhum provedor LLM disponível. Todos falharam repetidamente.")

            # Sempre tenta o primeiro da fila atual
            provider = self.providers[0]
            name = provider["name"]
            
            key_name = f"{name}_API_KEY" if name != "REPLICATE" else "REPLICATE_API_TOKEN"
            api_key = self.keys.get(key_name)
            
            if not api_key:
                # Se não tem a chave, remove da fila e tenta o próximo
                self.providers.pop(0)
                continue

            print(f"    [LLM] Tentando {name} ({provider['model']})...")
            try:
                if name == "GEMINI":
                    res = self._call_gemini(api_key, provider["model"], system_prompt, user_prompt)
                else:
                    res = self._call_openai_compatible(api_key, provider["base_url"], provider["model"], system_prompt, user_prompt)
                
                # Sucesso: zera o contador de falhas
                self.consecutive_failures[name] = 0
                return res
                
            except Exception as e:
                self.consecutive_failures[name] += 1
                falhas = self.consecutive_failures[name]
                print(f"      [!] Falha em {name} (Erro: {e})")
                
                if falhas >= 3:
                    print(f"\n      [🚨 ALERTA] {name} falhou {falhas} vezes seguidas.")
                    print(f"      Motivo: {e}")
                    print(f"      Ação: Removendo {name} permanentemente do fallback nesta rodada. Verifique limites ou a chave no .env.\n")
                    self.providers.pop(0) # Remove permanentemente
                else:
                    print(f"      -> Movendo {name} para o fim da fila de fallback.")
                    # Move para o fim da fila para não travar a execução nas próximas chamadas imediatas
                    failed_prov = self.providers.pop(0)
                    self.providers.append(failed_prov)
                    
        raise Exception("Todos os provedores da fila atual falharam nesta solicitação.")

if __name__ == "__main__":
    factory = LLMFactory()
    res = factory.ask("Você é um assistente útil.", "Diga 'Olá Mundo'")
    print(f"Resultado teste: {res}")
