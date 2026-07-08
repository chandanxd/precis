from precis.pipeline.hardware import (
    HardwareProfile,
    profile_hardware,
    select_mode,
)


class TestSelectMode:
    def test_gpu_model(self):
        assert select_mode(ram_gb=16, has_gpu=True, vram_gb=8) == "gpu"

    def test_gpu_partial_mode(self):
        assert select_mode(ram_gb=16, has_gpu=True, vram_gb=4) == "gpu-partial"

    def test_cpu_mode(self):
        assert select_mode(ram_gb=16, has_gpu=False, vram_gb=None) == "cpu"

    def test_cpu_list_mode(self):
        assert select_mode(ram_gb=8, has_gpu=False, vram_gb=None) == "cpu-light"

    def test_low_ram_with_gpu_still_cpu_light(self):
        assert select_mode(ram_gb=8, has_gpu=True, vram_gb=8) == "cpu-light"


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
        }
        assert set(d.keys()) == expected_keys
