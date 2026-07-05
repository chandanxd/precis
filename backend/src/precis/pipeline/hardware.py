import csv
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
                # TODO: parse vram from rocm-smi output
                return True, name, None
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
