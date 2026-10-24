"""
NOVA OS System Telemetry & Performance Dashboard.
Real-time monitoring of CPU, RAM, Disk, Network, and active processes.
"""

import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QProgressBar, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor
from nova.system_monitor import SystemMonitor

class TelemetryWorker(QThread):
    metrics_ready = Signal(dict)
    processes_ready = Signal(list)

    def __init__(self, monitor: SystemMonitor):
        super().__init__()
        self.monitor = monitor
        self._running = True
        self._poll_interval = 2.5
        self._paused = False

    def set_interval(self, interval: float):
        self._poll_interval = max(1.0, interval)

    def set_paused(self, paused: bool):
        self._paused = paused

    def stop(self):
        self._running = False
        self.quit()
        self.wait(800)

    def run(self):
        proc_cycle = 0
        while self._running:
            if not self._paused:
                try:
                    data = self.monitor.get_realtime_metrics()
                    self.metrics_ready.emit(data)

                    proc_cycle += 1
                    # Refresh process table every 2 cycles to reduce Win32 system overhead
                    if proc_cycle >= 2:
                        procs = self.monitor.get_top_processes(limit=8)
                        self.processes_ready.emit(procs)
                        proc_cycle = 0
                except Exception:
                    pass

            # Sleep in small slices to allow prompt thread termination
            slept = 0.0
            slice_dur = 0.2
            while self._running and slept < self._poll_interval:
                time.sleep(slice_dur)
                slept += slice_dur

