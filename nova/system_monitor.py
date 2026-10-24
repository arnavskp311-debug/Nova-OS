"""
System Telemetry & Resource Monitor for NOVA OS.
Uses psutil to safely poll read-only hardware and OS metrics.
"""

import time
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, List
import psutil

class SystemMonitor:
    def __init__(self):
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.time()
        self._static_info_cache = None
        self._metrics_cache = None
        self._metrics_cache_time = 0.0
        self._procs_cache = None
        self._procs_cache_time = 0.0
        # Prime psutil cpu_percent
        psutil.cpu_percent(interval=None)

    def get_static_info(self) -> Dict[str, Any]:
        """Returns cached static host OS and hardware details."""
        if self._static_info_cache is not None:
            # Update dynamic uptime
            boot_time = self._static_info_cache["_boot_datetime"]
            uptime = datetime.now() - boot_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self._static_info_cache["uptime_str"] = f"{hours}h {minutes}m {seconds}s"
            return self._static_info_cache

        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        cpu_freq = psutil.cpu_freq()
        cpu_freq_str = f"{cpu_freq.current:.1f} MHz" if cpu_freq else "N/A"

        self._static_info_cache = {
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor() or "Multi-Core CPU",
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "cpu_freq": cpu_freq_str,
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_str": f"{hours}h {minutes}m {seconds}s",
            "python_version": platform.python_version(),
            "_boot_datetime": boot_time
        }
        return self._static_info_cache

    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Polls dynamic hardware metrics with high-efficiency caching."""
        curr_time = time.time()
        if self._metrics_cache and (curr_time - self._metrics_cache_time) < 0.6:
            return self._metrics_cache

        # CPU
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

        # Virtual Memory
        mem = psutil.virtual_memory()
        mem_data = {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "percent": mem.percent
        }

        # Disk C:
        try:
            disk = psutil.disk_usage("C:\\")
            disk_data = {
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "used_gb": round(disk.used / (1024 ** 3), 1),
                "free_gb": round(disk.free / (1024 ** 3), 1),
                "percent": disk.percent
            }
        except Exception:
            disk_data = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}

        # Network Throughput
        net_io = psutil.net_io_counters()
        time_delta = max(curr_time - self._last_net_time, 0.001)

        bytes_sent_per_sec = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
        bytes_recv_per_sec = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta
        self._last_net_io = net_io
        self._last_net_time = curr_time

        net_data = {
            "upload_kbps": round(bytes_sent_per_sec / 1024, 1),
            "download_kbps": round(bytes_recv_per_sec / 1024, 1),
            "total_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 1),
            "total_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 1),
        }

        # Battery
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None

        if battery:
            battery_data = {
                "present": True,
                "percent": round(battery.percent, 1),
                "power_plugged": battery.power_plugged,
                "status": "Plugged In" if battery.power_plugged else "On Battery"
            }
        else:
            battery_data = {
                "present": False,
                "percent": 100,
                "power_plugged": True,
                "status": "AC Powered (Desktop)"
            }

        result = {
            "cpu_percent": cpu_total,
            "cpu_cores": cpu_per_core,
            "memory": mem_data,
            "disk": disk_data,
            "network": net_data,
            "battery": battery_data,
            "timestamp": curr_time
        }
        self._metrics_cache = result
        self._metrics_cache_time = curr_time
        return result

    def get_top_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns top active processes with time-to-live caching to prevent CPU starvation."""
        curr_time = time.time()
        if self._procs_cache is not None and (curr_time - self._procs_cache_time) < 3.5:
            return self._procs_cache

        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                # Filter out dead or 0-cost idle procs to speed up sorting
                mem = info.get('memory_percent') or 0.0
                cpu = info.get('cpu_percent') or 0.0
                if mem > 0.05 or cpu > 0.0:
                    procs.append({
                        'pid': info['pid'],
                        'name': info.get('name') or 'Process',
                        'cpu_percent': cpu,
                        'memory_percent': mem
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort by CPU descending, then Memory
        procs.sort(key=lambda x: (x['cpu_percent'], x['memory_percent']), reverse=True)
        res = procs[:limit]
        self._procs_cache = res
        self._procs_cache_time = curr_time
        return res
