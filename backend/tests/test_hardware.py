import pytest
from precis.pipeline.hardware import (
    HardwareProfile,
    MODE_TO_CEILING,
    MODE_TO_MODEL,
    profile_hardware,
    select_mode,
)


class TestSelectMode:
    def test_gpu_mode(self):
        assert select_mode(ram_gb=16, has_gpu=True, vram_gb=8) == "gpu"

    def test_gpu_partial_mode(self):
        assert select_mode(ram_gb=16, has_gpu=True, vram_gb=4) == "gpu-partial"

    def test_cpu_mode(self):
        assert select_mode(ram_gb=16, has_gpu=False, vram_gb=None) == "cpu"

    def test_cpu_light_mode(self):
        assert select_mode(ram_gb=8, has_gpu=False, vram_gb=None) == "cpu-light"

    def test_consumer_laptop_8gb_ram_with_gpu(self):
        assert select_mode(ram_gb=8, has_gpu=True, vram_gb=8) == "gpu"
        assert select_mode(ram_gb=8, has_gpu=True, vram_gb=4) == "gpu-partial"

    def test_insufficient_ram_with_gpu_falls_back_to_cpu_light(self):
        assert select_mode(ram_gb=4, has_gpu=True, vram_gb=8) == "cpu-light"

    @pytest.mark.parametrize(
        "ram_gb,has_gpu,vram_gb,expected_mode,expected_ceiling,expected_model",
        [
            (4, False, None, "cpu-light", 1024, "qwen2.5-coder:7b"),
            (8, False, None, "cpu-light", 1024, "qwen2.5-coder:7b"),
            (8, True, 4, "gpu-partial", 3072, "llama3:8b"),
            (8, True, 6, "gpu", 4096, "llama3:8b"),
            (8, True, 8, "gpu", 4096, "llama3:8b"),
            (16, False, None, "cpu", 2048, "llama3:8b"),
            (16, True, 6, "gpu", 4096, "llama3:8b"),
            (16, True, 8, "gpu", 4096, "llama3:8b"),
            (32, True, 8, "gpu", 4096, "llama3:8b"),
        ],
    )
    def test_all_decision_matrix_scenarios(
        self, ram_gb, has_gpu, vram_gb, expected_mode, expected_ceiling, expected_model
    ):
        mode = select_mode(ram_gb=ram_gb, has_gpu=has_gpu, vram_gb=vram_gb)
        assert mode == expected_mode
        assert MODE_TO_CEILING[mode] == expected_ceiling
        assert MODE_TO_MODEL[mode] == expected_model


class TestProfileHardware:
    def test_returns_hardware_profile(self):
        profile = profile_hardware()
        assert isinstance(profile, HardwareProfile)
        assert profile.cpu_cores > 0
        assert profile.ram_gb > 0
        assert profile.recommended_mode in ("gpu", "gpu-partial", "cpu", "cpu-light")
        assert profile.token_ceiling > 0

    def test_to_dict_has_all_keys(self):
        profile = profile_hardware()
        d = profile.to_dict()
        expected_keys = {
            "cpu_cores",
            "cpu_model",
            "ram_gb",
            "has_gpu",
            "gpu_name",
            "vram_gb",
            "recommended_model",
            "recommended_mode",
            "token_ceiling",
            "ml_accelerator",
        }
        assert set(d.keys()) == expected_keys