class MetricCard(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("AccentCard")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(6)

        # Header
        top_layout = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("AccentLabel")
        top_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setObjectName("MutedLabel")
        top_layout.addWidget(self.sub_lbl, alignment=Qt.AlignRight)
        self.layout.addLayout(top_layout)

        # Main Value
        self.val_lbl = QLabel("--")
        self.val_lbl.setObjectName("MetricValue")
        self.layout.addWidget(self.val_lbl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        self.layout.addWidget(self.progress)

        # Details
        self.details_lbl = QLabel("")
        self.details_lbl.setObjectName("MutedLabel")
        self.layout.addWidget(self.details_lbl)

    def update_metric(self, value_text: str, percent: float, details_text: str = ""):
        self.val_lbl.setText(value_text)
        self.progress.setValue(int(percent))
        if details_text:
            self.details_lbl.setText(details_text)

class DashboardWidget(QWidget):
    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.static_info = self.monitor.get_static_info()
        self.setup_ui()

        # Start non-blocking asynchronous telemetry worker thread
        self.worker = TelemetryWorker(self.monitor)
        self.worker.metrics_ready.connect(self.on_metrics_ready)
        self.worker.processes_ready.connect(self.on_processes_ready)
        self.worker.start()

    def set_performance_mode(self, mode: str):
        """Adapts polling interval based on performance mode."""
        if mode == "High Fidelity":
            self.worker.set_interval(1.5)
        elif mode == "Low Resource / Battery Saver":
            self.worker.set_interval(5.0)
        else: # Balanced
            self.worker.set_interval(2.5)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.set_paused(False)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "worker") and self.worker.isRunning():
            # Automatically suspend polling when dashboard window is hidden/minimized
            self.worker.set_paused(True)

    def closeEvent(self, event):
        if hasattr(self, "worker"):
            self.worker.stop()
        super().closeEvent(event)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header Banner
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("SYSTEM TELEMETRY & DIAGNOSTICS")
        title.setObjectName("HeaderTitle")
        title_box.addWidget(title)

        status_tag = QLabel(f"Platform: {self.static_info['os_name']} {self.static_info['os_release']} | Safe Trial Mode")
        status_tag.setObjectName("MutedLabel")
        title_box.addWidget(status_tag)
        header.addLayout(title_box)

        self.uptime_badge = QLabel("Uptime: --")
        self.uptime_badge.setStyleSheet("color: #00f0ff; font-weight: 600; padding: 4px 10px; background: #0c1222; border-radius: 6px; border: 1px solid rgba(0, 240, 255, 0.2);")
        header.addWidget(self.uptime_badge, alignment=Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addLayout(header)

        # Grid of Cards
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)

        self.cpu_card = MetricCard("CPU UTILIZATION", f"{self.static_info['cpu_cores_logical']} Cores")
        self.ram_card = MetricCard("VIRTUAL MEMORY", "RAM")
        self.disk_card = MetricCard("PRIMARY STORAGE (C:)", "Disk")
        self.net_card = MetricCard("NETWORK THROUGHPUT", "I/O")

        cards_layout.addWidget(self.cpu_card, 0, 0)
        cards_layout.addWidget(self.ram_card, 0, 1)
        cards_layout.addWidget(self.disk_card, 1, 0)
        cards_layout.addWidget(self.net_card, 1, 1)
        main_layout.addLayout(cards_layout)

        # System Hardware Specs Card
        specs_card = QFrame()
        specs_card.setObjectName("AccentCard")
        specs_layout = QGridLayout(specs_card)
        specs_layout.setContentsMargins(14, 12, 14, 12)
        specs_layout.setSpacing(8)

        specs_title = QLabel("HARDWARE ENVIRONMENT")
        specs_title.setObjectName("AccentLabel")
        specs_layout.addWidget(specs_title, 0, 0, 1, 2)

        specs_layout.addWidget(QLabel("Processor:"), 1, 0)
        specs_layout.addWidget(QLabel(self.static_info["processor"]), 1, 1)

        specs_layout.addWidget(QLabel("Architecture:"), 2, 0)
        specs_layout.addWidget(QLabel(self.static_info["architecture"]), 2, 1)

        specs_layout.addWidget(QLabel("Clock Speed / Base:"), 3, 0)
        specs_layout.addWidget(QLabel(self.static_info["cpu_freq"]), 3, 1)

        self.battery_val = QLabel("Detecting...")
        specs_layout.addWidget(QLabel("Power Supply:"), 4, 0)
        specs_layout.addWidget(self.battery_val, 4, 1)

        main_layout.addWidget(specs_card)

        # Process Monitor Table
        proc_box = QVBoxLayout()
        proc_header = QLabel("ACTIVE PROCESS MONITOR (READ-ONLY TELEMETRY)")
        proc_header.setObjectName("AccentLabel")
        proc_box.addWidget(proc_header)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(4)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "RAM %"])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.proc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.proc_table.setMaximumHeight(180)
        proc_box.addWidget(self.proc_table)

        main_layout.addLayout(proc_box)

    @Slot(dict)
    def on_metrics_ready(self, data: dict):
        """Asynchronously updates UI gauges without blocking the event loop."""
        cpu_pct = data["cpu_percent"]
        self.cpu_card.update_metric(
            f"{cpu_pct:.1f}%",
            cpu_pct,
            f"Core count: {len(data['cpu_cores'])}"
        )

        mem = data["memory"]
        self.ram_card.update_metric(
            f"{mem['percent']:.1f}%",
            mem["percent"],
            f"Used: {mem['used_gb']} GB / {mem['total_gb']} GB"
        )

        disk = data["disk"]
        self.disk_card.update_metric(
            f"{disk['percent']:.1f}%",
            disk["percent"],
            f"Free: {disk['free_gb']} GB / {disk['total_gb']} GB"
        )

        net = data["network"]
        down_rate = f"{net['download_kbps']} KB/s" if net['download_kbps'] < 1024 else f"{(net['download_kbps']/1024):.2f} MB/s"
        up_rate = f"{net['upload_kbps']} KB/s" if net['upload_kbps'] < 1024 else f"{(net['upload_kbps']/1024):.2f} MB/s"
        self.net_card.update_metric(
            f"↓ {down_rate}",
            min(100, int(net["download_kbps"] / 20)),
            f"↑ {up_rate} (Total: {net['total_recv_mb']} MB)"
        )

        bat = data["battery"]
        self.battery_val.setText(f"{bat['status']} ({bat['percent']}%)")

        dyn_info = self.monitor.get_static_info()
        self.uptime_badge.setText(f"Host Uptime: {dyn_info['uptime_str']}")

    @Slot(list)
    def on_processes_ready(self, procs: list):
        """Updates the process table from the background telemetry worker."""
        self.proc_table.setRowCount(len(procs))
        for row, p in enumerate(procs):
            pid_item = QTableWidgetItem(str(p.get("pid", "")))
            name_item = QTableWidgetItem(str(p.get("name", "Unknown")))
            cpu_val = p.get("cpu_percent", 0.0) or 0.0
            mem_val = p.get("memory_percent", 0.0) or 0.0
            cpu_item = QTableWidgetItem(f"{cpu_val:.1f}%")
            mem_item = QTableWidgetItem(f"{mem_val:.1f}%")

            pid_item.setTextAlignment(Qt.AlignCenter)
            cpu_item.setTextAlignment(Qt.AlignCenter)
            mem_item.setTextAlignment(Qt.AlignCenter)

            self.proc_table.setItem(row, 0, pid_item)
            self.proc_table.setItem(row, 1, name_item)
            self.proc_table.setItem(row, 2, cpu_item)
            self.proc_table.setItem(row, 3, mem_item)
