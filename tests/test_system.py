# -*- coding: utf-8 -*-
"""
Testes automatizados para validação do Estúdio Rádio IA (TJRN / NJUD)
-------------------------------------------------------------------
Valida o comportamento da fila de vozes (VoiceQueue), a fonetização de siglas (aplicar_pronuncia)
e o carregamento do .env.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Adicionar raiz do projeto ao path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from core.voice_queue import VoiceQueue
from core.best_practices import aplicar_pronuncia, carregar_env_var

class TestRadioSystem(unittest.TestCase):
    
    def setUp(self):
        # Configurar ambiente de teste se necessário
        self.regras_teste = {
            "TJRN": "T-J-R-N",
            "COSERN": "Cozern",
            "PJe": "P-Jê",
            "AMARN": "ámarn"
        }
        
    def test_voice_queue_rotation(self):
        """Valida que a fila de vozes rotaciona sequencialmente de forma round-robin."""
        queue = VoiceQueue()
        # Captura as vozes padrão configuradas
        default_voices = queue._voices
        self.assertEqual(len(default_voices), 4)
        
        # Pega a primeira voz e garante que o ciclo passa por todas elas sequencialmente
        primeira_vez = []
        for _ in range(4):
            primeira_vez.append(queue.next_voice())
            
        # Garante que todas as 4 vozes da lista padrão foram usadas
        for voz in default_voices:
            self.assertIn(voz, primeira_vez)
            
        # O quinto elemento deve repetir o primeiro elemento (round-robin)
        quinta_voz = queue.next_voice()
        self.assertEqual(quinta_voz, primeira_vez[0])
        
    def test_aplicar_pronuncia(self):
        """Valida que as siglas do roteiro são substituídas por suas pronúncias fonéticas."""
        texto_original = "O TJRN emitiu nota sobre o sistema PJe e a COSERN."
        
        # O resultado esperado de acordo com as chaves definidas no pronunciation_rules.json
        texto_processado = aplicar_pronuncia(texto_original)
        
        self.assertIn("T-J-R-N", texto_processado)
        self.assertIn("P-Jê", texto_processado)
        self.assertIn("Cozern", texto_processado)
        self.assertNotIn("TJRN", texto_processado)
        self.assertNotIn("COSERN", texto_processado)
        
    def test_carregar_env_var(self):
        """Valida que os fallbacks das variáveis do .env funcionam se o arquivo não existir ou se chave faltar."""
        env_path = os.path.join(project_root, ".env")
        env_bak = os.path.join(project_root, ".env.bak_test")
        
        # Salvar .env real se existir
        if os.path.exists(env_path):
            os.rename(env_path, env_bak)
            
        try:
            # Caso 1: Arquivo não existe - deve usar o fallback
            val1 = carregar_env_var("TEST_KEY", "fallback_val")
            self.assertEqual(val1, "fallback_val")
            
            # Caso 2: Criar .env de teste
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("TEST_KEY=valor_do_env\n")
                f.write("OUTRA_TEST_KEY = valor_com_espaco \n")
                
            val2 = carregar_env_var("TEST_KEY", "fallback")
            self.assertEqual(val2, "valor_do_env")
            
            val3 = carregar_env_var("OUTRA_TEST_KEY", "fallback")
            self.assertEqual(val3, "valor_com_espaco")
            
            # Caso 3: Chave inexistente no arquivo .env existente
            val4 = carregar_env_var("CHAVE_INEXISTENTE", "fallback_val")
            self.assertEqual(val4, "fallback_val")
            
        finally:
            # Limpar .env de teste
            if os.path.exists(env_path):
                os.remove(env_path)
            # Restaurar .env real se existia
            if os.path.exists(env_bak):
                os.rename(env_bak, env_path)
                
    @patch('urllib.request.urlopen')
    def test_notificador_push_priority_mapping(self, mock_urlopen):
        """Valida que a prioridade em texto (Ex: high/urgent) é devidamente mapeada para inteiros na API do ntfy."""
        from core.notificador_push import NotificadorPush
        
        # Configura resposta mockada com sucesso (status 200)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        notifier = NotificadorPush()
        notifier.url = "https://ntfy.sh"
        notifier.topico = "test_topic"
        
        # Caso 1: prioridade "urgent" mapeada para 5
        notifier.enviar("Olá, teste", prioridade="urgent")
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["priority"], 5)
        self.assertEqual(payload["topic"], "test_topic")
        
        # Caso 2: prioridade "high" mapeada para 4
        notifier.enviar("Olá, teste", prioridade="high")
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["priority"], 4)
        
        # Caso 3: prioridade default/invalida mapeada para 3
        notifier.enviar("Olá, teste", prioridade="invalid_string")
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["priority"], 3)

if __name__ == "__main__":
    unittest.main()


