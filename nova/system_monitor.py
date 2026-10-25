"""
System Telemetry & Resource Monitor for NOVA OS.
Uses psutil to safely poll read-only hardware and OS metrics.
Features physical vs. virtual memory separation, physical/logical CPU differentiation,
defensive error handling, and persistent process CPU tracking.
"""

import os
import time
import platform
from datetime import datetime
from typing import Dict, Any, List
import psutil

class SystemMonitor:
    def __init__(self):
        try:
            self._last_net_io = psutil.net_io_counters()
        except Exception:
            self._last_net_io = None
        self._last_net_time = time.time()
        self._static_info_cache = None
        self._metrics_cache = None
        self._metrics_cache_time = 0.0
        self._procs_cache = None
        self._procs_cache_time = 0.0
        self._proc_tracker: Dict[int, psutil.Process] = {}

        # Prime psutil cpu_percent
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def get_static_info(self) -> Dict[str, Any]:
        """Returns cached static host OS and hardware details."""
        if self._static_info_cache is not None:
            # Update dynamic uptime
            try:
                boot_time = self._static_info_cache["_boot_datetime"]
                uptime = datetime.now() - boot_time
                hours, remainder = divmod(int(uptime.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self._static_info_cache["uptime_str"] = f"{hours}h {minutes}m {seconds}s"
            except Exception:
                self._static_info_cache["uptime_str"] = "Unavailable"
            return self._static_info_cache

        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"
            boot_str = boot_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            boot_time = datetime.now()
            uptime_str = "Unavailable"
            boot_str = "Unavailable"

        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq and cpu_freq.current > 0:
                cpu_freq_str = f"{cpu_freq.current:.1f} MHz" if cpu_freq.current < 1000 else f"{(cpu_freq.current / 1000):.2f} GHz"
            else:
                cpu_freq_str = "Unavailable"
        except Exception:
            cpu_freq_str = "Unavailable"

        phys_cores = psutil.cpu_count(logical=False) or 1
        log_cores = psutil.cpu_count(logical=True) or 1
        sys_drive = os.environ.get("SystemDrive", "C:")

        self._static_info_cache = {
            "os_name": platform.system() or "Windows",
            "os_release": platform.release() or "11",
            "os_version": platform.version() or "",
            "architecture": platform.machine() or "AMD64",
            "processor": platform.processor() or "Multi-Core Processor",
            "cpu_cores_physical": phys_cores,
            "cpu_cores_logical": log_cores,
            "cpu_cores_str": f"{phys_cores} Physical / {log_cores} Logical",
            "cpu_freq": cpu_freq_str,
            "system_drive": sys_drive,
            "boot_time": boot_str,
            "uptime_str": uptime_str,
            "python_version": platform.python_version(),
            "_boot_datetime": boot_time
        }
        return self._static_info_cache

    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Polls dynamic hardware metrics with physical vs virtual RAM separation and defensive error handling."""
        curr_time = time.time()
        if self._metrics_cache and (curr_time - self._metrics_cache_time) < 0.6:
            return self._metrics_cache

        # 1. CPU (Total and per-core from the same calculation)
        try:
            cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
            if cpu_per_core:
                cpu_total = sum(cpu_per_core) / len(cpu_per_core)
            else:
                cpu_total = psutil.cpu_percent(interval=None)
                cpu_per_core = [cpu_total]
        except Exception:
            cpu_total = 0.0
            cpu_per_core = []

        # Live CPU Clock frequency
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current > 0:
                live_freq_str = f"{freq.current:.1f} MHz" if freq.current < 1000 else f"{(freq.current / 1000):.2f} GHz"
            else:
                live_freq_str = "Unavailable"
        except Exception:
            live_freq_str = "Unavailable"

        # 2. Physical RAM (Hardware Memory)
        try:
            vm = psutil.virtual_memory()
            total_ram_b = vm.total
            avail_ram_b = vm.available
            used_ram_b = max(0, total_ram_b - avail_ram_b)
            ram_data = {
                "total_gb": round(total_ram_b / (1024 ** 3), 2),
                "used_gb": round(used_ram_b / (1024 ** 3), 2),
                "available_gb": round(avail_ram_b / (1024 ** 3), 2),
                "percent": round(vm.percent, 1),
                "status": "Available"
            }
        except Exception:
            ram_data = {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "percent": 0.0,
                "status": "Unavailable"
            }

        # 3. Virtual Memory / Windows Commit Charge (Pagefile)
        try:
            sm = psutil.swap_memory()
            commit_total_b = sm.total
            commit_used_b = sm.used
            commit_free_b = sm.free
            commit_data = {
                "total_gb": round(commit_total_b / (1024 ** 3), 2),
                "used_gb": round(commit_used_b / (1024 ** 3), 2),
                "free_gb": round(commit_free_b / (1024 ** 3), 2),
                "percent": round(sm.percent, 1),
                "status": "Available"
            }
        except Exception:
            commit_data = {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "percent": 0.0,
                "status": "Unavailable"
            }

        # 4. Primary Disk (System Drive - C:\)
        sys_drive = os.environ.get("SystemDrive", "C:")
        drive_path = sys_drive + "\\" if not sys_drive.endswith("\\") else sys_drive
        try:
            disk = psutil.disk_usage(drive_path)
            d_total_b = disk.total
            d_free_b = disk.free
            d_used_b = disk.used
            disk_pct = disk.percent
            disk_data = {
                "drive": sys_drive,
                "total_gb": round(d_total_b / (1024 ** 3), 1),
                "used_gb": round(d_used_b / (1024 ** 3), 1),
                "free_gb": round(d_free_b / (1024 ** 3), 1),
                "percent": round(disk_pct, 1),
                "status": "Available"
            }
        except Exception:
            disk_data = {
                "drive": sys_drive,
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "percent": 0.0,
                "status": "Unavailable"
            }

        # 5. Network Throughput (Consistent units & clear upload/download labeling)
        try:
            net_io = psutil.net_io_counters()
            time_delta = max(curr_time - self._last_net_time, 0.001)

            if self._last_net_io is not None:
                bytes_sent_sec = max(0.0, (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta)
                bytes_recv_sec = max(0.0, (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta)
            else:
                bytes_sent_sec = 0.0
                bytes_recv_sec = 0.0

            self._last_net_io = net_io
            self._last_net_time = curr_time

            def _fmt_rate(bps: float) -> str:
                if bps < 1024:
                    return f"{bps:.0f} B/s"
                elif bps < 1024 * 1024:
                    return f"{(bps / 1024):.1f} KB/s"
                else:
                    return f"{(bps / (1024 * 1024)):.2f} MB/s"

            net_data = {
                "download_str": _fmt_rate(bytes_recv_sec),
                "upload_str": _fmt_rate(bytes_sent_sec),
                "download_kbps": round(bytes_recv_sec / 1024, 1),
                "upload_kbps": round(bytes_sent_sec / 1024, 1),
                "total_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 1),
                "total_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 1),
                "status": "Available"
            }
        except Exception:
            net_data = {
                "download_str": "Unavailable",
                "upload_str": "Unavailable",
                "download_kbps": 0.0,
                "upload_kbps": 0.0,
                "total_recv_mb": 0.0,
                "total_sent_mb": 0.0,
                "status": "Unavailable"
            }

        # 6. Battery / Power Supply
        try:
            battery = psutil.sensors_battery()
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
                    "status": "AC Powered (Desktop / Virtual)"
                }
        except Exception:
            battery_data = {
                "present": False,
                "percent": 0,
                "power_plugged": False,
                "status": "Unavailable"
            }

        result = {
            "cpu_percent": round(cpu_total, 1),
            "cpu_cores": cpu_per_core,
            "cpu_freq_live": live_freq_str,
            "memory": ram_data,
            "commit_memory": commit_data,
            "commit": commit_data,
            "disk": disk_data,
            "network": net_data,
            "battery": battery_data,
            "timestamp": curr_time
        }
        self._metrics_cache = result
        self._metrics_cache_time = curr_time
        return result

    def get_top_processes(self, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Returns top active processes by real CPU utilization and RAM working set (MB).
        Uses persistent process tracking to ensure psutil accurately measures non-zero CPU.
        Safely catches and handles NoSuchProcess, AccessDenied, and transient OS errors.
        """
        curr_time = time.time()
        if self._procs_cache is not None and (curr_time - self._procs_cache_time) < 1.8:
            return self._procs_cache

        try:
            current_pids = set(psutil.pids())
        except Exception:
            current_pids = set()

        # Prune dead PIDs from process tracker
        for pid in list(self._proc_tracker.keys()):
            if pid not in current_pids:
                del self._proc_tracker[pid]

        procs = []
        for pid in current_pids:
            if pid == 0:  # Skip System Idle Process
                continue
            try:
                if pid in self._proc_tracker:
                    p = self._proc_tracker[pid]
                else:
                    p = psutil.Process(pid)
                    try:
                        p.cpu_percent(None)  # Prime baseline
                    except Exception:
                        pass
                    self._proc_tracker[pid] = p

                cpu = p.cpu_percent(None)
                try:
                    mem_info = p.memory_info()
                    mem_mb = mem_info.rss / (1024 ** 2)
                except Exception:
                    mem_mb = 0.0

                try:
                    mem_pct = p.memory_percent()
                except Exception:
                    mem_pct = 0.0

                try:
                    name = p.name()
                except Exception:
                    name = "Process"

                # Filter out negligible idle background noise
                if cpu > 0.0 or mem_mb > 15.0:
                    procs.append({
                        "pid": pid,
                        "name": name,
                        "cpu_percent": round(cpu, 1),
                        "memory_mb": round(mem_mb, 1),
                        "memory_percent": round(mem_pct, 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                if pid in self._proc_tracker:
                    del self._proc_tracker[pid]
                continue

        # Sort by CPU descending, then Memory MB
        procs.sort(key=lambda x: (x["cpu_percent"], x["memory_mb"]), reverse=True)
        res = procs[:limit]
        self._procs_cache = res
        self._procs_cache_time = curr_time
        return res
