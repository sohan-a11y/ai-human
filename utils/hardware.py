"""
Hardware detection and automatic model tier selection.

Detects RAM, VRAM, and CPU to recommend the right quantized model
so the system works on machines as small as 4GB RAM.
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache

from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class HardwareProfile:
    ram_gb: float
    vram_gb: float
    cpu_cores: int
    cpu_name: str
    has_gpu: bool
    platform: str

    @property
    def tier(self) -> str:
        """
        Returns hardware tier:
          low    → < 6 GB RAM,  no GPU  (Raspberry Pi, old laptops)
          medium → 6-15 GB RAM, no GPU  (average laptops)
          high   → 16+ GB RAM or any VRAM ≥ 4 GB
          gpu    → VRAM ≥ 8 GB
        """
        if self.vram_gb >= 8:
            return "gpu"
        if self.vram_gb >= 4 or self.ram_gb >= 16:
            return "high"
        if self.ram_gb >= 6:
            return "medium"
        return "low"


# ─── Model recommendations per provider per tier ───────────────────────────
#
# All Ollama models are GGUF-quantized automatically.
# We prefer Q4_K_M quality — good balance of speed and accuracy.
#
# Context windows are conservative to avoid OOM on edge hardware.

MODEL_TIERS = {
    "ollama": {
        "low": {
            # 2-4 GB RAM: tiny models only
            "text": "tinyllama:1.1b",          # 638 MB, runs on 2 GB RAM
            "vision": "moondream:1.8b",        # 1.1 GB, 2 GB RAM
            "context": 2048,
            "note": "Minimal quality. For 4 GB RAM machines.",
        },
        "medium": {
            # 6-15 GB RAM: 3B-7B sweet spot
            "text": "llama3.2:3b",             # 2.0 GB, 5 GB RAM
            "vision": "llava:7b",              # 4.5 GB, 8 GB RAM
            "context": 4096,
            "note": "Good quality. Recommended for most laptops.",
        },
        "high": {
            # 16+ GB RAM, no GPU: 7B-13B
            "text": "mistral:7b",              # 4.1 GB, 8 GB RAM
            "vision": "llava:13b",             # 8.0 GB, 16 GB RAM
            "context": 8192,
            "note": "High quality. For 16 GB RAM systems.",
        },
        "gpu": {
            # Dedicated GPU ≥ 8 GB VRAM
            "text": "llama3.1:8b",             # 4.9 GB VRAM
            "vision": "llava:13b",
            "context": 16384,
            "note": "Best local quality. GPU accelerated.",
        },
    },
    "lmstudio": {
        # LM Studio uses GGUF files — same tier logic
        "low":    {"text": "llama-3.2-1b-instruct-q4_k_m",    "vision": "moondream2", "context": 2048},
        "medium": {"text": "llama-3.2-3b-instruct-q4_k_m",    "vision": "llava-1.5-7b-hf-q4_k_m", "context": 4096},
        "high":   {"text": "mistral-7b-instruct-v0.3-q4_k_m", "vision": "llava-v1.6-mistral-7b-q4_k_m", "context": 8192},
        "gpu":    {"text": "meta-llama-3.1-8b-instruct-q5_k_m", "vision": "llava-v1.6-34b-q4_k_m", "context": 16384},
    },
    "anthropic": {
        # Cloud — hardware doesn't matter, pick cheapest capable model
        "low":    {"text": "claude-haiku-4-5-20251001", "vision": "claude-haiku-4-5-20251001", "context": 32768},
        "medium": {"text": "claude-haiku-4-5-20251001", "vision": "claude-haiku-4-5-20251001", "context": 32768},
        "high":   {"text": "claude-sonnet-4-6",         "vision": "claude-sonnet-4-6",         "context": 100000},
        "gpu":    {"text": "claude-sonnet-4-6",         "vision": "claude-sonnet-4-6",         "context": 100000},
    },
    "openai": {
        "low":    {"text": "gpt-4o-mini", "vision": "gpt-4o-mini", "context": 16384},
        "medium": {"text": "gpt-4o-mini", "vision": "gpt-4o-mini", "context": 16384},
        "high":   {"text": "gpt-4o",      "vision": "gpt-4o",      "context": 128000},
        "gpu":    {"text": "gpt-4o",      "vision": "gpt-4o",      "context": 128000},
    },
}


def _detect_ram_gb() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception:
        return 8.0  # safe fallback


def _detect_cpu_cores() -> int:
    try:
        import psutil
        return psutil.cpu_count(logical=False) or 4
    except Exception:
        return 4


def _detect_cpu_name() -> str:
    try:
        import platform
        name = platform.processor()
        if name:
            return name
    except Exception:
        pass
    return "Unknown CPU"


def _detect_vram_gb() -> float:
    """Try NVIDIA → AMD → Intel → return 0 if none found."""
    # NVIDIA
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            total_mb = sum(int(x.strip()) for x in lines if x.strip().isdigit())
            return round(total_mb / 1024, 1)
    except Exception:
        pass

    # AMD (rocm-smi)
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--csv"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "VRAM" in result.stdout:
            import re
            nums = re.findall(r"(\d+)", result.stdout)
            if nums:
                return round(int(nums[0]) / 1024, 1)
    except Exception:
        pass

    return 0.0


@lru_cache(maxsize=1)
def detect_hardware() -> HardwareProfile:
    ram = _detect_ram_gb()
    vram = _detect_vram_gb()
    cores = _detect_cpu_cores()
    cpu_name = _detect_cpu_name()

    profile = HardwareProfile(
        ram_gb=ram,
        vram_gb=vram,
        cpu_cores=cores,
        cpu_name=cpu_name,
        has_gpu=vram > 0,
        platform=platform.system(),
    )

    log.info(
        f"Hardware: {ram}GB RAM | {vram}GB VRAM | {cores} cores | tier={profile.tier}"
    )
    return profile


def recommend_model(provider: str, model_type: str = "text") -> tuple[str, int]:
    """
    Returns (model_name, context_window) for the given provider
    based on detected hardware.

    model_type: 'text' or 'vision'
    """
    hw = detect_hardware()
    tier = hw.tier
    tiers = MODEL_TIERS.get(provider, MODEL_TIERS["ollama"])
    config = tiers.get(tier, tiers["medium"])

    model = config.get(model_type, config["text"])
    context = config.get("context", 4096)

    note = config.get("note", "")
    if note:
        log.info(f"Model recommendation ({provider}/{tier}): {model} — {note}")

    return model, context


def print_hardware_report() -> None:
    """Print a human-readable hardware + model recommendation report."""
    hw = detect_hardware()
    print("\n" + "=" * 55)
    print("  AI HUMAN — Hardware Report")
    print("=" * 55)
    print(f"  CPU    : {hw.cpu_name}")
    print(f"  Cores  : {hw.cpu_cores}")
    print(f"  RAM    : {hw.ram_gb} GB")
    print(f"  VRAM   : {hw.vram_gb} GB {'(GPU detected)' if hw.has_gpu else '(no GPU)'}")
    print(f"  Tier   : {hw.tier.upper()}")
    print()
    print("  Recommended models (Ollama):")
    text_model, ctx = recommend_model("ollama", "text")
    vision_model, _ = recommend_model("ollama", "vision")
    print(f"    Text   : {text_model}")
    print(f"    Vision : {vision_model}")
    print(f"    Context: {ctx} tokens")
    print()
    print("  Install with:")
    print(f"    ollama pull {text_model}")
    print(f"    ollama pull {vision_model}")
    print("=" * 55 + "\n")
