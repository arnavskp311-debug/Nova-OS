"""
Windows 11 Shell Tools & Subsystems Widget for NOVA OS.
Tabbed interface for:
1. WSL2 Linux Terminal & Distro Launcher
2. Windows Services Manager
3. DNS & Privacy Hosts Switcher
4. File Hash & Integrity Verifier
5. GPU & DirectX Hardware Telemetry
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QTextEdit, QComboBox, QFileDialog, QFrame
)
from PySide6.QtCore import Qt

from nova.windows_subsystem import (
    WSLBridge, WindowsServicesManager, DNSHostsSwitcher,
    FileIntegrityVerifier, GPUAcceleratorMonitor
)

class WindowsShellToolsWidget(QWidget):
    """Interactive control center for Windows subsystems and tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🪟")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("WINDOWS SUBSYSTEMS & SHELL TOOLS")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(0, 240, 255, 0.25);
                background-color: #090e1a;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #0f1629;
                color: #94a3b8;
                padding: 6px 14px;
                margin-right: 4px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #0052cc;
                color: #ffffff;
                border: 1px solid #00f0ff;
            }
        """)

        # Tab 1: WSL2
        self.tab_wsl = self._create_wsl_tab()
        self.tabs.addTab(self.tab_wsl, "🐧 WSL2 Linux")

        # Tab 2: Windows Services
        self.tab_services = self._create_services_tab()
        self.tabs.addTab(self.tab_services, "⚙ Services Manager")

        # Tab 3: DNS Switcher
        self.tab_dns = self._create_dns_tab()
        self.tabs.addTab(self.tab_dns, "🛡 DNS & Hosts")

        # Tab 4: File Hash
        self.tab_hash = self._create_hash_tab()
        self.tabs.addTab(self.tab_hash, "🔐 Hash Verifier")

        # Tab 5: GPU Telemetry
        self.tab_gpu = self._create_gpu_tab()
        self.tabs.addTab(self.tab_gpu, "🎮 GPU VRAM")

        layout.addWidget(self.tabs)

    def _create_wsl_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        head_row = QHBoxLayout()
        distros = WSLBridge.list_distributions()
        distro_names = [d["name"] for d in distros]
        self.distro_combo = QComboBox()
        self.distro_combo.addItems(distro_names)
        head_row.addWidget(QLabel("Distro:"))
        head_row.addWidget(self.distro_combo)
        head_row.addStretch()
        lay.addLayout(head_row)

        self.wsl_output = QTextEdit()
        self.wsl_output.setReadOnly(True)
        self.wsl_output.setStyleSheet("background: #070b14; color: #00ff88; font-family: 'Consolas'; font-size: 11px;")
        self.wsl_output.setPlainText("WSL2 Linux Bridge Ready. Enter bash commands below.\n")
        lay.addWidget(self.wsl_output)

        cmd_row = QHBoxLayout()
        self.wsl_input = QLineEdit()
        self.wsl_input.setPlaceholderText("e.g. uname -a, ls -la, python3 --version, docker ps")
        self.wsl_input.returnPressed.connect(self._run_wsl_cmd)
        cmd_row.addWidget(self.wsl_input)

        run_btn = QPushButton("Execute ↵")
        run_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        run_btn.clicked.connect(self._run_wsl_cmd)
        cmd_row.addWidget(run_btn)
        lay.addLayout(cmd_row)
        return w

    def _run_wsl_cmd(self):
        cmd = self.wsl_input.text().strip()
        if not cmd:
            return
        distro = self.distro_combo.currentText()
        self.wsl_output.append(f"$ {cmd}")
        ok, out = WSLBridge.run_bash(cmd, distro)
        self.wsl_output.append(out + "\n")
        self.wsl_input.clear()

    def _create_services_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Windows Background Services"))
        bar.addStretch()
        ref_btn = QPushButton("↻ Refresh")
        ref_btn.clicked.connect(self._refresh_services)
        bar.addWidget(ref_btn)
        lay.addLayout(bar)

        self.srv_table = QTableWidget()
        self.srv_table.setColumnCount(3)
        self.srv_table.setHorizontalHeaderLabels(["Service Name", "Display Name", "Status"])
        self.srv_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.srv_table.setStyleSheet("background: #0d1424; color: #e2e8f0;")
        lay.addWidget(self.srv_table)
        self._refresh_services()
        return w

    def _refresh_services(self):
        services = WindowsServicesManager.list_services(limit=30)
        self.srv_table.setRowCount(len(services))
        for r, s in enumerate(services):
            self.srv_table.setItem(r, 0, QTableWidgetItem(s["name"]))
            self.srv_table.setItem(r, 1, QTableWidgetItem(s["display"]))
            stat_item = QTableWidgetItem(s["status"])
            stat_item.setForeground(Qt.green if s["status"] == "Running" else Qt.gray)
            self.srv_table.setItem(r, 2, stat_item)

    def _create_dns_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Select Secure DNS Resolver Profile:"))
        self.dns_combo = QComboBox()
        profiles = DNSHostsSwitcher.get_profiles()
        for k, p in profiles.items():
            self.dns_combo.addItem(f"{p['name']} ({p['primary']}, {p['secondary']})", k)
        lay.addWidget(self.dns_combo)

        apply_btn = QPushButton("Apply Secure DNS Profile")
        apply_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 8px; border-radius: 4px;")
        apply_btn.clicked.connect(self._apply_dns)
        lay.addWidget(apply_btn)

        self.dns_status = QLabel("Current DNS: Default Network Gateway")
        self.dns_status.setStyleSheet("color: #00ff88; font-size: 11px;")
        lay.addWidget(self.dns_status)
        lay.addStretch()
        return w

    def _apply_dns(self):
        key = self.dns_combo.currentData()
        ok, msg = DNSHostsSwitcher.apply_dns(key)
        self.dns_status.setText(msg)

    def _create_hash_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        pick_btn = QPushButton("📂 Select Target File to Hash")
        pick_btn.clicked.connect(self._pick_hash_file)
        lay.addWidget(pick_btn)

        self.hash_results = QTextEdit()
        self.hash_results.setReadOnly(True)
        self.hash_results.setStyleSheet("background: #070b14; color: #00f0ff; font-family: 'Consolas'; font-size: 11px;")
        lay.addWidget(self.hash_results)
        return w

    def _pick_hash_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select File to Hash")
        if fname:
            res = FileIntegrityVerifier.compute_hashes(fname)
            self.hash_results.setPlainText(
                f"File: {res.get('file_name')}\n"
                f"Size: {res.get('size_bytes')} bytes\n\n"
                f"MD5:    {res.get('md5')}\n"
                f"SHA-1:  {res.get('sha1')}\n"
                f"SHA256: {res.get('sha256')}\n"
            )

    def _create_gpu_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        gpu = GPUAcceleratorMonitor.get_gpu_telemetry()
        card = QFrame()
        card.setStyleSheet("background: #0d1628; border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 8px; padding: 12px;")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(8)

        name_lbl = QLabel(f"🎮 Accelerator: {gpu['gpu_name']}")
        name_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        c_lay.addWidget(name_lbl)

        vram_lbl = QLabel(f"Dedicated VRAM: {gpu['vram_total_mb']} MB (Used: {gpu['vram_used_mb']} MB)")
        vram_lbl.setStyleSheet("color: #00ff88; font-size: 11px;")
        c_lay.addWidget(vram_lbl)

        drv_lbl = QLabel(f"Architecture: {gpu['driver_version']}")
        drv_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        c_lay.addWidget(drv_lbl)

        lay.addWidget(card)
        lay.addStretch()
        return w
