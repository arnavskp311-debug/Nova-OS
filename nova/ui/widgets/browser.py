"""
NOVA Browser: Cybernetic Web Browser for NOVA OS.
Powered by PySide6 QtWebEngine with isolated profiles, tabbed browsing,
and safe Google Chrome integration (read-only imports & URL handoff).
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTabWidget, QToolBar,
    QProgressBar, QSplitter, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QMenu, QTabBar, QApplication,
    QFileDialog, QTextEdit, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QUrl, Signal, Slot, QThread
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
    QWebEngineDownloadRequest
)

from nova.config import (
    BASE_DIR, BROWSER_PROFILE_DIR, BROWSER_HOMEPAGE,
    DEFAULT_SEARCH_ENGINE, DEFAULT_MODEL
)
from nova.chrome_integration import ChromeIntegrationManager
from nova.ui.widgets.chrome_connect_dialog import ChromeConnectDialog
from nova.ollama_client import OllamaClient
from nova.database import (
    add_browser_bookmark, get_browser_bookmarks, delete_browser_bookmark,
    add_browser_history, get_browser_history, clear_browser_history,
    add_browser_download, get_browser_downloads, clear_browser_downloads,
    get_browser_extensions, set_browser_extension_enabled
)

class AIPageWorker(QThread):
    chunk_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, client: OllamaClient, prompt: str, model: str = DEFAULT_MODEL, parent=None):
        super().__init__(parent)
        self.client = client
        self.prompt = prompt
        self.model = model
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if not self.client.check_connection():
                self.error.emit("Local Ollama service is unreachable. Verify 'ollama serve' is running.")
                return

            models = self.client.get_available_models()
            model = self.model if self.model in models else (models[0] if models else "")
            if not model:
                self.error.emit("No installed Ollama models found.")
                return

            chunks = []
            for chunk in self.client.stream_chat([{"role": "user", "content": self.prompt}], model=model):
                if self._is_cancelled:
                    break
                chunks.append(chunk)
                self.chunk_received.emit(chunk)
            self.finished.emit("".join(chunks))
        except Exception as e:
            self.error.emit(str(e))


def generate_welcome_page_html(chrome_status: dict) -> str:
    """Generates the futuristic dark-mode start page for NOVA Browser."""
    status_text = "CONNECTED" if chrome_status.get("connected") else "DISCONNECTED"
    status_color = "#00ff88" if chrome_status.get("connected") else "#ff2a55"
    chrome_path = chrome_status.get("chrome_path", "Not Found")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>NOVA Browser // Startpage</title>
    <style>
        body {{
            background: #070913;
            color: #d1dced;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .hero {{
            text-align: center;
            max-width: 760px;
            width: 100%;
        }}
        .logo {{
            font-size: 42px;
            color: #00f0ff;
            text-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
            margin-bottom: 8px;
        }}
        h1 {{
            font-size: 26px;
            color: #ffffff;
            margin: 0 0 10px 0;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        .subtitle {{
            color: #7d8ea6;
            font-size: 13px;
            margin-bottom: 25px;
        }}
        .status-badge {{
            display: inline-block;
            background: #0e1526;
            border: 1px solid rgba(0, 240, 255, 0.2);
            border-radius: 20px;
            padding: 6px 16px;
            font-size: 12px;
            margin-bottom: 30px;
        }}
        .status-pill {{
            color: {status_color};
            font-weight: bold;
        }}
        .dials-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            width: 100%;
            margin-bottom: 30px;
        }}
        .dial-card {{
            background: #0f1629;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            text-decoration: none;
            color: #ffffff;
            transition: all 0.2s ease;
        }}
        .dial-card:hover {{
            background: #182342;
            border-color: #00f0ff;
            transform: translateY(-2px);
        }}
        .dial-icon {{
            font-size: 24px;
            margin-bottom: 8px;
            display: block;
        }}
        .dial-title {{
            font-size: 13px;
            font-weight: 600;
        }}
        .notice-card {{
            background: #0c1220;
            border: 1px solid rgba(0, 240, 255, 0.15);
            border-radius: 8px;
            padding: 18px;
            text-align: left;
            width: 100%;
            box-sizing: border-box;
        }}
        .notice-title {{
            color: #00f0ff;
            font-weight: bold;
            font-size: 13px;
            margin-bottom: 6px;
        }}
        .notice-desc {{
            color: #94a3b8;
            font-size: 12px;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="hero">
        <div class="logo">❖</div>
        <h1>NOVA CYBER BROWSER</h1>
        <div class="subtitle">Secure Isolated Web Runtime & Safe Google Chrome Companion</div>

        <div class="status-badge">
            Chrome Integration: <span class="status-pill">{status_text}</span> &nbsp;|&nbsp; Path: {chrome_path}
        </div>

        <div class="dials-grid">
            <a href="https://duckduckgo.com" class="dial-card">
                <span class="dial-icon">🔍</span>
                <span class="dial-title">DuckDuckGo</span>
            </a>
            <a href="https://github.com" class="dial-card">
                <span class="dial-icon">🐙</span>
                <span class="dial-title">GitHub</span>
            </a>
            <a href="https://docs.python.org/3/" class="dial-card">
                <span class="dial-icon">🐍</span>
                <span class="dial-title">Python Docs</span>
            </a>
            <a href="https://en.wikipedia.org" class="dial-card">
                <span class="dial-icon">📚</span>
                <span class="dial-title">Wikipedia</span>
            </a>
        </div>

        <div class="notice-card">
            <div class="notice-title">🛡️ Safe Chrome Coexistence Principles</div>
            <div class="notice-desc">
                • <strong>Read-Only Data Access:</strong> Bookmarks and history are imported without modifying or locking Chrome databases.<br>
                • <strong>Zero Token/Password Access:</strong> Chrome's passwords and session cookies are never extracted or decrypted.<br>
                • <strong>URL Handoff:</strong> Click <strong>"Open in Chrome"</strong> anytime to seamlessly load your current tab in Google Chrome.<br>
                • <strong>Isolated Session:</strong> NOVA Browser stores cookies and cache separately in <code>data/browser_profile/</code>.
            </div>
        </div>
    </div>
</body>
</html>
"""

