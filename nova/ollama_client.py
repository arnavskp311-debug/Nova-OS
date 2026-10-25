"""
Client for communicating with the local Ollama instance.
Supports model discovery, streaming chat completions, and connection status checks.
Optimized for low-RAM Windows 11 with bounded retries, failure caching, and non-blocking operation.
"""

import os
import sys
import json
import logging
import time
import shutil
import subprocess
import threading
from pathlib import Path
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
        # Fast pooled HTTP session with connection reuse and 0 automatic retries on discovery
        self._session = requests.Session()
        # total=0 prevents urllib3 from logging noisy 'Retrying...' warnings on health checks
        retries = Retry(total=0, connect=0, read=0)
        adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=retries)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Cache connection and model list
        self._conn_cache = None
        self._conn_cache_time = 0.0
        self._models_cache = None
        self._models_cache_time = 0.0
        self._failure_cache_duration = 15.0  # Back off 15s if Ollama is unreachable

    def check_connection(self, force_refresh: bool = False) -> bool:
        """Returns True if Ollama service is reachable. Cached with failure backoff."""
        curr = time.time()
        # If recently verified offline, do not spam requests until failure duration elapses
        if not force_refresh and self._conn_cache is False and (curr - self._conn_cache_time) < self._failure_cache_duration:
            return False

        if not force_refresh and self._conn_cache is True and (curr - self._conn_cache_time) < 10.0:
            return True

        try:
            resp = self._session.get(f"{self.host}/api/tags", timeout=(0.8, 2.5))
            is_ok = (resp.status_code == 200)
            self._conn_cache = is_ok
            self._conn_cache_time = curr
            return is_ok
        except Exception:
            self._conn_cache = False
            self._conn_cache_time = curr
            return False

    def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """Fetches list of model names currently installed in Ollama. Cached for 15s."""
        curr = time.time()
        if not force_refresh and self._models_cache is not None and (curr - self._models_cache_time) < 15.0:
            return self._models_cache

        # Check connection first using cached status
        if not force_refresh and self._conn_cache is False and (curr - self._conn_cache_time) < self._failure_cache_duration:
            return []

        try:
            resp = self._session.get(f"{self.host}/api/tags", timeout=(0.8, 2.5))
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                self._models_cache = models
                self._models_cache_time = curr
                self._conn_cache = True
                self._conn_cache_time = curr
                return models
        except Exception:
            # Service is offline or busy; update failure cache
            self._conn_cache = False
            self._conn_cache_time = curr

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
            yield "\n[Notice: Local Ollama service is currently offline. Start Ollama (`ollama serve`) to enable AI chat.]"
        except requests.exceptions.Timeout:
            yield "\n[Notice: Ollama inference request timed out. The local model may be busy swapping or loading.]"
        except Exception as e:
            yield f"\n[Transmission Error: {str(e)}]"


def get_ollama_executable_path() -> Optional[str]:
    """Locates the Ollama executable on the local system."""
    cmd = shutil.which("ollama") or shutil.which("ollama.exe")
    if cmd and os.path.exists(cmd):
        return cmd

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates = [
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe",
            Path(local_app_data) / "Programs" / "Ollama" / "ollama app.exe",
        ]
        for p in candidates:
            if p.exists():
                return str(p)

    prog_files = os.environ.get("ProgramFiles", "")
    if prog_files:
        p = Path(prog_files) / "Ollama" / "ollama.exe"
        if p.exists():
            return str(p)

    return None


def ensure_ollama_running(host: str = DEFAULT_OLLAMA_HOST, timeout_wait: float = 6.0) -> bool:
    """
    Checks if Ollama daemon is active; if offline, auto-starts the
    Ollama server detached in the background without opening a command window.
    """
    client = OllamaClient(host=host)
    if client.check_connection(force_refresh=True):
        return True

    exe = get_ollama_executable_path()
    if not exe:
        logger.warning("Ollama executable not found on host system.")
        return False

    logger.info(f"Auto-starting Ollama service via '{exe} serve'...")
    try:
        creation_flags = 0
        if sys.platform == "win32":
            # CREATE_NO_WINDOW (0x08000000) | DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200)
            creation_flags = 0x08000000 | 0x00000008 | 0x00000200

        env = os.environ.copy()
        # Force CPU compute on low-RAM Intel Core i3 systems to prevent Vulkan/CUDA DLL load failure (0xc0000142)
        env["OLLAMA_LLM_LIBRARY"] = "cpu"
        env["OLLAMA_VULKAN"] = "0"
        env["CUDA_VISIBLE_DEVICES"] = ""
        env["ROCR_VISIBLE_DEVICES"] = ""
        env["GGML_VK_VISIBLE_DEVICES"] = ""

        subprocess.Popen(
            [exe, "serve"],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            close_fds=True
        )

        start = time.time()
        while time.time() - start < timeout_wait:
            time.sleep(0.4)
            if client.check_connection(force_refresh=True):
                logger.info(f"Ollama successfully auto-started in {time.time()-start:.2f}s")
                return True
    except Exception as e:
        logger.error(f"Failed to auto-start Ollama: {e}")

    return False


def start_ollama_in_background(host: str = DEFAULT_OLLAMA_HOST, on_ready_callback=None):
    """Asynchronously starts Ollama on a daemon thread so the main UI never blocks."""
    def _worker():
        ok = ensure_ollama_running(host=host, timeout_wait=8.0)
        if ok and on_ready_callback:
            try:
                on_ready_callback()
            except Exception:
                pass

    t = threading.Thread(target=_worker, name="OllamaAutoStartDaemon", daemon=True)
    t.start()
    return t
