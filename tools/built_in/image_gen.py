"""
Image Generation Tool — supports multiple backends:
1. DALL-E 3 (OpenAI API — requires OPENAI_API_KEY)
2. Stable Diffusion via Automatic1111 API (local, http://localhost:7860)
3. ComfyUI API (local, http://localhost:8188)
4. Replicate API (cloud, requires REPLICATE_API_TOKEN)
5. Pollinations.ai (free, no API key, online)

Auto-selects best available backend.
"""

from __future__ import annotations
import os
import base64
import uuid
from pathlib import Path
from tools.base_tool import BaseTool


class ImageGenTool(BaseTool):
    name = "generate_image"
    description = (
        "Generate images from text prompts. Supports DALL-E, Stable Diffusion, "
        "ComfyUI, Replicate, or free online generation. "
        "Returns path to saved image file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Text description of image to generate"},
            "negative_prompt": {"type": "string", "default": "", "description": "What NOT to include"},
            "width": {"type": "integer", "default": 512},
            "height": {"type": "integer", "default": 512},
            "steps": {"type": "integer", "default": 20, "description": "Inference steps (SD only)"},
            "backend": {
                "type": "string",
                "enum": ["auto", "dalle", "stable_diffusion", "comfyui", "replicate", "pollinations"],
                "default": "auto",
            },
            "output_dir": {"type": "string", "default": "data/generated_images"},
            "model": {"type": "string", "default": "", "description": "Model name (backend-specific)"},
            "style": {
                "type": "string",
                "enum": ["vivid", "natural", ""],
                "default": "",
                "description": "DALL-E style",
            },
        },
        "required": ["prompt"],
    }

    def run(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        backend: str = "auto",
        output_dir: str = "data/generated_images",
        model: str = "",
        style: str = "",
    ) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out_path = str(Path(output_dir) / f"img_{uuid.uuid4().hex[:8]}.png")

        if backend == "auto":
            backend = self._detect_best_backend()

        if backend == "dalle":
            return self._dalle(prompt, width, height, out_path, model, style)
        elif backend == "stable_diffusion":
            return self._stable_diffusion(prompt, negative_prompt, width, height, steps, out_path, model)
        elif backend == "comfyui":
            return self._comfyui(prompt, negative_prompt, width, height, steps, out_path)
        elif backend == "replicate":
            return self._replicate(prompt, negative_prompt, width, height, steps, out_path, model)
        elif backend == "pollinations":
            return self._pollinations(prompt, width, height, out_path)
        else:
            return f"Unknown backend: {backend}"

    def _detect_best_backend(self) -> str:
        """Auto-detect which backend is available."""
        # Check DALL-E
        if os.environ.get("OPENAI_API_KEY"):
            return "dalle"
        # Check local SD (Automatic1111)
        try:
            import requests
            r = requests.get("http://localhost:7860/sdapi/v1/options", timeout=2)
            if r.status_code == 200:
                return "stable_diffusion"
        except Exception:
            pass
        # Check ComfyUI
        try:
            import requests
            r = requests.get("http://localhost:8188/system_stats", timeout=2)
            if r.status_code == 200:
                return "comfyui"
        except Exception:
            pass
        # Check Replicate
        if os.environ.get("REPLICATE_API_TOKEN"):
            return "replicate"
        # Fallback to free pollinations
        return "pollinations"

    def _dalle(self, prompt: str, width: int, height: int,
               out_path: str, model: str, style: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI()
            size = f"{width}x{height}"
            if size not in ["256x256", "512x512", "1024x1024", "1024x1792", "1792x1024"]:
                size = "1024x1024"
            kwargs = {
                "model": model or "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "response_format": "b64_json",
            }
            if style:
                kwargs["style"] = style
            response = client.images.generate(**kwargs)
            img_data = base64.b64decode(response.data[0].b64_json)
            Path(out_path).write_bytes(img_data)
            return f"Image saved: {out_path}"
        except ImportError:
            return "openai library not installed: pip install openai"
        except Exception as e:
            return f"DALL-E error: {e}"

    def _stable_diffusion(self, prompt: str, negative_prompt: str,
                           width: int, height: int, steps: int,
                           out_path: str, model: str) -> str:
        try:
            import requests
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": 7,
                "sampler_name": "DPM++ 2M Karras",
            }
            r = requests.post(
                "http://localhost:7860/sdapi/v1/txt2img",
                json=payload, timeout=120
            )
            r.raise_for_status()
            data = r.json()
            img_data = base64.b64decode(data["images"][0])
            Path(out_path).write_bytes(img_data)
            return f"Image saved: {out_path}"
        except Exception as e:
            return f"Stable Diffusion error: {e}"

    def _comfyui(self, prompt: str, negative_prompt: str,
                  width: int, height: int, steps: int, out_path: str) -> str:
        try:
            import requests
            import json as _json
            import websocket
            import uuid as _uuid

            client_id = str(_uuid.uuid4())
            # Simple ComfyUI workflow
            workflow = {
                "3": {"inputs": {"seed": 42, "steps": steps, "cfg": 7, "sampler_name": "euler",
                                  "scheduler": "normal", "denoise": 1, "model": ["4", 0],
                                  "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]},
                      "class_type": "KSampler"},
                "4": {"inputs": {"ckpt_name": "v1-5-pruned-emaonly.ckpt"}, "class_type": "CheckpointLoaderSimple"},
                "5": {"inputs": {"width": width, "height": height, "batch_size": 1}, "class_type": "EmptyLatentImage"},
                "6": {"inputs": {"text": prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
                "7": {"inputs": {"text": negative_prompt or "ugly, blurry", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
                "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
                "9": {"inputs": {"filename_prefix": "ai_human", "images": ["8", 0]}, "class_type": "SaveImage"},
            }
            r = requests.post(
                "http://localhost:8188/prompt",
                json={"prompt": workflow, "client_id": client_id},
                timeout=10,
            )
            r.raise_for_status()
            prompt_id = r.json()["prompt_id"]

            # Wait for completion via WebSocket
            ws = websocket.WebSocket()
            ws.connect(f"ws://localhost:8188/ws?clientId={client_id}")
            while True:
                msg = _json.loads(ws.recv())
                if msg.get("type") == "executing" and msg["data"].get("node") is None:
                    break
            ws.close()

            # Get output image
            history = requests.get(f"http://localhost:8188/history/{prompt_id}", timeout=10).json()
            images = history[prompt_id]["outputs"]["9"]["images"]
            img_data = requests.get(
                f"http://localhost:8188/view",
                params={"filename": images[0]["filename"], "type": "output"},
                timeout=30,
            ).content
            Path(out_path).write_bytes(img_data)
            return f"Image saved: {out_path}"
        except Exception as e:
            return f"ComfyUI error: {e}"

    def _replicate(self, prompt: str, negative_prompt: str,
                    width: int, height: int, steps: int, out_path: str, model: str) -> str:
        try:
            import replicate
            model_id = model or "stability-ai/sdxl:39ed52f2319f9c7c08bb7d785baf77b2b5e5e7c7fb8d6f4de1be0c01e12e8893"
            output = replicate.run(
                model_id,
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": steps,
                }
            )
            # output is a list of URLs
            import requests
            url = output[0] if isinstance(output, list) else output
            img_data = requests.get(str(url), timeout=60).content
            Path(out_path).write_bytes(img_data)
            return f"Image saved: {out_path}"
        except ImportError:
            return "replicate not installed: pip install replicate"
        except Exception as e:
            return f"Replicate error: {e}"

    def _pollinations(self, prompt: str, width: int, height: int, out_path: str) -> str:
        """Free image generation via pollinations.ai — no API key needed."""
        try:
            import requests
            import urllib.parse
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            Path(out_path).write_bytes(r.content)
            return f"Image saved: {out_path}"
        except Exception as e:
            return f"Pollinations error: {e}"