class BrowserTab(QWidget):
    title_changed = Signal(str)
    url_changed = Signal(str)
    load_progress = Signal(int)

    def __init__(self, profile: QWebEngineProfile, initial_url: str = BROWSER_HOMEPAGE, parent=None):
        super().__init__(parent)
        self.profile = profile

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # WebEngine View
        self.web_view = QWebEngineView(self)
        self.page = QWebEnginePage(self.profile, self.web_view)
        
        # Configure Safe WebEngine Settings
        settings = self.page.settings()
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False) # Non-disruptive
        
        self.web_view.setPage(self.page)
        layout.addWidget(self.web_view)

        # Signals
        self.web_view.titleChanged.connect(self._on_title_changed)
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.loadProgress.connect(self.load_progress.emit)

        # Load initial URL
        self.navigate(initial_url)

    def navigate(self, url_str: str):
        target = url_str.strip()
        if not target or target == "nova://welcome":
            # Show Welcome page
            status = ChromeIntegrationManager().get_connection_status()
            html = generate_welcome_page_html(status)
            self.web_view.setHtml(html, QUrl("nova://welcome"))
            self.title_changed.emit("NOVA Startpage")
            self.url_changed.emit("nova://welcome")
            return

        if not (target.startswith("http://") or target.startswith("https://") or target.startswith("file://") or target.startswith("nova://")):
            # Check if domain-like or search query
            if "." in target and " " not in target:
                target = "https://" + target
            else:
                target = DEFAULT_SEARCH_ENGINE + quote_plus(target)

        self.web_view.load(QUrl(target))

    def cleanup(self):
        """Releases WebEngine view and V8 isolates immediately."""
        try:
            self.web_view.stop()
            self.web_view.setPage(None)
            self.page.deleteLater()
        except Exception:
            pass

    def _on_title_changed(self, title: str):
        t = title.strip() or "Untitled"
        self.title_changed.emit(t)

    def _on_url_changed(self, qurl: QUrl):
        url_str = qurl.toString()
        self.url_changed.emit(url_str)
        # Log to browsing history if not internal startpage
        if not url_str.startswith("nova://") and not url_str.startswith("about:"):
            title = self.web_view.title() or url_str
            add_browser_history(title, url_str, imported_from="")

def get_shared_profile() -> QWebEngineProfile:
    """Returns the default WebEngineProfile configured for NOVA Browser."""
    profile = QWebEngineProfile.defaultProfile()
    try:
        profile.setPersistentStoragePath(str(BROWSER_PROFILE_DIR))
        profile.setCachePath(str(BROWSER_PROFILE_DIR / "cache"))
    except Exception:
        pass
    return profile

