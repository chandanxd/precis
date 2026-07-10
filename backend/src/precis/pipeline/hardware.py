import csv
import platform
import re
import subprocess
from dataclasses import dataclass

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
        except Exception:
            model = "Unknown CPU"

    elif system == "Linux":
        try:
            model = "Unknown CPU"
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            model = "Unknown CPU"

    elif system == "Darwin":
        try:
            model = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip()
        except Exception:
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
                vram = round(float(result.stdout.strip()) / 1024, 1)
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
                    match = re.search(r"/d+", line)
                    if not match:
                        continue
                    value = int(match.group(1))
                    if "B" in line:
                        vram = round(value / (1024**3), 1)
                    elif "MiB" in line:
                        vram = round(value / 1024, 1)
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
        }

    def __str__(self) -> str:
        gpu_str = f"{self.gpu_name} ({self.vram_gb} GB)" if self.has_gpu else "None"
        return (
            f"HardwareProfile(\n"
            f"CPU: {self.cpu_model} ({self.cpu_cores} cores)\n"
            f"RAM: {self.ram_gb} GB\n"
            f"GPU: {gpu_str}\n"
            f"Mode: {self.recommended_mode}\n"
            f"Model: {self.recommended_model}\n"
            f"Token ceiling: {self.token_ceiling}\n"
            ")"
        )


def select_mode(ram_gb: float, has_gpu: bool, vram_gb: float | None) -> str:
    if ram_gb >= 16 and has_gpu and vram_gb is not None and vram_gb >= 6:
        return "gpu"
    if ram_gb >= 16 and has_gpu and vram_gb is not None:
        return "gpu-partial"
    if ram_gb >= 16:
        return "cpu"
    return "cpu-light"


MODE_TO_MODEL: dict[str, str] = {
    "gpu": "llama3:8b",
    "gpu-partial": "llama3:8b",
    "cpu": "llama3:8b",
    "cpu-light": "qwen2.5v1:7b",
}

MODE_TO_CEILING: dict[str, int] = {
    "gpu": 4096,
    "gpu-partial": 3072,
    "cpu": 2048,
    "cpu-light": 1024,
}


def profile_hardware() -> HardwareProfile:
    cores, cpu_model = detect_cpu()
    ram = detect_ram()
    has_gpu, gpu_name, vram = detect_gpu()
    mode = select_mode(ram["usable"], has_gpu, vram)

    return HardwareProfile(
        cpu_cores=cores,
        cpu_model=cpu_model,
        ram_gb=ram["usable"],
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        vram_gb=vram,
        recommended_model=MODE_TO_MODEL[mode],
        recommended_mode=mode,
        token_ceiling=MODE_TO_CEILING[mode],
    )


def validate_ollama(model: str) -> bool:
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return model.split(":")[0] in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


print(profile_hardware())
