"""
Network Tools, Subnet Map & Mobile Companion Widget for NOVA OS.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QListWidget, QFrame
)
from PySide6.QtCore import Qt

from nova.networking import MobileCompanionServer, SubnetScanner, NetworkSpeedMonitor, RSSFeedReader

class NetworkToolsWidget(QWidget):
    """Network control center and mobile companion launcher."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()
        icon = QLabel("🌐")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("NETWORK TOOLS & MOBILE COMPANION")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(0, 240, 255, 0.25); background: #090e1a; border-radius: 6px; }
            QTabBar::tab { background: #0f1629; color: #94a3b8; padding: 6px 14px; margin-right: 4px; border-radius: 4px; font-weight: 600; }
            QTabBar::tab:selected { background: #0052cc; color: #ffffff; border: 1px solid #00f0ff; }
        """)

        # Tab 1: Mobile Companion
        self.tab_companion = self._create_companion_tab()
        self.tabs.addTab(self.tab_companion, "📱 Phone Companion")

        # Tab 2: LAN Subnet Map
        self.tab_lan = self._create_lan_tab()
        self.tabs.addTab(self.tab_lan, "🗺️ LAN Subnet Map")

        # Tab 3: Ping & Latency
        self.tab_ping = self._create_ping_tab()
        self.tabs.addTab(self.tab_ping, "⚡ Latency & Ping")

        # Tab 4: RSS Reader
        self.tab_rss = self._create_rss_tab()
        self.tabs.addTab(self.tab_rss, "📰 Cyber RSS Reader")

        layout.addWidget(self.tabs)

    def _create_companion_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        card = QFrame()
        card.setStyleSheet("background: #0d1628; border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 8px; padding: 12px;")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(8)

        t_lbl = QLabel("MOBILE WEB COMPANION (PORT 8088)")
        t_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 12px;")
        c_lay.addWidget(t_lbl)

        local_ip = SubnetScanner.get_local_ip()
        self.url_lbl = QLabel(f"Access on your phone's browser: http://{local_ip}:8088")
        self.url_lbl.setStyleSheet("color: #00ff88; font-size: 13px; font-weight: bold;")
        c_lay.addWidget(self.url_lbl)

        desc = QLabel("View live CPU & RAM telemetry, lock your desktop, or flush memory remotely from any smartphone on your local Wi-Fi.")
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        desc.setWordWrap(True)
        c_lay.addWidget(desc)

        btn_row = QHBoxLayout()
        self.start_srv_btn = QPushButton("▶ Start Companion Server")
        self.start_srv_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        self.start_srv_btn.clicked.connect(self._toggle_server)
        btn_row.addWidget(self.start_srv_btn)
        btn_row.addStretch()
        c_lay.addLayout(btn_row)

        lay.addWidget(card)
        lay.addStretch()
        return w

    def _toggle_server(self):
        ok, msg = MobileCompanionServer.start(8088)
        self.url_lbl.setText(msg)
        self.start_srv_btn.setText("● Server Active (Listening on 8088)")
        self.start_srv_btn.setEnabled(False)

    def _create_lan_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Discovered Network Devices on Local Subnet:"))
        bar.addStretch()
        scan_btn = QPushButton("↻ Scan Subnet")
        scan_btn.clicked.connect(self._scan_lan)
        bar.addWidget(scan_btn)
        lay.addLayout(bar)

        self.lan_table = QTableWidget()
        self.lan_table.setColumnCount(3)
        self.lan_table.setHorizontalHeaderLabels(["IP Address", "Device Type", "Status"])
        self.lan_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.lan_table.setStyleSheet("background: #0d1424; color: #e2e8f0;")
        lay.addWidget(self.lan_table)
        self._scan_lan()
        return w

    def _scan_lan(self):
        devs = SubnetScanner.scan_lan()
        self.lan_table.setRowCount(len(devs))
        for r, d in enumerate(devs):
            self.lan_table.setItem(r, 0, QTableWidgetItem(d["ip"]))
            self.lan_table.setItem(r, 1, QTableWidgetItem(d["type"]))
            st = QTableWidgetItem(d["status"])
            st.setForeground(Qt.green)
            self.lan_table.setItem(r, 2, st)

    def _create_ping_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Ping Latency Benchmark:"))
        ping_btn = QPushButton("⚡ Benchmark Latency to DNS Gateways")
        ping_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 8px; border-radius: 4px;")
        ping_btn.clicked.connect(self._run_ping)
        lay.addWidget(ping_btn)

        self.ping_res_box = QFrame()
        self.ping_res_box.setStyleSheet("background: #070b14; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 6px; padding: 12px;")
        pr_lay = QVBoxLayout(self.ping_res_box)

        self.p1_lbl = QLabel("Cloudflare (1.1.1.1): Ready")
        self.p1_lbl.setStyleSheet("color: #00f0ff; font-family: 'Consolas'; font-size: 12px;")
        pr_lay.addWidget(self.p1_lbl)

        self.p2_lbl = QLabel("Google (8.8.8.8): Ready")
        self.p2_lbl.setStyleSheet("color: #00ff88; font-family: 'Consolas'; font-size: 12px;")
        pr_lay.addWidget(self.p2_lbl)

        lay.addWidget(self.ping_res_box)
        lay.addStretch()
        return w

    def _run_ping(self):
        res1 = NetworkSpeedMonitor.ping_host("1.1.1.1")
        res2 = NetworkSpeedMonitor.ping_host("8.8.8.8")
        self.p1_lbl.setText(f"Cloudflare (1.1.1.1): {res1['latency_ms']} ms ({res1['status']})")
        self.p2_lbl.setText(f"Google (8.8.8.8): {res2['latency_ms']} ms ({res2['status']})")

    def _create_rss_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)

        articles = RSSFeedReader.get_sample_articles()
        feed_list = QListWidget()
        feed_list.setStyleSheet("background: #0d1424; color: #cbd5e1;")
        for art in articles:
            feed_list.addItem(f"• {art['title']}\n  Source: {art['source']} ({art['date']})")
        lay.addWidget(feed_list)
        return w
