import platform
import subprocess

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
