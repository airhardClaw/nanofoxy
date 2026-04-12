"""System monitoring tool for agent."""

import json
import platform
import time
from typing import Any

import psutil

from nanobot.agent.tools.base import Tool


class SystemMonitorTool(Tool):
    """Monitor system resources: CPU, memory, disk, network, system info, and uptime."""

    _AVAILABLE_METRICS = [
        "cpu",
        "memory",
        "disk",
        "network",
        "system",
        "uptime",
        "processes",
        "io",
    ]

    @property
    def name(self) -> str:
        return "system_monitor"

    @property
    def description(self) -> str:
        return (
            "Monitor system resources. Returns JSON with CPU, memory, disk, network, "
            "system info, uptime, top processes, and I/O stats. "
            "Use metrics parameter to specify which data to collect."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "array",
                    "items": {"type": "string", "enum": self._AVAILABLE_METRICS},
                    "description": f"List of metrics to collect. Available: {', '.join(self._AVAILABLE_METRICS)}",
                    "default": ["cpu", "memory", "disk", "system", "uptime"],
                },
            },
        }

    async def execute(self, metrics: list[str] | None = None, **kwargs: Any) -> str:
        if metrics is None:
            metrics = ["cpu", "memory", "disk", "system", "uptime"]

        result: dict[str, Any] = {}

        for metric in metrics:
            if metric == "cpu":
                result["cpu"] = self._get_cpu_info()
            elif metric == "memory":
                result["memory"] = self._get_memory_info()
            elif metric == "disk":
                result["disk"] = self._get_disk_info()
            elif metric == "network":
                result["network"] = self._get_network_info()
            elif metric == "system":
                result["system"] = self._get_system_info()
            elif metric == "uptime":
                result["uptime"] = self._get_uptime_info()
            elif metric == "processes":
                result["processes"] = self._get_process_info()
            elif metric == "io":
                result["io"] = self._get_io_info()

        return json.dumps(result, indent=2)

    def _get_cpu_info(self) -> dict[str, Any]:
        return {
            "usage_percent": psutil.cpu_percent(interval=0.1),
            "per_core": psutil.cpu_percent(interval=0.1, percpu=True),
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True),
            "load_average": (
                psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else None
            ),
        }

    def _get_memory_info(self) -> dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "free": mem.free,
            "active": getattr(mem, "active", None),
            "inactive": getattr(mem, "inactive", None),
            "buffers": getattr(mem, "buffers", None),
            "cached": getattr(mem, "cached", None),
            "shared": getattr(mem, "shared", None),
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
            },
        }

    def _get_disk_info(self) -> list[dict[str, Any]]:
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "mount": partition.mountpoint,
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except PermissionError:
                continue
        return disks

    def _get_network_info(self) -> dict[str, Any]:
        net_io = psutil.net_io_counters(pernic=True)
        interfaces = {}
        for name, stats in net_io.items():
            interfaces[name] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errin": stats.errin,
                "errout": stats.errout,
                "dropin": stats.dropin,
                "dropout": stats.dropout,
            }

        conn_stats = psutil.net_connections(kind="inet")
        states: dict[str, int] = {}
        for conn in conn_stats:
            if conn.status:
                states[conn.status] = states.get(conn.status, 0) + 1

        return {
            "interfaces": interfaces,
            "connection_states": states,
        }

    def _get_system_info(self) -> dict[str, Any]:
        return {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "kernel": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "boot_time": psutil.boot_time(),
        }

    def _get_uptime_info(self) -> dict[str, Any]:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        return {
            "seconds": int(uptime_seconds),
            "boot_time": boot_time,
            "boot_time_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time)),
            "days": int(uptime_seconds // 86400),
            "hours": int((uptime_seconds % 86400) // 3600),
            "minutes": int((uptime_seconds % 3600) // 60),
        }

    def _get_process_info(self) -> dict[str, Any]:
        cpu_procs = []
        mem_procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                if info["cpu_percent"] is not None:
                    cpu_procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": round(info["cpu_percent"], 1),
                        "memory_percent": round(info["memory_percent"] or 0, 1),
                    })
                if info["memory_percent"] is not None and info["memory_percent"] > 0:
                    mem_procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": round(info["cpu_percent"] or 0, 1),
                        "memory_percent": round(info["memory_percent"], 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        cpu_procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        mem_procs.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
        return {
            "top_cpu": cpu_procs[:5],
            "top_memory": mem_procs[:5],
            "total": len(psutil.pids()),
        }

    def _get_io_info(self) -> dict[str, Any]:
        try:
            io = psutil.disk_io_counters()
            if io:
                return {
                    "read_count": io.read_count,
                    "write_count": io.write_count,
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes,
                    "read_time": io.read_time,
                    "write_time": io.write_time,
                }
        except Exception:
            pass
        return {}
