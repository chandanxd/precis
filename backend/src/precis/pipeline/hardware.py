import csv
import os
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Any

import psutil

COMMON_RAM_SIZES = [2, 4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256]


def detect_cpu() -> tuple[int, str]:
    cores = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True) or 1
    system = platform.system()
    if system == "Windows":
        try:
            model = subprocess.check_output(
                ["powershell", "-command", "(Get-CimInstance Win32_Processor).Name"],
                text=True,
            ).strip()
        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
        ):
            model = "Unknown CPU"

    elif system == "Linux":
        try:
            model = "Unknown CPU"
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        model = line.split(":", 1)[1].strip()
                        break
        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
        ):
            model = "Unknown CPU"

    elif system == "Darwin":
        try:
            model = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip()
        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
        ):
            model = "Unknown CPU"

    else:
        model = "Unknown CPU"

    return cores, model


def detect_ram() -> dict[str, int | float]:
    memory = psutil.virtual_memory()

    usable = round(memory.total / (1024**3), 1)
    total = min(COMMON_RAM_SIZES, key=lambda size: abs(size - usable))
    available = round(memory.available / (1024**3), 1)
    used = round(memory.used / (1024**3), 1)
    usage = memory.percent

    return {
        "total": total,
        "usable": usable,
        "available": available,
        "used": used,
        "usage": usage,
    }


def _select_gpu(gpus: list[str]) -> str:
    for gpu in gpus:
        if "NVIDIA" in gpu:
            return gpu
    for gpu in gpus:
        if "AMD" in gpu or "ATI" in gpu:
            return gpu
    return gpus[0]


def _detect_linux_gpu() -> tuple[bool, str | None, float | None]:
    try:
        result = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=5, check=True
        )
        gpus: list[str] = []

        for line in result.stdout.splitlines():
            if "VGA compatible controller" in line or "3D controller" in line:
                gpus.append(line.split(":", 2)[-1].strip())

        if not gpus:
            return False, None, None

        name = _select_gpu(gpus)

        if "NVIDIA" in name:
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                )
                first_gpu_vram = result.stdout.strip().splitlines()[0]
                vram = round(float(first_gpu_vram) / 1024, 1)
                return True, name, vram
            except (
                FileNotFoundError,
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
            ):
                return True, name, None

        if "AMD" in name or "ATI" in name:
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showmeminfo", "vram"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                )

                vram = None

                for line in result.stdout.splitlines():
                    if "VRAM Total Memory" not in line:
                        continue
                    match = re.search(r"(\d+)\s*$", line.strip())
                    if not match:
                        continue
                    value = int(match.group(1))
                    # Check MiB first: "MiB" also contains "B".
                    if "MiB" in line:
                        vram = round(value / 1024, 1)
                    else:
                        vram = round(value / (1024**3), 1)
                    break
                return True, name, vram
            except (
                FileNotFoundError,
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
            ):
                return True, name, None
            # leaving AMD VRAM parsing for later since rocm-smi is less standardized
            # and many consumer AMD systems don't have it installed
        return True, name, None

    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    ):
        return False, None, None


