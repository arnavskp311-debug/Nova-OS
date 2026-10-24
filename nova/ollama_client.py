"""
Client for communicating with the local Ollama instance.
Supports model discovery, streaming chat completions, and connection status checks.
"""

import json
import logging
from typing import List, Dict, Any, Generator, Optional
import requests
from nova.config import DEFAULT_OLLAMA_HOST, DEFAULT_MODEL

logger = logging.getLogger("nova.ollama")

SYSTEM_PROMPT = """You are NOVA, the advanced synthetic intelligence of NOVA OS — a futuristic AI desktop trial running safely inside Windows.
Your core traits:
1. Intelligent, concise, sleek, cybernetic, and helpful.
2. Safety-first: Emphasize that NOVA OS operates as a safe trial inside Windows without altering bootloaders, partitions, or system files.
3. You can assist with coding, system analysis, writing notes, and answering complex inquiries.
4. When suggesting shell commands for user diagnostics, explain what they do.
"""

import json
import logging
import time
from typing import List, Dict, Any, Generator, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from nova.config import DEFAULT_OLLAMA_HOST, DEFAULT_MODEL

logger = logging.getLogger("nova.ollama")

SYSTEM_PROMPT = """You are NOVA, the advanced synthetic intelligence of NOVA OS — a futuristic AI desktop trial running safely inside Windows.
Your core traits:
1. Intelligent, concise, sleek, cybernetic, and helpful.
2. Safety-first: Emphasize that NOVA OS operates as a safe trial inside Windows without altering bootloaders, partitions, or system files.
3. You can assist with coding, system analysis, writing notes, and answering complex inquiries.
4. When suggesting shell commands for user diagnostics, explain what they do.
"""

class OllamaClient:
    def __init__(self, host: str = DEFAULT_OLLAMA_HOST):
        self.host = host.rstrip("/")
        # Fast pooled HTTP session with connection reuse
        self._session = requests.Session()
        retries = Retry(total=1, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        self._session.mount("http://", HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=retries))
        
        # Cache connection and model list
        self._conn_cache = None
        self._conn_cache_time = 0.0
        self._models_cache = None
        self._models_cache_time = 0.0

    def check_connection(self, force_refresh: bool = False) -> bool:
        """Returns True if Ollama service is reachable. Cached for 5s."""
        curr = time.time()
        if not force_refresh and self._conn_cache is not None and (curr - self._conn_cache_time) < 5.0:
            return self._conn_cache

        try:
            resp = self._session.get(f"{self.host}/api/tags", timeout=1.5)
            is_ok = (resp.status_code == 200)
            self._conn_cache = is_ok
            self._conn_cache_time = curr
            return is_ok
        except Exception:
            self._conn_cache = False
            self._conn_cache_time = curr
            return False

    def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """Fetches list of model names currently installed in Ollama. Cached for 10s."""
        curr = time.time()
        if not force_refresh and self._models_cache is not None and (curr - self._models_cache_time) < 10.0:
            return self._models_cache

        try:
            resp = self._session.get(f"{self.host}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                self._models_cache = models
                self._models_cache_time = curr
                self._conn_cache = True
                self._conn_cache_time = curr
                return models
        except Exception as e:
            logger.warning(f"Failed to fetch models from Ollama: {e}")
        
        return []

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Streams response chunks from Ollama chat API.
        Yields text chunks as they arrive.
        """
        url = f"{self.host}/api/chat"
        
        # Inject system prompt at beginning if not present
        formatted_messages = []
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt or SYSTEM_PROMPT
            })
        formatted_messages.extend(messages)

        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": 0.7,
            }
        }

        try:
            with requests.post(url, json=payload, stream=True, timeout=30) as resp:
                if resp.status_code != 200:
                    yield f"[Ollama Error {resp.status_code}: {resp.text}]"
                    return
                
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                        if chunk.get("done", False):
                            break
        except requests.exceptions.ConnectionError:
            yield "\n[Error: Unable to connect to local Ollama server at " + self.host + ". Ensure Ollama is running (`ollama serve`).]"
        except Exception as e:
            yield f"\n[Transmission Error: {str(e)}]"
