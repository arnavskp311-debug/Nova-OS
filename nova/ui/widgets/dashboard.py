"""
NOVA OS System Telemetry & Performance Dashboard.
Real-time monitoring of CPU, physical RAM, Windows commit charge, disk storage, network I/O,
hardware environment, and active processes with smooth scrolling and high-contrast styling.
"""

import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QProgressBar, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor
from nova.system_monitor import SystemMonitor

class TelemetryWorker(QThread):
    metrics_ready = Signal(dict)
    processes_ready = Signal(list)

    def __init__(self, monitor: SystemMonitor):
        super().__init__()
        self.monitor = monitor
        self._running = True
        self._poll_interval = 2.0
        self._paused = False

    def set_interval(self, interval: float):
        self._poll_interval = max(1.0, interval)

    def set_paused(self, paused: bool):
        self._paused = paused

    def stop(self):
        self._running = False
        self.quit()
        self.wait(600)

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
                        procs = self.monitor.get_top_processes(limit=15)
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
        self.setStyleSheet("""
            QFrame#AccentCard {
                background-color: #0d1527;
                border: 1px solid rgba(0, 240, 255, 0.22);
                border-radius: 8px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(6)

        # Header
        top_layout = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        top_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("color: #8fa0b5; font-size: 11px;")
        top_layout.addWidget(self.sub_lbl, alignment=Qt.AlignRight)
        self.layout.addLayout(top_layout)

        # Main Value
        self.val_lbl = QLabel("Loading...")
        self.val_lbl.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        self.layout.addWidget(self.val_lbl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(7)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #111a2e;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f0ff);
                border-radius: 2px;
            }
        """)
        self.layout.addWidget(self.progress)

        # Details
        self.details_lbl = QLabel("Initializing metrics...")
        self.details_lbl.setStyleSheet("color: #8fa0b5; font-size: 11px;")
        self.details_lbl.setWordWrap(True)
        self.layout.addWidget(self.details_lbl)

    def update_metric(self, value_text: str, percent: float, details_text: str = "", subtitle: str = None):
        self.val_lbl.setText(value_text)
        self.progress.setValue(max(0, min(100, int(percent))))
        if details_text:
            self.details_lbl.setText(details_text)
        if subtitle is not None:
            self.sub_lbl.setText(subtitle)