def _detect_windows_gpu() -> tuple[bool, str | None, float | None]:
    # 1. try nvidia-smi first to bypass Windows WMI 4GB VRAM capping
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        first_gpu = result.stdout.strip().splitlines()[0]
        name, vram_mb = first_gpu.split(",")
        return True, name.strip(), round(float(vram_mb.strip()) / 1024, 1)
    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    ):
        pass

    # 2. fallback to Powershell for AMD/Intel or systems without nvidia-smi
    try:
        result = subprocess.run(
            [
                "powershell",
                "-command",
                (
                    "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Csv -NoTypeInformation"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        reader = csv.DictReader(result.stdout.splitlines())
        gpus: list[tuple[str, float | None]] = []

        for row in reader:
            name = row["Name"].strip()
            try:
                vram = round(int(row["AdapterRAM"]) / (1024**3), 1)
            except (ValueError, TypeError):
                vram = None

            gpus.append((name, vram))

        if not gpus:
            return False, None, None

        name = _select_gpu([gpu[0] for gpu in gpus])
        for gpu_name, vram in gpus:
            if gpu_name == name:
                return True, gpu_name, vram
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return False, None, None

    return False, None, None


def _detect_macos_gpu() -> tuple[bool, str | None, float | None]:
    try:
        result = subprocess.run(
            ["system-profiler", "SPDisplaysType"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        name = None
        vram = None

        for line in result.stdout.splitlines():
            line = line.strip()

            if line.startswith("Chipset Model:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("VRAM"):
                value = line.split(":", 1)[1].strip()
                try:
                    vram = float(value.split()[0])
                except ValueError:
                    pass

        if name:
            if "Apple" in name:
                memory = psutil.virtual_memory()
                vram = round((memory.total * 0.75) / (1024**3), 1)
            return True, name, vram

    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    ):
        pass

    return False, None, None


def detect_gpu() -> tuple[bool, str | None, float | None]:
    detectors = {
        "Linux": _detect_linux_gpu,
        "Windows": _detect_windows_gpu,
        "Darwin": _detect_macos_gpu,
    }

    detector = detectors.get(platform.system())
    if detector is None:
        return False, None, None

    return detector()


def detect_ml_accelerator() -> tuple[bool, str | None]:
    try:
        import torch
    except ImportError:
        return False, "cpu"
    if torch.cuda.is_available():
        if getattr(torch.version, "hip", None) is not None:
            return True, "rocm"
        return True, "cuda"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return True, "mps"
    return False, "cpu"


@dataclass
class HardwareProfile:
    cpu_cores: int
    cpu_model: str
    ram_gb: float
    has_gpu: bool
    gpu_name: str | None
    vram_gb: float | None
    ml_accelerator: str | None
    recommended_model: str
    recommended_mode: str
    token_ceiling: int

    def to_dict(self) -> dict:
        return {
            "cpu_cores": self.cpu_cores,
            "cpu_model": self.cpu_model,
            "ram_gb": self.ram_gb,
            "has_gpu": self.has_gpu,
            "gpu_name": self.gpu_name,
            "vram_gb": self.vram_gb,
            "recommended_model": self.recommended_model,
            "recommended_mode": self.recommended_mode,
            "token_ceiling": self.token_ceiling,
            "ml_accelerator": self.ml_accelerator,
        }

    def __str__(self) -> str:
        gpu_str = f"{self.gpu_name} ({self.vram_gb} GB)" if self.has_gpu else "None"
        return (
            f"HardwareProfile(\n"
            f"CPU: {self.cpu_model} ({self.cpu_cores} cores)\n"
            f"RAM: {self.ram_gb} GB\n"
            f"GPU: {gpu_str}\n"
            f"ML accelerator: {self.ml_accelerator}\n"
            f"Mode: {self.recommended_mode}\n"
            f"Model: {self.recommended_model}\n"
            f"Token ceiling: {self.token_ceiling}\n"
            ")"
        )


def select_mode(ram_gb: float, has_gpu: bool, vram_gb: float | None) -> str:
    # gpu-large only changes the default model: its ceiling equals gpu's, so the
    # token-ceiling rules (4,096 for RAM >= 8 GB and VRAM >= 6 GB) are unchanged.
    if ram_gb >= 8 and has_gpu and vram_gb is not None and vram_gb >= 10:
        return "gpu-large"
    if ram_gb >= 8 and has_gpu and vram_gb is not None and vram_gb >= 6:
        return "gpu"
    if ram_gb >= 8 and has_gpu and vram_gb is not None and vram_gb >= 2:
        return "gpu-partial"
    if ram_gb >= 16:
        return "cpu"
    return "cpu-light"


PRIMARY_MODEL = os.getenv("PRECIS_OLLAMA_MODEL", "qwen3.5:4b")
# Model for the lightest tier (under 16 GB RAM, no usable GPU): the smallest
# model of the same family (q4_K_M, 1.9 GB on disk against 3.3 GB for 4b), so
# it fits beside spaCy, the coreference model and the embedder in 8 GB.
FALLBACK_MODEL = os.getenv("PRECIS_OLLAMA_FALLBACK_MODEL", "qwen3.5:2b")
# Model for GPUs with 10 GB+ VRAM: the 9b model (q4_K_M, 6.6 GB) fits with room
# for the context, which a 6-8 GB card does not reliably give it.
LARGE_MODEL = os.getenv("PRECIS_OLLAMA_LARGE_MODEL", "qwen3.5:9b")

MODE_TO_MODEL: dict[str, str] = {
    "gpu-large": LARGE_MODEL,
    "gpu": PRIMARY_MODEL,
    "gpu-partial": PRIMARY_MODEL,
    "cpu": PRIMARY_MODEL,
    "cpu-light": FALLBACK_MODEL,
}

MODE_TO_CEILING: dict[str, int] = {
    "gpu-large": 4096,
    "gpu": 4096,
    "gpu-partial": 3072,
    "cpu": 2048,
    "cpu-light": 1024,
}


# Human-readable rule per mode, in the order of select_mode. Settings shows
# these as device presets.
MODE_LABELS: dict[str, str] = {
    "gpu-large": "GPU with 10 GB+ VRAM (and 8 GB+ RAM)",
    "gpu": "GPU with 6-10 GB VRAM (and 8 GB+ RAM)",
    "gpu-partial": "GPU with 2-6 GB VRAM (and 8 GB+ RAM)",
    "cpu": "16 GB+ RAM, no usable GPU",
    "cpu-light": "Under 16 GB RAM, no usable GPU",
}


def hardware_tiers() -> list[dict[str, Any]]:
    """The hardware modes with their default model and token ceiling."""
    return [
        {
            "mode": mode,
            "label": MODE_LABELS[mode],
            "model": get_model_for_mode(mode),
            "token_ceiling": MODE_TO_CEILING[mode],
        }
        for mode in ("gpu-large", "gpu", "gpu-partial", "cpu", "cpu-light")
    ]


def get_model_for_mode(mode: str) -> str:
    """Resolve active model tag for operating mode with runtime env overrides."""
    primary = os.getenv("PRECIS_OLLAMA_MODEL", PRIMARY_MODEL)
    fallback = os.getenv("PRECIS_OLLAMA_FALLBACK_MODEL", FALLBACK_MODEL)
    large = os.getenv("PRECIS_OLLAMA_LARGE_MODEL", LARGE_MODEL)
    if mode == "cpu-light":
        return fallback
    if mode == "gpu-large":
        return large
    return primary


def profile_hardware() -> HardwareProfile:
    cores, cpu_model = detect_cpu()
    ram = detect_ram()
    has_gpu, gpu_name, vram = detect_gpu()
    _, ml_accelerator = detect_ml_accelerator()
    # Tier on nominal installed RAM: "usable" is the OS-reported figure and
    # sits just under it (e.g. 15.5 GB on a 16 GB machine).
    mode = select_mode(ram["total"], has_gpu, vram)

    return HardwareProfile(
        cpu_cores=cores,
        cpu_model=cpu_model,
        ram_gb=ram["usable"],
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        vram_gb=vram,
        ml_accelerator=ml_accelerator,
        recommended_model=get_model_for_mode(mode),
        recommended_mode=mode,
        token_ceiling=MODE_TO_CEILING[mode],
    )
