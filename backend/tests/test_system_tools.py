from __future__ import annotations

from app.tools.system_tools import CpuUsageTool, DiskUsageTool, NetworkStatusTool, RamUsageTool


async def test_cpu_usage():
    result = await CpuUsageTool().execute()
    assert result.success is True
    assert 0.0 <= result.data["cpu_percent"] <= 100.0
    assert result.data["cpu_count"] >= 1


async def test_ram_usage():
    result = await RamUsageTool().execute()
    assert result.success is True
    assert result.data["total_gb"] > 0
    assert 0.0 <= result.data["percent"] <= 100.0


async def test_disk_usage():
    result = await DiskUsageTool().execute(path="C:\\")
    assert result.success is True
    assert result.data["total_gb"] > 0


async def test_disk_usage_invalid_path():
    result = await DiskUsageTool().execute(path="Z:\\this-drive-should-not-exist\\")
    assert result.success is False


async def test_network_status():
    result = await NetworkStatusTool().execute()
    assert result.success is True
    assert isinstance(result.data["interfaces"], list)
