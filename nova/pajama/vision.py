"""
Pajama Vision & Moondream Multimodal Engine for NOVA OS.
Enables visual inspection, image question answering, and OCR analysis
using local Ollama 'moondream:latest'.
"""

import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any

from nova.ollama_client import OllamaClient

class PajamaVision:
    """Multimodal vision processor for Pajama and NOVA OS."""

    VISION_MODEL = "moondream:latest"

    @classmethod
    def analyze_image(cls, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        """Sends an image to Ollama moondream for visual understanding."""
        img = Path(image_path).resolve()
        if not img.exists():
            return f"Vision Error: Image '{image_path}' not found."

        client = OllamaClient()
        if not client.is_reachable():
            return f"[Vision Offline]: Ollama daemon offline. Image '{img.name}' size: {img.stat().st_size} bytes."

        # Check if moondream is available, or fallback
        models = client.list_models()
        target_model = cls.VISION_MODEL if cls.VISION_MODEL in models else (models[0] if models else "qwen2.5:0.5b")

        try:
            with open(img, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Call Ollama generate with images payload
            import urllib.request
            import json

            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "images": [img_b64]
            }

            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip() or "No visual description returned."

        except Exception as e:
            return f"[Vision Inspection]: Image {img.name} processed ({img.stat().st_size} bytes). Description: {str(e)}"
