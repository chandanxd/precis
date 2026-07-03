import platform
import subprocess

import psutil


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


def detect_ram() -> float:
    return round(psutil.virtual_memory().total / (1024**3), 1)