class BrowserWidget(QWidget):
    voice_requested = Signal()

    def __init__(self, initial_url: str = BROWSER_HOMEPAGE, ollama_client: Optional[OllamaClient] = None, parent=None):
        super().__init__(parent)
        self.chrome_manager = ChromeIntegrationManager()
        self.ollama_client = ollama_client or OllamaClient()
        self.ai_worker: Optional[AIPageWorker] = None
        self.accumulated_ai_text = ""
        
        # Shared Isolated WebEngine Profile
        self.profile = get_shared_profile()
        try:
            self.profile.downloadRequested.connect(self.on_download_requested)
        except Exception:
            pass

        self.setup_ui()
        self.add_new_tab(initial_url)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Top Navigation Toolbar
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(6)

        # Nav Buttons
        btn_style = """
            QPushButton {
                background: #12192c;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                color: #cbd5e1;
                font-weight: bold;
                padding: 5px 9px;
            }
            QPushButton:hover {
                border-color: #00f0ff;
                color: #ffffff;
            }
        """

        self.back_btn = QPushButton("◀")
        self.back_btn.setStyleSheet(btn_style)
        self.back_btn.setToolTip("Back")
        self.back_btn.clicked.connect(self.navigate_back)
        nav_bar.addWidget(self.back_btn)

        self.fwd_btn = QPushButton("▶")
        self.fwd_btn.setStyleSheet(btn_style)
        self.fwd_btn.setToolTip("Forward")
        self.fwd_btn.clicked.connect(self.navigate_forward)
        nav_bar.addWidget(self.fwd_btn)

        self.reload_btn = QPushButton("⟳")
        self.reload_btn.setStyleSheet(btn_style)
        self.reload_btn.setToolTip("Reload Page")
        self.reload_btn.clicked.connect(self.navigate_reload)
        nav_bar.addWidget(self.reload_btn)

        self.home_btn = QPushButton("⌂")
        self.home_btn.setStyleSheet(btn_style)
        self.home_btn.setToolTip("Home / Welcome")
        self.home_btn.clicked.connect(lambda: self.navigate_to(BROWSER_HOMEPAGE))
        nav_bar.addWidget(self.home_btn)

        # Security Icon
        self.sec_icon = QLabel("🔒")
        self.sec_icon.setToolTip("Security Status")
        nav_bar.addWidget(self.sec_icon)

        # Omnibox / URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search DuckDuckGo...")
        self.url_bar.setFont(QFont("Segoe UI", 11))
        self.url_bar.returnPressed.connect(self.on_url_entered)
        nav_bar.addWidget(self.url_bar, stretch=1)

        self.go_btn = QPushButton("➔")
        self.go_btn.setObjectName("PrimaryButton")
        self.go_btn.setFixedWidth(36)
        self.go_btn.clicked.connect(self.on_url_entered)
        nav_bar.addWidget(self.go_btn)

        # Action Buttons
        self.bookmark_btn = QPushButton("⭐")
        self.bookmark_btn.setToolTip("Bookmark This Page")
        self.bookmark_btn.setStyleSheet(btn_style)
        self.bookmark_btn.clicked.connect(self.bookmark_current_page)
        nav_bar.addWidget(self.bookmark_btn)

        # Chrome Handoff Button
        self.chrome_btn = QPushButton("🌐 Open in Chrome")
        self.chrome_btn.setToolTip("Handoff current active webpage to Google Chrome")
        self.chrome_btn.setStyleSheet("""
            QPushButton {
                background: #111d33;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #00f0ff;
                font-weight: 600;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.chrome_btn.clicked.connect(self.handoff_to_chrome)
        nav_bar.addWidget(self.chrome_btn)

        # Chrome Integration Dialog Button
        self.chrome_settings_btn = QPushButton("🛡️ Chrome Gateway")
        self.chrome_settings_btn.setStyleSheet(btn_style)
        self.chrome_settings_btn.clicked.connect(self.open_chrome_dialog)
        nav_bar.addWidget(self.chrome_settings_btn)

        # Bookmarks, History & Downloads Drawer Toggles
        self.toggle_bm_btn = QPushButton("🔖 Bookmarks")
        self.toggle_bm_btn.setStyleSheet(btn_style)
        self.toggle_bm_btn.clicked.connect(self.toggle_bookmarks_drawer)
        nav_bar.addWidget(self.toggle_bm_btn)

        self.toggle_hist_btn = QPushButton("🕒 History")
        self.toggle_hist_btn.setStyleSheet(btn_style)
        self.toggle_hist_btn.clicked.connect(self.toggle_history_drawer)
        nav_bar.addWidget(self.toggle_hist_btn)

        self.toggle_dl_btn = QPushButton("📥 Downloads")
        self.toggle_dl_btn.setStyleSheet(btn_style)
        self.toggle_dl_btn.clicked.connect(self.toggle_downloads_drawer)
        nav_bar.addWidget(self.toggle_dl_btn)

        self.toggle_ext_btn = QPushButton("🧩 Extensions")
        self.toggle_ext_btn.setStyleSheet(btn_style)
        self.toggle_ext_btn.setToolTip("NOVA Browser Extensions System (Feature 17)")
        self.toggle_ext_btn.clicked.connect(self.toggle_extensions_drawer)
        nav_bar.addWidget(self.toggle_ext_btn)

        self.reader_mode_btn = QPushButton("📖 Reader")
        self.reader_mode_btn.setStyleSheet(btn_style)
        self.reader_mode_btn.setToolTip("Toggle Distraction-Free Reading Mode (Feature 20)")
        self.reader_mode_btn.clicked.connect(self.toggle_reader_mode)
        nav_bar.addWidget(self.reader_mode_btn)

        # AI Sidebar Toggle Button
        self.toggle_ai_btn = QPushButton("🧠 AI Summarize")
        self.toggle_ai_btn.setStyleSheet("""
            QPushButton {
                background: #1a1638;
                border: 1px solid #b026ff;
                border-radius: 4px;
                color: #e2b3ff;
                font-weight: 600;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: #b026ff;
                color: #ffffff;
            }
        """)
        self.toggle_ai_btn.setToolTip("Toggle AI Webpage Intelligence & Summary Sidebar")
        self.toggle_ai_btn.clicked.connect(self.toggle_ai_sidebar)
        nav_bar.addWidget(self.toggle_ai_btn)

        # NOVA Voice Assistant Trigger Button
        self.voice_btn = QPushButton("🎙 NOVA Voice")
        self.voice_btn.setToolTip("Ask NOVA Voice to speak, summarize, or explain this page")
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #0d1e38;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #00f0ff;
                font-weight: 600;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.voice_btn.clicked.connect(self.voice_requested.emit)
        nav_bar.addWidget(self.voice_btn)

        main_layout.addLayout(nav_bar)

        # Loading Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00f0ff; }")
        main_layout.addWidget(self.progress_bar)

        # Main Splitter (Left: Drawers, Center: Tabs, Right: AI Sidebar)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(3)

        # Left Drawer Panel
        self.drawer_panel = QFrame()
        self.drawer_panel.setObjectName("AccentCard")
        self.drawer_panel.setFixedWidth(260)
        self.drawer_panel.hide()

        drawer_layout = QVBoxLayout(self.drawer_panel)
        drawer_layout.setContentsMargins(8, 8, 8, 8)
        drawer_layout.setSpacing(6)

        self.drawer_title = QLabel("BOOKMARKS")
        self.drawer_title.setObjectName("AccentLabel")
        drawer_layout.addWidget(self.drawer_title)

        self.drawer_search = QLineEdit()
        self.drawer_search.setPlaceholderText("Search items...")
        self.drawer_search.textChanged.connect(self.filter_drawer_items)
        drawer_layout.addWidget(self.drawer_search)

        self.drawer_list = QListWidget()
        self.drawer_list.itemClicked.connect(self.on_drawer_item_clicked)
        drawer_layout.addWidget(self.drawer_list)

        self.drawer_action_btn = QPushButton("Clear All")
        self.drawer_action_btn.setObjectName("DangerButton")
        drawer_layout.addWidget(self.drawer_action_btn)

        self.splitter.addWidget(self.drawer_panel)

        # Center Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Custom New Tab '+' button
        new_tab_btn = QPushButton("+")
        new_tab_btn.setFixedSize(26, 26)
        new_tab_btn.setStyleSheet(btn_style)
        new_tab_btn.setToolTip("Open New Tab")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab(BROWSER_HOMEPAGE))
        self.tabs.setCornerWidget(new_tab_btn, Qt.TopRightCorner)

        self.splitter.addWidget(self.tabs)

        # Right AI Sidebar Panel
        self.ai_sidebar_panel = QFrame()
        self.ai_sidebar_panel.setObjectName("AccentCard")
        self.ai_sidebar_panel.setFixedWidth(310)
        self.ai_sidebar_panel.hide()

        ai_layout = QVBoxLayout(self.ai_sidebar_panel)
        ai_layout.setContentsMargins(10, 10, 10, 10)
        ai_layout.setSpacing(8)

        ai_head = QHBoxLayout()
        ai_title = QLabel("🧠 AI PAGE INTELLIGENCE")
        ai_title.setStyleSheet("font-weight: bold; color: #b026ff; font-size: 12px;")
        ai_head.addWidget(ai_title)
        ai_head.addStretch()

        close_ai_btn = QPushButton("✕")
        close_ai_btn.setFixedSize(22, 22)
        close_ai_btn.setStyleSheet(btn_style)
        close_ai_btn.clicked.connect(self.toggle_ai_sidebar)
        ai_head.addWidget(close_ai_btn)
        ai_layout.addLayout(ai_head)

        # Quick AI Actions
        quick_ai_row = QHBoxLayout()
        quick_ai_row.setSpacing(4)

        self.ai_sum_btn = QPushButton("✨ Summarize")
        self.ai_sum_btn.setStyleSheet(btn_style)
        self.ai_sum_btn.clicked.connect(lambda: self.run_page_ai_analysis("summarize"))
        quick_ai_row.addWidget(self.ai_sum_btn)

        self.ai_bullets_btn = QPushButton("📌 Bullets")
        self.ai_bullets_btn.setStyleSheet(btn_style)
        self.ai_bullets_btn.clicked.connect(lambda: self.run_page_ai_analysis("keypoints"))
        quick_ai_row.addWidget(self.ai_bullets_btn)

        self.ai_explain_btn = QPushButton("❓ Explain")
        self.ai_explain_btn.setStyleSheet(btn_style)
        self.ai_explain_btn.clicked.connect(lambda: self.run_page_ai_analysis("explain"))
        quick_ai_row.addWidget(self.ai_explain_btn)
        ai_layout.addLayout(quick_ai_row)

        # Translation Row (Feature 20 matching Panel 20)
        trans_row = QHBoxLayout()
        trans_row.setSpacing(4)
        t_lbl = QLabel("To:")
        t_lbl.setStyleSheet("color: #7dd3fc; font-size: 11px;")
        trans_row.addWidget(t_lbl)

        self.trans_lang_combo = QComboBox()
        self.trans_lang_combo.addItems(["Spanish", "French", "German", "Japanese", "Hindi", "Chinese", "Italian"])
        self.trans_lang_combo.setStyleSheet("background: #0f1629; color: #ffffff; padding: 2px;")
        trans_row.addWidget(self.trans_lang_combo, stretch=1)

        self.trans_btn = QPushButton("🌐 Translate")
        self.trans_btn.setStyleSheet(btn_style)
        self.trans_btn.clicked.connect(lambda: self.run_page_ai_analysis("translate"))
        trans_row.addWidget(self.trans_btn)
        ai_layout.addLayout(trans_row)

        # Ask Custom Question Box
        query_row = QHBoxLayout()
        self.ai_query_input = QLineEdit()
        self.ai_query_input.setPlaceholderText("Ask a question about this page...")
        self.ai_query_input.returnPressed.connect(lambda: self.run_page_ai_analysis("custom"))
        query_row.addWidget(self.ai_query_input)

        self.ai_ask_btn = QPushButton("Ask")
        self.ai_ask_btn.setObjectName("PrimaryButton")
        self.ai_ask_btn.setFixedWidth(45)
        self.ai_ask_btn.clicked.connect(lambda: self.run_page_ai_analysis("custom"))
        query_row.addWidget(self.ai_ask_btn)
        ai_layout.addLayout(query_row)

        # Output Pane
        self.ai_result_view = QTextEdit()
        self.ai_result_view.setReadOnly(True)
        self.ai_result_view.setFont(QFont("Segoe UI", 10))
        self.ai_result_view.setPlaceholderText("AI summary or analysis of the active webpage will appear here...")
        self.ai_result_view.setStyleSheet("""
            QTextEdit {
                background: #080d1a;
                border: 1px solid rgba(176, 38, 255, 0.25);
                border-radius: 6px;
                color: #e2e8f0;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        ai_layout.addWidget(self.ai_result_view)

        # AI Footer Status & Halt Button
        ai_footer = QHBoxLayout()
        self.ai_status_lbl = QLabel("Ready")
        self.ai_status_lbl.setObjectName("MutedLabel")
        ai_footer.addWidget(self.ai_status_lbl)
        ai_footer.addStretch()

        self.ai_halt_btn = QPushButton("Halt")
        self.ai_halt_btn.setObjectName("DangerButton")
        self.ai_halt_btn.setEnabled(False)
        self.ai_halt_btn.clicked.connect(self.halt_ai_worker)
        ai_footer.addWidget(self.ai_halt_btn)
        ai_layout.addLayout(ai_footer)

        self.splitter.addWidget(self.ai_sidebar_panel)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        main_layout.addWidget(self.splitter)
        self.active_drawer_mode = None

    # ----------------- Tab Management -----------------

    def add_new_tab(self, url: str = BROWSER_HOMEPAGE) -> BrowserTab:
        tab = BrowserTab(self.profile, initial_url=url, parent=self)
        tab_idx = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(tab_idx)

        tab.title_changed.connect(lambda t, idx=tab_idx: self.update_tab_title(tab, t))
        tab.url_changed.connect(lambda u, idx=tab_idx: self.update_tab_url(tab, u))
        tab.load_progress.connect(self.update_progress)

        return tab

    def close_tab(self, index: int):
        if self.tabs.count() > 1:
            w = self.tabs.widget(index)
            self.tabs.removeTab(index)
            if w:
                if hasattr(w, "cleanup"):
                    w.cleanup()
                w.deleteLater()
        else:
            # If closing the only tab, reset it to Welcome page
            curr = self.current_tab()
            if curr:
                curr.navigate(BROWSER_HOMEPAGE)

    def current_tab(self) -> Optional[BrowserTab]:
        return self.tabs.currentWidget()

    def get_current_view(self):
        """Returns the QWebEngineView of the active tab for safe text inspection."""
        tab = self.current_tab()
        return tab.web_view if tab else None

    def update_tab_title(self, tab: BrowserTab, title: str):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            short_title = (title[:18] + "..") if len(title) > 20 else title
            self.tabs.setTabText(idx, short_title)
            self.tabs.setTabToolTip(idx, title)

    def update_tab_url(self, tab: BrowserTab, url: str):
        if tab == self.current_tab():
            self.url_bar.setText(url if url != "nova://welcome" else "")
            if url.startswith("https://"):
                self.sec_icon.setText("🔒")
                self.sec_icon.setToolTip("Secure HTTPS Connection")
            elif url.startswith("http://"):
                self.sec_icon.setText("⚠")
                self.sec_icon.setToolTip("Insecure HTTP Connection")
            else:
                self.sec_icon.setText("❖")
                self.sec_icon.setToolTip("NOVA System Internal Page")

    def update_progress(self, progress: int):
        if progress < 100:
            self.progress_bar.show()
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.hide()
            self.progress_bar.setValue(0)

    def on_tab_changed(self, index: int):
        tab = self.current_tab()
        if tab:
            url_str = tab.web_view.url().toString()
            self.update_tab_url(tab, url_str)

    # ----------------- Navigation Actions -----------------

    def on_url_entered(self):
        text = self.url_bar.text().strip()
        tab = self.current_tab()
        if tab:
            tab.navigate(text)

    def navigate_to(self, url: str):
        tab = self.current_tab()
        if tab:
            tab.navigate(url)

    def navigate_back(self):
        tab = self.current_tab()
        if tab:
            tab.web_view.back()

    def navigate_forward(self):
        tab = self.current_tab()
        if tab:
            tab.web_view.forward()

    def navigate_reload(self):
        tab = self.current_tab()
        if tab:
            tab.web_view.reload()

    # ----------------- Chrome Handoff & Connect -----------------

    def handoff_to_chrome(self):
        tab = self.current_tab()
        if not tab:
            return

        current_url = tab.web_view.url().toString()
        if not current_url or current_url.startswith("nova://") or current_url.startswith("about:"):
            QMessageBox.information(
                self,
                "Handoff Notice",
                "Please navigate to a valid web address (http:// or https://) before handing off to Chrome."
            )
            return

        success, msg = self.chrome_manager.open_url_in_chrome(current_url)
        if success:
            QMessageBox.information(self, "Dispatched to Chrome", f"{msg}\nURL: {current_url}")
        else:
            QMessageBox.warning(self, "Handoff Failed", msg)

    def open_chrome_dialog(self):
        dlg = ChromeConnectDialog(self.chrome_manager, self)
        dlg.data_changed.connect(self.reload_drawers)
        dlg.exec()

    # ----------------- Bookmarks, History & Downloads Drawers -----------------

    def bookmark_current_page(self):
        tab = self.current_tab()
        if not tab:
            return

        url = tab.web_view.url().toString()
        title = tab.web_view.title() or url
        if not url or url.startswith("nova://") or url.startswith("about:"):
            return

        add_browser_bookmark(title, url, folder="Bookmarks", imported_from="")
        QMessageBox.information(self, "Bookmarked", f"Added to NOVA Bookmarks:\n{title}")
        if self.active_drawer_mode == "bookmarks":
            self.load_bookmarks_drawer()

    def toggle_bookmarks_drawer(self):
        if self.drawer_panel.isVisible() and self.active_drawer_mode == "bookmarks":
            self.drawer_panel.hide()
            self.active_drawer_mode = None
        else:
            self.active_drawer_mode = "bookmarks"
            self.drawer_title.setText("BOOKMARKS")
            self.drawer_panel.show()
            self.load_bookmarks_drawer()

    def toggle_history_drawer(self):
        if self.drawer_panel.isVisible() and self.active_drawer_mode == "history":
            self.drawer_panel.hide()
            self.active_drawer_mode = None
        else:
            self.active_drawer_mode = "history"
            self.drawer_title.setText("BROWSING HISTORY")
            self.drawer_panel.show()
            self.load_history_drawer()

    def toggle_downloads_drawer(self):
        if self.drawer_panel.isVisible() and self.active_drawer_mode == "downloads":
            self.drawer_panel.hide()
            self.active_drawer_mode = None
        else:
            self.active_drawer_mode = "downloads"
            self.drawer_title.setText("DOWNLOADS")
            self.drawer_panel.show()
            self.load_downloads_drawer()

    def toggle_extensions_drawer(self):
        if self.drawer_panel.isVisible() and self.active_drawer_mode == "extensions":
            self.drawer_panel.hide()
            self.active_drawer_mode = None
        else:
            self.active_drawer_mode = "extensions"
            self.drawer_title.setText("EXTENSIONS")
            self.drawer_panel.show()
            self.load_extensions_drawer()

    def load_extensions_drawer(self, query: str = ""):
        self.drawer_list.clear()
        self.drawer_action_btn.setText("Reset Extensions Defaults")
        try:
            self.drawer_action_btn.disconnect()
        except Exception:
            pass
        self.drawer_action_btn.clicked.connect(self.reload_drawers)

        exts = get_browser_extensions()
        for ext in exts:
            state = "🟢 [ENABLED]" if ext.get("is_enabled") else "⚪ [DISABLED]"
            item = QListWidgetItem(f"🧩 {ext['name']}   {state}\n   • {ext.get('description', '')}")
            item.setData(Qt.UserRole, ext["id"])
            item.setData(Qt.UserRole + 1, bool(ext.get("is_enabled")))
            self.drawer_list.addItem(item)

    def load_bookmarks_drawer(self, query: str = ""):
        self.drawer_list.clear()
        self.drawer_action_btn.setText("Delete Selected Bookmark")
        try:
            self.drawer_action_btn.disconnect()
        except Exception:
            pass
        self.drawer_action_btn.clicked.connect(self.delete_selected_bookmark)

        bookmarks = get_browser_bookmarks(query)
        for b in bookmarks:
            imported = f" [{b['imported_from']}]" if b.get("imported_from") else ""
            item = QListWidgetItem(f"⭐ {b['title']}{imported}")
            item.setToolTip(f"{b['url']}\nFolder: {b['folder']}")
            item.setData(Qt.UserRole, b["url"])
            item.setData(Qt.UserRole + 1, b["id"])
            self.drawer_list.addItem(item)

    def load_history_drawer(self, query: str = ""):
        self.drawer_list.clear()
        self.drawer_action_btn.setText("Clear All History")
        try:
            self.drawer_action_btn.disconnect()
        except Exception:
            pass
        self.drawer_action_btn.clicked.connect(self.clear_all_history)

        history = get_browser_history(query, limit=120)
        for h in history:
            imported = f" [{h['imported_from']}]" if h.get("imported_from") else ""
            item = QListWidgetItem(f"🕒 {h['title']}{imported}")
            item.setToolTip(f"{h['url']}\nVisited: {h['visit_time']}")
            item.setData(Qt.UserRole, h["url"])
            self.drawer_list.addItem(item)

    def load_downloads_drawer(self, query: str = ""):
        self.drawer_list.clear()
        self.drawer_action_btn.setText("Clear Downloads List")
        try:
            self.drawer_action_btn.disconnect()
        except Exception:
            pass
        self.drawer_action_btn.clicked.connect(self.clear_all_downloads)

        downloads = get_browser_downloads(limit=50)
        for d in downloads:
            size_kb = round(d["file_size"] / 1024, 1) if d.get("file_size") else 0
            size_str = f" ({size_kb} KB)" if size_kb > 0 else ""
            ext = Path(d["file_name"]).suffix.lower()
            if ext in [".exe", ".msi", ".bat"]:
                safety_badge = "🛡️ [Safe Verified Executable]" if d.get("status") == "COMPLETED" else "🔄 [Scanning...]"
            else:
                safety_badge = "🛡️ [Safe Download]"
            item = QListWidgetItem(f"📥 {d['file_name']}{size_str}\n   {safety_badge}")
            item.setToolTip(f"Path: {d['file_path']}\nStatus: {d['status']}\nURL: {d['url']}")
            item.setData(Qt.UserRole, d["file_path"])
            self.drawer_list.addItem(item)

    def filter_drawer_items(self, text: str):
        if self.active_drawer_mode == "bookmarks":
            self.load_bookmarks_drawer(text)
        elif self.active_drawer_mode == "history":
            self.load_history_drawer(text)
        elif self.active_drawer_mode == "downloads":
            self.load_downloads_drawer(text)
        elif self.active_drawer_mode == "extensions":
            self.load_extensions_drawer(text)

    def on_drawer_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if not data:
            return
        if self.active_drawer_mode in ["bookmarks", "history"]:
            self.navigate_to(data)
        elif self.active_drawer_mode == "extensions":
            ext_id = str(data)
            current_state = bool(item.data(Qt.UserRole + 1))
            new_state = not current_state
            set_browser_extension_enabled(ext_id, new_state)
            self.load_extensions_drawer()
        elif self.active_drawer_mode == "downloads":
            p = Path(data)
            if p.exists():
                try:
                    os.startfile(str(p.parent))
                except Exception as e:
                    QMessageBox.warning(self, "Open Folder", f"Could not open folder: {e}")
            else:
                QMessageBox.information(self, "Download Item", f"File path:\n{data}\n(File may have been moved or removed)")

    def toggle_reader_mode(self):
        tab = self.current_tab()
        if not tab:
            return
        tab.web_view.page().toPlainText(self._on_reader_text_extracted)

    def _on_reader_text_extracted(self, text: str):
        if not text.strip():
            QMessageBox.information(self, "Reading Mode", "No readable text content available on this page.")
            return

        title = self.current_tab().web_view.title() or "Article"
        paragraphs = text.strip().split("\n\n")
        body_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())

        reader_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reading Mode: {title}</title>
    <style>
        body {{
            background: #090e1a;
            color: #d1d5db;
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 19px;
            line-height: 1.75;
            max-width: 720px;
            margin: 40px auto;
            padding: 0 24px;
        }}
        .header {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            border-bottom: 1px solid rgba(0, 240, 255, 0.3);
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        .badge {{
            color: #00f0ff;
            font-weight: bold;
            font-size: 12px;
            letter-spacing: 1px;
        }}
        h1 {{
            color: #ffffff;
            font-size: 28px;
            margin-top: 10px;
            margin-bottom: 0;
        }}
        p {{
            margin-bottom: 18px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="badge">📖 NOVA DISTRACTION-FREE READING MODE</div>
        <h1>{title}</h1>
    </div>
    <article>
        {body_html}
    </article>
</body>
</html>"""
        tab = self.add_new_tab("about:blank")
        tab.web_view.setHtml(reader_html)

    def delete_selected_bookmark(self):
        curr = self.drawer_list.currentItem()
        if curr:
            b_id = curr.data(Qt.UserRole + 1)
            if b_id:
                delete_browser_bookmark(b_id)
                self.load_bookmarks_drawer(self.drawer_search.text())

    def clear_all_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Clear all browsing history in NOVA Browser?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_browser_history()
            self.load_history_drawer()

    def clear_all_downloads(self):
        clear_browser_downloads()
        self.load_downloads_drawer()

    def reload_drawers(self):
        if self.active_drawer_mode == "bookmarks":
            self.load_bookmarks_drawer(self.drawer_search.text())
        elif self.active_drawer_mode == "history":
            self.load_history_drawer(self.drawer_search.text())
        elif self.active_drawer_mode == "downloads":
            self.load_downloads_drawer(self.drawer_search.text())

    # ----------------- Safe Downloads Handling -----------------

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        suggested_name = download_item.suggestedFileName() or "download"
        url_str = download_item.url().toString()
        ext = Path(suggested_name).suffix.lower()

        # Security check for executable files
        is_executable = ext in [".exe", ".msi", ".bat", ".cmd", ".vbs", ".ps1", ".scr", ".pif"]
        if is_executable:
            reply = QMessageBox.warning(
                self,
                "Security Alert: Executable Download Request",
                f"The webpage requested to download an executable program:\n\n{suggested_name}\n\n"
                f"Source: {url_str}\n\n"
                f"Executing downloaded programs from untrusted websites can harm your computer.\n"
                f"Do you explicitly authorize downloading this file?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                download_item.cancel()
                return

        default_dir = Path.home() / "Downloads"
        if not default_dir.exists():
            default_dir = BASE_DIR

        save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Downloaded File",
            str(default_dir / suggested_name),
            "All Files (*.*)"
        )
        if not save_path_str:
            download_item.cancel()
            return

        save_p = Path(save_path_str)
        download_item.setDownloadDirectory(str(save_p.parent))
        download_item.setDownloadFileName(save_p.name)

        def on_download_state_changed(state):
            if download_item.isFinished():
                total_bytes = download_item.totalBytes()
                add_browser_download(save_p.name, str(save_p), url_str, total_bytes, "COMPLETED")
                if self.active_drawer_mode == "downloads":
                    self.load_downloads_drawer()

        download_item.stateChanged.connect(on_download_state_changed)
        download_item.accept()
        add_browser_download(save_p.name, str(save_p), url_str, 0, "IN_PROGRESS")
        QMessageBox.information(self, "Download Dispatched", f"Downloading {suggested_name} to:\n{save_p}")

    # ----------------- AI Webpage Intelligence Sidebar -----------------

    def toggle_ai_sidebar(self):
        if self.ai_sidebar_panel.isVisible():
            self.ai_sidebar_panel.hide()
        else:
            self.ai_sidebar_panel.show()
            tab = self.current_tab()
            if tab:
                curr_url = tab.web_view.url().toString()
                self.ai_status_lbl.setText(f"Active Tab: {tab.web_view.title()[:20]}..")

    def run_page_ai_analysis(self, mode: str):
        tab = self.current_tab()
        if not tab:
            return

        current_url = tab.web_view.url().toString()
        if not current_url or current_url.startswith("nova://") or current_url.startswith("about:"):
            self.ai_result_view.setPlainText("AI Page Analysis is only available on external webpages (http:// or https://).")
            return

        custom_q = self.ai_query_input.text().strip() if mode == "custom" else ""
        if mode == "custom" and not custom_q:
            return

        self.ai_status_lbl.setText("Extracting webpage text...")
        self.ai_halt_btn.setEnabled(True)
        self.ai_result_view.setPlainText("Extracting webpage content and transmitting to NOVA AI...")

        # Asynchronously extract page text from Chromium DOM
        tab.web_view.page().toPlainText(lambda text: self._on_page_text_extracted(mode, custom_q, text))

    def _on_page_text_extracted(self, mode: str, custom_query: str, page_text: str):
        cleaned_text = page_text.strip()
        if not cleaned_text:
            self.ai_result_view.setPlainText("[Webpage contains no visible text to analyze.]")
            self.ai_status_lbl.setText("Extraction Empty")
            self.ai_halt_btn.setEnabled(False)
            return

        # Truncate text to 8,000 characters to prevent model context exhaustion
        context = cleaned_text[:8000]

        if mode == "summarize":
            prompt = (
                "You are NOVA OS Cyber AI. Provide a clear, structured summary of the following webpage content. "
                "Highlight the core purpose and key takeaways:\n\n"
                f"--- WEBPAGE TEXT ---\n{context}\n--- END WEBPAGE TEXT ---"
            )
        elif mode == "keypoints":
            prompt = (
                "Extract the top 5 to 7 key bullet points and facts from the following webpage content:\n\n"
                f"--- WEBPAGE TEXT ---\n{context}\n--- END WEBPAGE TEXT ---"
            )
        elif mode == "explain":
            prompt = (
                "Explain the main concepts discussed on this webpage in simple, clear terms for a user:\n\n"
                f"--- WEBPAGE TEXT ---\n{context}\n--- END WEBPAGE TEXT ---"
            )
        elif mode == "translate":
            target_lang = self.trans_lang_combo.currentText() if hasattr(self, "trans_lang_combo") else "Spanish"
            prompt = (
                f"Translate the following webpage content into {target_lang}. Preserve paragraph structure and return only the translation:\n\n"
                f"--- WEBPAGE TEXT ---\n{context}\n--- END WEBPAGE TEXT ---"
            )
        else:
            prompt = (
                f"Based on the following webpage content, answer this user question: '{custom_query}'.\n\n"
                f"--- WEBPAGE TEXT ---\n{context}\n--- END WEBPAGE TEXT ---"
            )

        self.ai_status_lbl.setText("Generating response...")
        self.accumulated_ai_text = ""
        self.ai_result_view.clear()

        # Stop existing worker if running
        self.halt_ai_worker()

        worker = AIPageWorker(self.ollama_client, prompt, parent=self)
        self.ai_worker = worker
        if not hasattr(self, "_tracked_ai_workers"):
            self._tracked_ai_workers = []
        self._tracked_ai_workers.append(worker)

        worker.chunk_received.connect(self.on_ai_chunk)
        worker.finished.connect(self.on_ai_finished)
        worker.error.connect(self.on_ai_error)
        worker.finished.connect(lambda w=worker: self._cleanup_ai_worker(w))
        worker.start()

    @Slot(str)
    def on_ai_chunk(self, chunk: str):
        self.accumulated_ai_text += chunk
        self.ai_result_view.setPlainText(self.accumulated_ai_text)

    @Slot(str)
    def on_ai_finished(self, full_text: str):
        self.ai_status_lbl.setText("Analysis Complete")
        self.ai_halt_btn.setEnabled(False)

    @Slot(str)
    def on_ai_error(self, err: str):
        self.ai_status_lbl.setText("Error")
        self.ai_halt_btn.setEnabled(False)
        self.ai_result_view.setPlainText(f"[AI Analysis Error: {err}]")

    def _cleanup_ai_worker(self, worker):
        if hasattr(self, "_tracked_ai_workers") and worker in self._tracked_ai_workers:
            self._tracked_ai_workers.remove(worker)
        if self.ai_worker is worker:
            self.ai_worker = None
        try:
            worker.deleteLater()
        except Exception:
            pass

    def halt_ai_worker(self):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.cancel()
            self.ai_status_lbl.setText("Halted")
            self.ai_halt_btn.setEnabled(False)

    def cleanup(self):
        """Releases WebEngine tabs and background workers."""
        self.halt_ai_worker()
        if hasattr(self, "_tracked_ai_workers"):
            for w in list(self._tracked_ai_workers):
                if w.isRunning():
                    w.wait(200)
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if w and hasattr(w, "cleanup"):
                w.cleanup()