class DashboardWidget(QWidget):
    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardWidget")
        self.setStyleSheet("QWidget#DashboardWidget { background-color: #090e1a; }")
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
        else:  # Balanced
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
        # Outer layout holds the smooth scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Smooth Scroll Area so layout never clips on smaller window sizes
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #090e1a;
                border: none;
            }
            QScrollBar:vertical {
                background: #0b1122;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1c273e;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00f0ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        container.setObjectName("DashboardScrollContainer")
        container.setStyleSheet("QWidget#DashboardScrollContainer { background-color: #090e1a; }")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Header Banner
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("SYSTEM TELEMETRY & DIAGNOSTICS")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")
        title_box.addWidget(title)

        status_tag = QLabel(f"Platform: {self.static_info['os_name']} {self.static_info['os_release']} ({self.static_info['architecture']}) • Safe Windows Trial")
        status_tag.setStyleSheet("color: #8fa0b5; font-size: 11px;")
        title_box.addWidget(status_tag)
        header.addLayout(title_box)

        self.uptime_badge = QLabel("Uptime: --")
        self.uptime_badge.setStyleSheet("""
            QLabel {
                color: #00f0ff;
                font-weight: 600;
                font-size: 11px;
                padding: 4px 10px;
                background: #0c1424;
                border-radius: 6px;
                border: 1px solid rgba(0, 240, 255, 0.25);
            }
        """)
        header.addWidget(self.uptime_badge, alignment=Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addLayout(header)

        # 2. Grid of 4 Key Metric Cards
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)

        phys = self.static_info['cpu_cores_physical']
        log = self.static_info['cpu_cores_logical']
        sys_drive = self.static_info.get('system_drive', 'C:')

        self.cpu_card = MetricCard("CPU UTILIZATION", f"{phys} Physical / {log} Logical")
        self.ram_card = MetricCard("PHYSICAL RAM", "Hardware Memory")
        self.disk_card = MetricCard(f"PRIMARY STORAGE ({sys_drive})", "System Drive")
        self.net_card = MetricCard("NETWORK THROUGHPUT", "Live Network I/O")

        cards_layout.addWidget(self.cpu_card, 0, 0)
        cards_layout.addWidget(self.ram_card, 0, 1)
        cards_layout.addWidget(self.disk_card, 1, 0)
        cards_layout.addWidget(self.net_card, 1, 1)
        main_layout.addLayout(cards_layout)

        # 3. System Hardware Environment Specs Card
        specs_card = QFrame()
        specs_card.setObjectName("AccentCard")
        specs_card.setStyleSheet("""
            QFrame#AccentCard {
                background-color: #0d1527;
                border: 1px solid rgba(0, 240, 255, 0.18);
                border-radius: 8px;
            }
        """)
        specs_layout = QGridLayout(specs_card)
        specs_layout.setContentsMargins(14, 12, 14, 12)
        specs_layout.setSpacing(8)

        specs_title = QLabel("HARDWARE ENVIRONMENT")
        specs_title.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 12px; letter-spacing: 0.5px;")
        specs_layout.addWidget(specs_title, 0, 0, 1, 2)

        lbl_style = "color: #8fa0b5; font-size: 11px; font-weight: 500;"
        val_style = "color: #ffffff; font-size: 11px; font-weight: 600;"

        def add_spec_row(row, name, val_widget):
            lbl = QLabel(name)
            lbl.setStyleSheet(lbl_style)
            specs_layout.addWidget(lbl, row, 0)
            if isinstance(val_widget, str):
                w = QLabel(val_widget)
                w.setStyleSheet(val_style)
                specs_layout.addWidget(w, row, 1)
            else:
                val_widget.setStyleSheet(val_style)
                specs_layout.addWidget(val_widget, row, 1)

        add_spec_row(1, "Processor Model:", self.static_info["processor"])
        add_spec_row(2, "Architecture:", self.static_info["architecture"])
        add_spec_row(3, "CPU Topology:", f"{phys} Physical Cores • {log} Logical Processors")

        self.clock_val = QLabel(self.static_info.get("cpu_freq", "Unavailable"))
        add_spec_row(4, "Clock Speed / Frequency:", self.clock_val)

        self.commit_val = QLabel("Calculating...")
        add_spec_row(5, "Virtual Memory / Commit Charge:", self.commit_val)

        self.battery_val = QLabel("Detecting...")
        add_spec_row(6, "Power Supply Status:", self.battery_val)

        main_layout.addWidget(specs_card)

        # 4. Live Process Monitor Table
        proc_box = QVBoxLayout()
        proc_box.setSpacing(8)

        proc_header = QLabel("ACTIVE PROCESS MONITOR (READ-ONLY TELEMETRY)")
        proc_header.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 12px; letter-spacing: 0.5px;")
        proc_box.addWidget(proc_header)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(5)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "RAM (MB)", "RAM %"])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.proc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.proc_table.setMinimumHeight(180)
        self.proc_table.setStyleSheet("""
            QTableWidget {
                background-color: #0a1020;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                gridline-color: rgba(255, 255, 255, 0.04);
                color: #cbd5e1;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #10182c;
                color: #00f0ff;
                font-weight: 700;
                font-size: 11px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0052cc;
                color: #ffffff;
            }
        """)
        proc_box.addWidget(self.proc_table)
        main_layout.addLayout(proc_box)

        self.scroll_area.setWidget(container)
        outer_layout.addWidget(self.scroll_area)

    @Slot(dict)
    def on_metrics_ready(self, data: dict):
        """Asynchronously updates UI gauges without blocking the event loop."""
        # 1. CPU
        cpu_pct = data.get("cpu_percent", 0.0)
        phys = self.static_info['cpu_cores_physical']
        log = self.static_info['cpu_cores_logical']
        live_freq = data.get("cpu_freq_live", "Unavailable")
        self.cpu_card.update_metric(
            f"{cpu_pct:.1f}%",
            cpu_pct,
            f"{phys} Physical Cores • {log} Logical Processors | Clock: {live_freq}",
            subtitle=f"{phys} Phys / {log} Log"
        )
        self.clock_val.setText(live_freq)

        # 2. Physical RAM
        mem = data.get("memory", {})
        if mem.get("status") == "Available":
            ram_pct = mem.get("percent", 0.0)
            self.ram_card.update_metric(
                f"{ram_pct:.1f}%",
                ram_pct,
                f"Used: {mem.get('used_gb', 0):.2f} GB / {mem.get('total_gb', 0):.2f} GB • Avail: {mem.get('available_gb', 0):.2f} GB"
            )
        else:
            self.ram_card.update_metric("Unavailable", 0, "Physical RAM metric unavailable.")

        # Virtual / Commit Charge
        cmem = data.get("commit_memory", {})
        if cmem.get("status") == "Available":
            self.commit_val.setText(
                f"Used: {cmem.get('used_gb', 0):.2f} GB / {cmem.get('total_gb', 0):.2f} GB ({cmem.get('percent', 0):.1f}%) • Free: {cmem.get('free_gb', 0):.2f} GB"
            )
        else:
            self.commit_val.setText("Unavailable")

        # 3. Disk (Primary C:)
        disk = data.get("disk", {})
        if disk.get("status") == "Available":
            disk_pct = disk.get("percent", 0.0)
            drive_name = disk.get("drive", "C:")
            self.disk_card.update_metric(
                f"{disk_pct:.1f}%",
                disk_pct,
                f"Used: {disk.get('used_gb', 0):.1f} GB / {disk.get('total_gb', 0):.1f} GB • Free: {disk.get('free_gb', 0):.1f} GB",
                subtitle=f"System Drive ({drive_name})"
            )
        else:
            self.disk_card.update_metric("Unavailable", 0, "System disk reading unavailable.")

        # 4. Network Throughput
        net = data.get("network", {})
        if net.get("status") == "Available":
            down_str = net.get("download_str", "0 B/s")
            up_str = net.get("upload_str", "0 B/s")
            # Normalize progress bar relative to 20 MB/s
            down_kbps = net.get("download_kbps", 0.0)
            prog_val = min(100, int(down_kbps / 200))
            self.net_card.update_metric(
                f"↓ {down_str}",
                prog_val,
                f"↑ Upload: {up_str} • In: {net.get('total_recv_mb', 0):.1f} MB | Out: {net.get('total_sent_mb', 0):.1f} MB"
            )
        else:
            self.net_card.update_metric("Unavailable", 0, "Network I/O unavailable.")

        # 5. Battery / Power
        bat = data.get("battery", {})
        if bat.get("status") != "Unavailable":
            bat_pct_str = f" ({bat.get('percent', 100)}%)" if bat.get("present") else ""
            self.battery_val.setText(f"{bat.get('status', 'AC Powered')}{bat_pct_str}")
        else:
            self.battery_val.setText("Unavailable")

        # 6. Uptime
        dyn_info = self.monitor.get_static_info()
        self.uptime_badge.setText(f"Host Uptime: {dyn_info.get('uptime_str', '--')}")

    @Slot(list)
    def on_processes_ready(self, procs: list):
        """
        Updates the process table from the background telemetry worker.
        Preserves user scroll position so scrolling through processes never jumps or stutters.
        """
        # Save vertical scroll position
        v_bar = self.proc_table.verticalScrollBar()
        cur_scroll = v_bar.value()

        self.proc_table.setRowCount(len(procs))
        for row, p in enumerate(procs):
            pid_item = QTableWidgetItem(str(p.get("pid", "")))
            name_item = QTableWidgetItem(str(p.get("name", "Unknown")))
            cpu_val = p.get("cpu_percent", 0.0) or 0.0
            mem_mb = p.get("memory_mb", 0.0) or 0.0
            mem_pct = p.get("memory_percent", 0.0) or 0.0

            cpu_item = QTableWidgetItem(f"{cpu_val:.1f}%")
            mem_mb_item = QTableWidgetItem(f"{mem_mb:.1f} MB")
            mem_pct_item = QTableWidgetItem(f"{mem_pct:.1f}%")

            pid_item.setTextAlignment(Qt.AlignCenter)
            cpu_item.setTextAlignment(Qt.AlignCenter)
            mem_mb_item.setTextAlignment(Qt.AlignCenter)
            mem_pct_item.setTextAlignment(Qt.AlignCenter)

            self.proc_table.setItem(row, 0, pid_item)
            self.proc_table.setItem(row, 1, name_item)
            self.proc_table.setItem(row, 2, cpu_item)
            self.proc_table.setItem(row, 3, mem_mb_item)
            self.proc_table.setItem(row, 4, mem_pct_item)

        # Restore vertical scroll position
        v_bar.setValue(cur_scroll)
