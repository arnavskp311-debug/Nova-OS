from nova.ui.widgets.os_matrix_cockpit import OSMatrixCockpitWidget
from nova.ui.left_sidebar import LeftNavSidebar
from nova.ui.right_dashboard import RightSystemDashboard
from nova.ui.workspace_bar import WorkspaceThumbnailBar
from nova.ui.widgets.windows_shell_tools import WindowsShellToolsWidget
from nova.ui.widgets.media_hub import MediaHubWidget
from nova.ui.widgets.arcade_hub import ArcadeHubWidget
from nova.ui.widgets.network_tools import NetworkToolsWidget
from nova.ui.widgets.security_fortress_widget import SecurityFortressWidget
from nova.ui.widgets.productivity_hub import ProductivityHubWidget
from nova.ui.alt_tab_hud import AltTabHUD
from nova.ui.lock_screen import CyberLockScreen
from nova.usb_manager import USBManager
from nova.recycle_bin import RecycleBinWidget
from nova.ui.widgets.startup_manager import StartupManager
from nova.ui.widgets.uninstaller import AppUninstaller
from nova.ui.widgets.event_viewer import SystemEventViewer
from nova.ui.datetime_settings import DateTimeSettings
from nova.ui.accessibility import AccessibilityCenter
from nova.hotkeys import HotkeyRebinderWidget
from nova.pajama.dojo import PajamaDojoWidget
from nova.pajama.canvas import PajamaCanvasWindow
from nova.auto_repair import AutoRepairMatrix
"""
Master Desktop Environment & Window Manager for NOVA OS.
Coordinates the cybernetic desktop canvas, floating window frames, taskbar,
and inter-application workflows.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QApplication, QLabel, QMenu, QInputDialog, QFileDialog
)
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, QThread, Signal, QEvent
from PySide6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QBrush, QPixmap,
    QKeySequence, QShortcut
)

from nova.config import APP_NAME, APP_VERSION, APP_SUBTITLE, DEFAULT_ACCENT, BROWSER_HOMEPAGE, DEFAULT_WALLPAPER_PATH
from nova.system_monitor import SystemMonitor
from nova.ollama_client import OllamaClient
from nova.database import init_db, get_setting, set_setting, get_due_reminders, complete_reminder, purge_transient_cache
from nova.ui.theme import get_stylesheet, setup_nova_palette
from nova.ui.taskbar import Taskbar
from nova.ui.window_frame import WindowFrame
from nova.ui.notifications import NotificationManager
from nova.clipboard_manager import ClipboardListener, ClipboardHistoryDialog
from nova.ui.widgets.universal_search import UniversalSearchDialog
from nova.ui.widgets.quick_settings import QuickSettingsFlyout
from nova.voice import VoiceEngine, VoiceOrchestrator, BrowserVoiceContext
from nova.ui.voice_ui import NovaVoiceHUD
from nova.ui.desktop_icons import DesktopIconManager
from nova.workspace_manager import WorkspaceManager
from nova.ui.desktop_widgets import ClockCalendarWidget, SystemMetersWidget, StickyNoteWidget

from nova.ui.widgets.dashboard import DashboardWidget
from nova.ui.widgets.chat import ChatWidget
from nova.ui.widgets.notes import NotesWidget
from nova.ui.widgets.terminal import TerminalWidget
from nova.ui.widgets.file_viewer import FileViewerWidget
from nova.ui.widgets.settings import SettingsWidget
from nova.ui.widgets.browser import BrowserWidget
from nova.ui.widgets.workspace import WorkspaceWidget
from nova.ui.widgets.backup_restore import BackupRestoreWidget
from nova.ui.widgets.document_search import DocumentSearchWidget
from nova.ui.widgets.ai_memory import AIMemoryWidget
from nova.ui.widgets.automation_studio import AutomationStudioWidget
from nova.ui.widgets.calendar_widget import CalendarRemindersWidget
from nova.ui.widgets.privacy_center import PrivacyCenterWidget
from nova.ui.widgets.nova_search import NovaSearchWidget
from nova.ui.widgets.agent_hub import AgentHubWidget
from nova.ui.widgets.research_cockpit import ResearchCockpitWidget
from nova.ui.widgets.vault_widget import VaultWidget
from nova.ui.widgets.pajama_studio import PajamaStudioWidget
from nova.ui.widgets.windows_app_hub import WindowsAppHubWidget
from nova.ui.widgets.quick_launcher import QuickLauncherWidget
from nova.ui.widgets.cyber_wallpaper import CyberWallpaperWidget
from nova.wake_word import WakeWordWorker
from nova.sound_fx import play_sound
from nova.memory_optimizer import get_memory_optimizer


class AIStatusWorker(QThread):
    """
    Background worker that checks Ollama AI daemon connectivity asynchronously
    to prevent blocking the Qt main UI thread.
    Uses cooperative cancellation to avoid unsafe thread termination.
    """
    status_checked = Signal(bool, str)

    def __init__(self, ollama_client, parent=None):
        super().__init__(parent)
        self.ollama = ollama_client
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return
            ok = self.ollama.check_connection()
            if self._is_cancelled:
                return
            model = ""
            if ok:
                models = self.ollama.get_available_models()
                if self._is_cancelled:
                    return
                if models:
                    model = models[0]
            self.status_checked.emit(ok, model)
        except Exception:
            if not self._is_cancelled:
                self.status_checked.emit(False, "")


class CyberDesktopHost(QWidget):
    """
    Host container for the NOVA OS workspace.
    Renders and caches the cybernetic wallpaper across the entire application window,
    with cyber corner brackets and status watermark.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CyberDesktopHost")
        self._cached_pixmap = None
        self._wallpaper_path = None
        self._raw_wallpaper_pixmap = None
        self.load_wallpaper()

    def load_wallpaper(self):
        saved_path = get_setting("custom_wallpaper", str(DEFAULT_WALLPAPER_PATH))
        p = Path(saved_path)
        if not p.exists() or "mountain" in str(p):
            p = DEFAULT_WALLPAPER_PATH
        if p.exists():
            self._wallpaper_path = str(p)
            self._raw_wallpaper_pixmap = QPixmap(str(p))
            if self._raw_wallpaper_pixmap.isNull():
                self._raw_wallpaper_pixmap = None
        else:
            self._raw_wallpaper_pixmap = None
        self._cached_pixmap = None

    def set_wallpaper(self, path: str) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        pix = QPixmap(str(p))
        if pix.isNull():
            return False
        self._wallpaper_path = str(p)
        self._raw_wallpaper_pixmap = pix
        set_setting("custom_wallpaper", str(p))
        self._cached_pixmap = None
        self.update()
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_cached_pixmap()

    def _update_cached_pixmap(self):
        w = max(1, self.width())
        h = max(1, self.height())
        pixmap = QPixmap(w, h)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self._raw_wallpaper_pixmap and not self._raw_wallpaper_pixmap.isNull():
            scaled = self._raw_wallpaper_pixmap.scaled(
                w, h,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            sx = max(0, (scaled.width() - w) // 2)
            sy = max(0, (scaled.height() - h) // 2)
            painter.drawPixmap(0, 0, scaled, sx, sy, w, h)
            # Subtle cybernetic darkening overlay for UI readability
            painter.fillRect(0, 0, w, h, QColor(4, 6, 12, 60))
        else:
            # Fallback procedural cyber background
            bg_gradient = QRadialGradient(w / 2, h / 2, max(w, h) * 0.7)
            bg_gradient.setColorAt(0.0, QColor("#0d1222"))
            bg_gradient.setColorAt(0.6, QColor("#080b14"))
            bg_gradient.setColorAt(1.0, QColor("#04060a"))
            painter.fillRect(0, 0, w, h, bg_gradient)

            pen = QPen(QColor(0, 240, 255, 14))
            pen.setWidth(1)
            painter.setPen(pen)
            grid_size = 45
            for x in range(0, w, grid_size):
                painter.drawLine(x, 0, x, h)
            for y in range(0, h, grid_size):
                painter.drawLine(0, y, w, y)

        # Neon cyber corner brackets matching reference image
        accent_pen = QPen(QColor(0, 240, 255, 100))
        accent_pen.setWidth(2)
        painter.setPen(accent_pen)
        # Top-left
        painter.drawLine(14, 14, 50, 14)
        painter.drawLine(14, 14, 14, 50)
        # Top-right
        painter.drawLine(w - 50, 14, w - 14, 14)
        painter.drawLine(w - 14, 14, w - 14, 50)
        # Bottom-left
        painter.drawLine(14, h - 50, 14, h - 14)
        painter.drawLine(14, h - 14, 50, h - 14)
        # Bottom-right
        painter.drawLine(w - 50, h - 14, w - 14, h - 14)
        painter.drawLine(w - 14, h - 50, w - 14, h - 14)

        # Subtle trial watermark
        watermark_pen = QPen(QColor(255, 255, 255, 30))
        painter.setPen(watermark_pen)
        painter.drawText(
            QRect(w - 420, h - 24, 400, 18),
            Qt.AlignRight | Qt.AlignVCenter,
            "NOVA OS • PERSONALIZED SPACE DESKTOP • SAFE ON WINDOWS"
        )
        painter.end()
        self._cached_pixmap = pixmap

    def paintEvent(self, event):
        if self._cached_pixmap is None or self._cached_pixmap.size() != self.size():
            self._update_cached_pixmap()
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cached_pixmap)


class DesktopIconLayer(QWidget):
    """
    Dedicated background layer widget that hosts desktop shortcut icons.
    Permanently kept at the bottom of the DesktopCanvas z-stack (below all window frames).
    Forwards unhandled clicks and context menu events to the parent DesktopCanvas.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesktopIconLayer")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    def contextMenuEvent(self, event):
        parent = self.parentWidget()
        if parent:
            parent.contextMenuEvent(event)
        else:
            super().contextMenuEvent(event)


class DesktopCanvas(QWidget):
    """
    Interactive desktop workspace.
    Maintains a strict visual stacking order:
    1. CyberWallpaperWidget (bottom background effect)
    2. DesktopIconLayer (icons and desktop widgets)
    3. WindowFrames (application windows)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesktopCanvas")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        # Background effect layer (must be at the absolute bottom)
        self.cyber_wallpaper = CyberWallpaperWidget(self)

        # Dedicated Icon Layer widget hosting shortcuts and desktop widgets
        self.icon_layer = DesktopIconLayer(self)
        self.icon_manager = DesktopIconManager(self.icon_layer)

        # Bottom Workspace Switcher Card Deck
        self.workspace_bar = WorkspaceThumbnailBar(self.icon_layer)
        self.workspace_bar.show()

        self._ensure_stacking_order()

    def _ensure_stacking_order(self):
        """Enforces that cyber_wallpaper is strictly underneath icon_layer and windows."""
        if hasattr(self, "icon_layer"):
            self.icon_layer.lower()
        if hasattr(self, "cyber_wallpaper"):
            self.cyber_wallpaper.lower()
            if hasattr(self, "icon_layer"):
                self.cyber_wallpaper.stackUnder(self.icon_layer)

    def set_effects_mode(self, mode: str):
        if hasattr(self, "cyber_wallpaper"):
            self.cyber_wallpaper.set_effects_mode(mode)

    def pause_wallpaper(self):
        if hasattr(self, "cyber_wallpaper"):
            self.cyber_wallpaper.pause()

    def resume_wallpaper(self):
        if hasattr(self, "cyber_wallpaper"):
            self.cyber_wallpaper.resume()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if hasattr(self, "cyber_wallpaper"):
            self.cyber_wallpaper.setGeometry(0, 0, w, h)
        if hasattr(self, "icon_layer"):
            self.icon_layer.setGeometry(0, 0, w, h)
        if hasattr(self, "workspace_bar") and self.workspace_bar:
            self.workspace_bar.move(25, max(80, h - 85))
        self._ensure_stacking_order()
        if hasattr(self, "clock_widget") and self.clock_widget:
            x = max(100, w - 280)
            self.clock_widget.move(x, 30)
            if hasattr(self, "meters_widget") and self.meters_widget:
                self.meters_widget.move(x, 255)
            if hasattr(self, "sticky_widget") and self.sticky_widget:
                self.sticky_widget.move(x, 400)

    def setup_icons(self, on_activate_callback):
        self.icon_manager.render_icons(on_activate_callback)
        self._ensure_stacking_order()

    def setup_widgets(self, system_monitor):
        """Instantiates Desktop Widgets (Clock, Calendar, Meters, Sticky Note) on icon layer."""
        w = max(900, self.width())
        x = max(100, w - 280)
        self.clock_widget = ClockCalendarWidget(parent=self.icon_layer)
        self.clock_widget.move(x, 30)
        self.clock_widget.show()

        self.meters_widget = SystemMetersWidget(system_monitor, parent=self.icon_layer)
        self.meters_widget.move(x, 255)
        self.meters_widget.show()

        self.sticky_widget = StickyNoteWidget(parent=self.icon_layer)
        self.sticky_widget.move(x, 400)
        self.sticky_widget.show()
        self.desktop_widgets = [self.clock_widget, self.meters_widget, self.sticky_widget]
        self._ensure_stacking_order()

    def update_telemetry(self, cpu_pct: float):
        if hasattr(self, "cyber_wallpaper"):
            self.cyber_wallpaper.set_telemetry(cpu_pct)
        self._ensure_stacking_order()

    def contextMenuEvent(self, event):
        """Shows the Cyber Desktop context menu when right-clicking the empty desktop."""
        main_win = self.window()
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0c1424;
                color: #e2e8f0;
                border: 1px solid #00f0ff;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0052cc;
                color: #ffffff;
            }
        """)

        act_search = menu.addAction("🔍 Universal Search (Ctrl+Space)")
        act_quick = menu.addAction("⚡ Quick Settings (Ctrl+Shift+S)")
        act_clip = menu.addAction("📋 Clipboard History (Ctrl+Shift+V)")
        menu.addSeparator()
        act_grid = menu.addAction("🔲 Auto-Arrange Desktop Icons")
        act_restore_layout = menu.addAction("↺ Restore Default Desktop Layout")
        act_add_app = menu.addAction("➕ Add Application Shortcut...")
        act_add_file = menu.addAction("📁 Add File/Folder Shortcut...")
        menu.addSeparator()
        act_wallpaper = menu.addAction("🖼 Change Wallpaper...")
        act_refresh = menu.addAction("🔄 Refresh Desktop")

        chosen = menu.exec(event.globalPos())
        if chosen == act_search and hasattr(main_win, "toggle_search"):
            main_win.toggle_search()
        elif chosen == act_quick and hasattr(main_win, "toggle_quick_settings"):
            main_win.toggle_quick_settings()
        elif chosen == act_clip and hasattr(main_win, "toggle_clipboard_history"):
            main_win.toggle_clipboard_history()
        elif chosen == act_grid:
            self.icon_manager.arrange_grid()
        elif chosen == act_restore_layout:
            callback = getattr(main_win, "_on_desktop_icon_activated", None)
            self.icon_manager.restore_default_layout(callback)
            if hasattr(main_win, "notify"):
                main_win.notify("DESKTOP RESTORED", "Default layout and shortcuts restored.", "info", 3000)
        elif chosen == act_add_app and hasattr(main_win, "_on_desktop_icon_activated"):
            self._prompt_add_app_shortcut(main_win)
        elif chosen == act_add_file and hasattr(main_win, "_on_desktop_icon_activated"):
            self._prompt_add_file_shortcut(main_win)
        elif chosen == act_wallpaper:
            self._prompt_change_wallpaper(main_win)
        elif chosen == act_refresh:
            if hasattr(main_win, "host_container"):
                main_win.host_container.load_wallpaper()
                main_win.host_container.update()
            if hasattr(main_win, "_on_desktop_icon_activated"):
                self.icon_manager.render_icons(main_win._on_desktop_icon_activated)
            self.update()

    def _prompt_add_app_shortcut(self, main_win):
        apps = [
            ("NOVA Cyber Browser", "🌐", "app", "browser"),
            ("NOVA AI Assistant", "🤖", "app", "chat"),
            ("Telemetry Dashboard", "📊", "app", "dashboard"),
            ("NovaPad Knowledge", "📝", "app", "notes"),
            ("Cyber Safe Terminal", "💻", "app", "terminal"),
            ("Sandbox File Vault", "📁", "app", "files"),
            ("Control Center", "⚙", "app", "settings"),
            ("NOVA Voice Assistant", "🎙", "app", "voice"),
            ("Clipboard History", "📋", "app", "clipboard"),
        ]
        items = [f"{icon} {name}" for name, icon, _, _ in apps]
        item, ok = QInputDialog.getItem(
            self, "Add Application Shortcut", "Select an application to place on the desktop:", items, 0, False
        )
        if ok and item:
            idx = items.index(item)
            name, icon, s_type, target = apps[idx]
            self.icon_manager.add_shortcut(
                name, icon, s_type, target, main_win._on_desktop_icon_activated
            )
            if hasattr(main_win, "notify"):
                main_win.notify("SHORTCUT CREATED", f"Added '{name}' to desktop.", "info", 3000)

    def _prompt_add_file_shortcut(self, main_win):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File or Script for Desktop Shortcut", str(Path.home())
        )
        if file_path:
            p = Path(file_path)
            icon = "📁" if p.is_dir() else "📄"
            self.icon_manager.add_shortcut(
                p.name, icon, "file", str(p), main_win._on_desktop_icon_activated
            )
            if hasattr(main_win, "notify"):
                main_win.notify("FILE SHORTCUT ADDED", f"Linked '{p.name}' on desktop.", "info", 3000)

    def _prompt_change_wallpaper(self, main_win):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Wallpaper Image", str(Path.home()), "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            if hasattr(main_win, "host_container") and main_win.host_container.set_wallpaper(file_path):
                if hasattr(main_win, "notify"):
                    main_win.notify("WALLPAPER UPDATED", "Applied new cyber wallpaper.", "info", 3000)
            else:
                QMessageBox.warning(self, "Invalid Image", "Could not load the selected wallpaper image file.")

class MainWindow(QMainWindow):
    def __init__(self, initial_url: str = None):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE}")
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)

        # Initialize Core Services
        init_db()
        self.system_monitor = SystemMonitor()
        saved_host = get_setting("ollama_host", "http://127.0.0.1:11434")
        self.ollama_client = OllamaClient(host=saved_host)

        # Workspace Manager (Feature 3)
        self.workspace_manager = WorkspaceManager(self)
        self.workspace_manager.workspace_switched.connect(self._on_workspace_switched)

        # Open Window Tracking: win_id -> (WindowFrame, is_visible)
        self.windows = {}
        self._stagger_offset = 0

        self.setup_ui()
        self.quick_launcher = QuickLauncherWidget(self)
        self.quick_launcher.action_triggered.connect(self._on_quick_launcher_action)
        self.setup_shortcuts()
        self.desktop_canvas.setup_icons(self._on_desktop_icon_activated)
        self.desktop_canvas.setup_widgets(self.system_monitor)
        self.apply_theme(get_setting("accent_color", DEFAULT_ACCENT))

        # Check due reminders periodically (every 10 seconds)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_reminders)
        self.reminder_timer.start(10000)

        # Asynchronous AI Status Poller (every 20s, initial check at 400ms)
        self._ai_worker = None
        self.ai_status_timer = QTimer(self)
        self.ai_status_timer.timeout.connect(self._refresh_ai_status)
        self.ai_status_timer.start(20000)
        QTimer.singleShot(400, self._refresh_ai_status)

        # Auto-ensure Ollama background daemon is running (non-blocking)
        from nova.ollama_client import start_ollama_in_background
        start_ollama_in_background(self.ollama_client.host, on_ready_callback=self._refresh_ai_status)

        # Welcome notification toast
        QTimer.singleShot(1200, lambda: self.notify(
            "NOVA OS Online",
            "Hardware Profile: Intel Core i3 • 4 GB RAM Mode Active\nPress Ctrl+Space for Universal Search",
            "info",
            5000
        ))

        if initial_url:
            self.launch_app("browser", initial_pos=(120, 30), initial_size=(900, 680), url=initial_url)
            self.launch_app("dashboard", initial_pos=(140, 50), initial_size=(560, 480))
        else:
            # Launch default desktop windows (positioned to avoid covering the desktop icon strip on the left)
            self.launch_app("dashboard", initial_pos=(120, 30), initial_size=(620, 530))
            self.launch_app("chat", initial_pos=(770, 30), initial_size=(560, 680))

    def setup_ui(self):
        # Central Cyber Host Container (renders full-bleed wallpaper)
        self.host_container = CyberDesktopHost(self)
        self.setCentralWidget(self.host_container)
        main_layout = QVBoxLayout(self.host_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main Shell Horizontal Layout: Left Sidebar + Desktop Canvas + Right Dashboard
        body_container = QWidget(self.host_container)
        body_container.setObjectName("BodyContainer")
        body_container.setStyleSheet("background: transparent;")
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        self.left_sidebar = LeftNavSidebar(body_container)
        self.left_sidebar.app_requested.connect(self._on_left_nav_requested)
        body_layout.addWidget(self.left_sidebar)

        # 2. Central Desktop Canvas
        self.desktop_canvas = DesktopCanvas(body_container)
        self.desktop_canvas.workspace_bar.workspace_changed.connect(self._on_workspace_bar_changed)
        body_layout.addWidget(self.desktop_canvas, stretch=1)

        # 3. Right System Dashboard
        self.right_dashboard = RightSystemDashboard(self.system_monitor, body_container)
        self.right_dashboard.settings_requested.connect(lambda: self.launch_app("settings"))
        self.right_dashboard.dark_mode_toggled.connect(self._toggle_dark_mode)
        self.right_dashboard.focus_mode_toggled.connect(self._toggle_focus_mode)
        self.right_dashboard.lock_requested.connect(self.lock_screen)
        body_layout.addWidget(self.right_dashboard)

        main_layout.addWidget(body_container, stretch=1)

        # Notification Stack Manager (HUD overlay)
        self.notification_manager = NotificationManager(self.desktop_canvas)

        # Clipboard Listener and History HUD
        self.clipboard_listener = ClipboardListener(self)
        self.clipboard_dialog = ClipboardHistoryDialog(self)
        self.clipboard_dialog.snippet_selected.connect(self._on_clipboard_snippet_selected)

        # Alt+Tab App Switcher HUD
        self.alt_tab_hud = AltTabHUD(self.desktop_canvas)
        self.alt_tab_hud.window_selected.connect(self._on_alt_tab_selected)

        # Cyber Lock Screen (Win+L / Ctrl+L)
        self.lock_screen_overlay = CyberLockScreen(self)
        self.lock_screen_overlay.unlocked.connect(lambda: play_sound("success"))

        # Removable Media / USB Manager
        self.usb_manager = USBManager(self)
        self.usb_manager.drive_inserted.connect(self._on_usb_drive_inserted)

        # Self-Healing RAM & Watchdog Timer
        self.auto_repair_timer = QTimer(self)
        self.auto_repair_timer.timeout.connect(self._run_auto_repair_check)
        self.auto_repair_timer.start(60000)

        # Universal Search HUD Dialog
        self.search_dialog = UniversalSearchDialog(self)
        self.search_dialog.app_launch_requested.connect(self._on_search_launch_requested)
        self.search_dialog.notification_requested.connect(self.notify)

        # Quick Settings Flyout Panel
        self.quick_settings = QuickSettingsFlyout(self)
        self.quick_settings.theme_changed.connect(self.apply_theme)
        self.quick_settings.performance_mode_changed.connect(self.apply_performance_mode)
        self.quick_settings.open_full_settings.connect(lambda: self.launch_app("settings"))
        self.quick_settings.notification_requested.connect(self.notify)

        # Siri-like NOVA Voice Engine, Orchestrator & HUD
        self.voice_engine = VoiceEngine(parent=self)
        self.browser_voice_context = BrowserVoiceContext(parent=self)
        self.voice_orchestrator = VoiceOrchestrator(self.ollama_client, parent=self)
        self.voice_orchestrator.register_action_handler("launch_app", self.launch_app)
        self.voice_orchestrator.register_action_handler("purge_cache", purge_transient_cache)
        self.voice_hud = NovaVoiceHUD(
            self.voice_engine,
            self.voice_orchestrator,
            browser_context=self.browser_voice_context,
            parent=self
        )

        # Floating Bottom Dock Container
        dock_container = QWidget(self.host_container)
        dock_container.setObjectName("DockContainer")
        dock_container.setStyleSheet("background: transparent;")
        dock_layout = QHBoxLayout(dock_container)
        dock_layout.setContentsMargins(20, 0, 20, 10)
        dock_layout.setSpacing(0)

        # Bottom Floating Taskbar / Dock
        self.taskbar = Taskbar(dock_container)
        self.taskbar.app_launch_requested.connect(self.launch_app)
        self.taskbar.window_toggle_requested.connect(self.toggle_window)
        self.taskbar.universal_search_requested.connect(self.toggle_search)
        self.taskbar.quick_settings_requested.connect(self.toggle_quick_settings)
        self.taskbar.clipboard_requested.connect(self.toggle_clipboard_history)
        self.taskbar.voice_assistant_requested.connect(self.toggle_voice_assistant)
        self.taskbar.exit_requested.connect(self.confirm_exit)
        dock_layout.addWidget(self.taskbar)
        main_layout.addWidget(dock_container)


    def _on_left_nav_requested(self, key: str):
        if key == "home":
            for app_id, item in list(self.windows.items()):
                frame = item[0] if isinstance(item, tuple) else item
                if frame.isMinimized():
                    frame.showNormal()
                frame.raise_()
        elif key == "workspace":
            self.launch_app("workspace")
        elif key == "dashboard":
            self.launch_app("dashboard")
        elif key in ("browser", "files", "chat", "terminal", "settings", "voice", "winapps"):
            self.launch_app(key)
        else:
            self.launch_app(key)

    def switch_desktop(self, index: int):
        """Switches virtual desktop / workspace profile by index (1: General, 2: Research, 3: Coding, 4: Personal)."""
        profiles = ["study", "research", "coding", "personal"]
        idx = max(0, min(len(profiles) - 1, index - 1))
        target_id = profiles[idx]
        self.workspace_manager.switch_to(target_id)

    def _on_workspace_bar_changed(self, key: str):
        ws_map = {
            "desktop": "study",
            "general": "study",
            "research": "research",
            "dev": "coding",
            "coding": "coding",
            "personal": "personal"
        }
        if key in ws_map:
            target_id = ws_map[key]
            self.workspace_manager.switch_to(target_id)
        elif key in ("new", "manage"):
            self.notify("WORKSPACES", "Opening Workspace Profiles Manager...", "info", 2000)
            self.launch_app("workspace")

    def _toggle_dark_mode(self):
        self.notify("THEME MODE", "NOVA Cyber Dark Palette Active.", "info", 2000)

    def _toggle_focus_mode(self):
        self.notify("FOCUS MODE", "Zen Focus Mode Engaged. Distractions Minimized.", "info", 2500)

    def _on_desktop_icon_activated(self, data: dict):
        if hasattr(self.desktop_canvas, "icon_manager") and self.desktop_canvas.icon_manager:
            self.desktop_canvas.icon_manager.launch_target(data, self.launch_app)

    def setup_shortcuts(self):
        # Alt+Tab App Switcher Carousel
        QShortcut(QKeySequence("Alt+Tab"), self, self.toggle_alt_tab)

        # Cyber Lock Screen (Ctrl+L)
        QShortcut(QKeySequence("Ctrl+L"), self, self.lock_screen)

        # Quick Hotkeys: Terminal (Ctrl+Alt+T) & Pajama (Ctrl+Shift+P)
        QShortcut(QKeySequence("Ctrl+Alt+T"), self, lambda: self.launch_app("terminal"))
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, lambda: self.launch_app("pajama"))

        # Siri-Style NOVA Voice Assistant (Ctrl+Shift+Space or F4)
        QShortcut(QKeySequence("Ctrl+Shift+Space"), self, self.toggle_voice_assistant)
        QShortcut(QKeySequence("F4"), self, self.toggle_voice_assistant)

        # Escape key to restore maximized windows or dismiss immersive views
        QShortcut(QKeySequence("Escape"), self, self._handle_escape_key)

        # Universal Search HUD (Spotlight)
        QShortcut(QKeySequence("Ctrl+Space"), self, self.toggle_search)
        QShortcut(QKeySequence("Alt+Space"), self, self.toggle_quick_launcher)
        QShortcut(QKeySequence("F3"), self, self.toggle_quick_launcher)

        # Clipboard History HUD
        QShortcut(QKeySequence("Ctrl+Shift+V"), self, self.toggle_clipboard_history)

        # Quick Settings Flyout
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.toggle_quick_settings)

        # Fullscreen Toggle
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)

        # Safe Exit
        QShortcut(QKeySequence("Ctrl+Q"), self, self.confirm_exit)

        # Fast App Switching (Ctrl+1 to Ctrl+7)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.launch_app("dashboard"))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.launch_app("chat"))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.launch_app("browser"))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.launch_app("notes"))
        QShortcut(QKeySequence("Ctrl+5"), self, lambda: self.launch_app("terminal"))
        QShortcut(QKeySequence("Ctrl+6"), self, lambda: self.launch_app("files"))
        QShortcut(QKeySequence("Ctrl+7"), self, lambda: self.launch_app("settings"))

        # Command Palette Fast Directives (Panel 2: Alt+B, Alt+F, Alt+W, Alt+S, Alt+D, Alt+C)
        QShortcut(QKeySequence("Alt+B"), self, lambda: self.launch_app("browser"))
        QShortcut(QKeySequence("Alt+F"), self, lambda: self.launch_app("files"))
        QShortcut(QKeySequence("Alt+W"), self, lambda: self.launch_app("workspace"))
        QShortcut(QKeySequence("Alt+S"), self, lambda: self.launch_app("settings"))
        QShortcut(QKeySequence("Alt+D"), self, lambda: self.launch_app("docsearch"))
        QShortcut(QKeySequence("Alt+C"), self, self.toggle_search_calc)

    def _handle_escape_key(self):
        """Restores any active maximized window to normal floating geometry or dismisses active overlays."""
        if hasattr(self, "search_dialog") and self.search_dialog.isVisible():
            self.search_dialog.hide()
            return
        if hasattr(self, "quick_settings") and self.quick_settings.isVisible():
            self.quick_settings.hide()
            return
        if hasattr(self, "clipboard_dialog") and self.clipboard_dialog.isVisible():
            self.clipboard_dialog.hide()
            return
        # Find active / topmost maximized window and restore it
        for app_id, item in list(self.windows.items()):
            frame = item[0] if isinstance(item, tuple) else item
            if frame.isVisible() and getattr(frame, "is_maximized", False):
                frame.restore_window()
                return

    def _on_accessibility_changed(self, data: dict):
        """Applies live accessibility settings across the shell."""
        if "effects_mode" in data:
            self.apply_desktop_effects_mode(data["effects_mode"])
        if "reduced_motion" in data and data["reduced_motion"]:
            self.apply_desktop_effects_mode("clean")
            self.notify("ACCESSIBILITY", "Reduced motion engaged. Animated effects paused.", "info", 3000)

    def apply_theme(self, accent_name: str):
        qss = get_stylesheet(accent_name)
        app = QApplication.instance()
        if app:
            setup_nova_palette(app)
            app.setStyleSheet(qss)
        self.setStyleSheet(qss)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                if hasattr(self, "desktop_canvas"):
                    self.desktop_canvas.pause_wallpaper()
                if hasattr(self, "right_dashboard") and hasattr(self.right_dashboard, "set_update_interval"):
                    self.right_dashboard.set_update_interval(5000)
                try:
                    from nova.memory_optimizer import get_memory_optimizer
                    get_memory_optimizer().trim_current_process()
                except Exception:
                    pass
            else:
                if hasattr(self, "desktop_canvas"):
                    self.desktop_canvas.resume_wallpaper()
                if hasattr(self, "right_dashboard") and hasattr(self.right_dashboard, "set_update_interval"):
                    self.right_dashboard.set_update_interval(1000)
        super().changeEvent(event)

    def apply_desktop_effects_mode(self, mode: str):
        """Propagates visual effects mode ('Clean', 'Balanced', 'Cyber') to desktop wallpaper."""
        if hasattr(self, "desktop_canvas"):
            self.desktop_canvas.set_effects_mode(mode)

    def apply_performance_mode(self, mode: str):
        """Propagates performance mode to active widgets and throttles polling."""
        if "dashboard" in self.windows:
            frame, _ = self.windows["dashboard"]
            if hasattr(frame, "content_widget") and hasattr(frame.content_widget, "set_performance_mode"):
                frame.content_widget.set_performance_mode(mode)

        if "Low Resource" in mode or "Battery" in mode:
            if hasattr(self, "right_dashboard") and hasattr(self.right_dashboard, "set_update_interval"):
                self.right_dashboard.set_update_interval(3000)
            self.apply_desktop_effects_mode("Clean")
            try:
                from nova.memory_optimizer import get_memory_optimizer
                get_memory_optimizer().trim_current_process()
            except Exception:
                pass
        elif "High Fidelity" in mode:
            if hasattr(self, "right_dashboard") and hasattr(self.right_dashboard, "set_update_interval"):
                self.right_dashboard.set_update_interval(500)
            self.apply_desktop_effects_mode("Cyber")
        else:
            # Balanced (Default)
            if hasattr(self, "right_dashboard") and hasattr(self.right_dashboard, "set_update_interval"):
                self.right_dashboard.set_update_interval(1000)
            self.apply_desktop_effects_mode("Balanced")

    def launch_app(self, app_id: str, initial_pos=None, initial_size=None, url: str = None):
        """Creates or restores an application window on the desktop canvas."""
        # Non-window utility integrations
        if app_id == "voice":
            self.toggle_voice_assistant()
            return
        if app_id == "clipboard":
            self.toggle_clipboard_history()
            return
        if app_id == "reminders":
            self.launch_app("notes")
            if "notes" in self.windows:
                frame, _ = self.windows["notes"]
                if hasattr(frame, "content_widget") and hasattr(frame.content_widget, "tabs"):
                    frame.content_widget.tabs.setCurrentIndex(1)
            return

        # If already instantiated, toggle visible and bring to front
        if app_id in self.windows:
            frame, _ = self.windows[app_id]
            frame.show()
            frame.raise_()
            self.windows[app_id] = (frame, True)
            self.taskbar.update_active_windows(self.windows)
            if app_id == "browser" and url and hasattr(frame, "content_widget"):
                frame.content_widget.navigate_to(url)
            return

        # Instantiate Widget
        if app_id == "browser":
            target_url = url or BROWSER_HOMEPAGE
            widget = BrowserWidget(initial_url=target_url, ollama_client=self.ollama_client)
            widget.voice_requested.connect(self.toggle_voice_assistant)
            if hasattr(self, "browser_voice_context"):
                self.browser_voice_context.set_browser_widget(widget)
            title = "NOVA CYBER BROWSER"
            icon = "🌐"
            default_size = (920, 680)
        elif app_id == "dashboard":
            widget = DashboardWidget(self.system_monitor)
            perf_mode = get_setting("performance_mode", "Balanced")
            widget.set_performance_mode(perf_mode)
            title = "SYSTEM TELEMETRY"
            icon = "📊"
            default_size = (620, 520)
        elif app_id == "chat":
            widget = ChatWidget(self.ollama_client, voice_engine=self.voice_engine)
            title = "NOVA AI TRANSMISSION"
            icon = "🤖"
            default_size = (560, 680)
        elif app_id == "notes":
            widget = NotesWidget(self.ollama_client)
            title = "NOVAPAD KNOWLEDGE"
            icon = "📝"
            default_size = (680, 500)
        elif app_id == "terminal":
            widget = TerminalWidget()
            title = "SECURE CYBER TERMINAL"
            icon = "💻"
            default_size = (640, 460)
        elif app_id == "files":
            widget = FileViewerWidget()
            title = "SANDBOX FILE VAULT"
            icon = "📁"
            default_size = (620, 480)
        elif app_id == "settings":
            widget = SettingsWidget(self.ollama_client)
            widget.theme_changed.connect(self.apply_theme)
            widget.performance_mode_changed.connect(self.apply_performance_mode)
            if hasattr(widget, "effects_mode_changed"):
                widget.effects_mode_changed.connect(self.apply_desktop_effects_mode)
            title = "CONTROL CENTER"
            icon = "⚙"
            default_size = (640, 600)
        elif app_id == "workspace":
            widget = WorkspaceWidget(self.workspace_manager)
            widget.workspace_applied.connect(self._on_workspace_applied)
            widget.app_launch_requested.connect(self.launch_app)
            title = "WORKSPACE MANAGER"
            icon = "🗂"
            default_size = (720, 500)
        elif app_id == "backup":
            widget = BackupRestoreWidget()
            widget.notification_requested.connect(self.notify)
            title = "BACKUP & RESTORE"
            icon = "📦"
            default_size = (700, 520)
        elif app_id == "docsearch":
            widget = DocumentSearchWidget()
            widget.file_open_requested.connect(self.launch_app)
            title = "AI DOCUMENT SEARCH"
            icon = "🔍"
            default_size = (680, 520)
        elif app_id == "memory":
            widget = AIMemoryWidget()
            widget.notification_requested.connect(self.notify)
            title = "NOVA MEMORY"
            icon = "🧠"
            default_size = (640, 480)
        elif app_id == "automation":
            widget = AutomationStudioWidget()
            widget.action_requested.connect(self._on_automation_action)
            widget.notification_requested.connect(self.notify)
            title = "AUTOMATION STUDIO"
            icon = "⚡"
            default_size = (680, 500)
        elif app_id == "calendar":
            widget = CalendarRemindersWidget()
            widget.notification_requested.connect(self.notify)
            title = "CALENDAR & REMINDERS"
            icon = "📅"
            default_size = (720, 520)
        elif app_id == "privacy":
            widget = PrivacyCenterWidget()
            widget.notification_requested.connect(self.notify)
            title = "PRIVACY CENTER"
            icon = "🛡️"
            default_size = (680, 520)
        elif app_id == "novasearch":
            widget = NovaSearchWidget()
            widget.search_activated.connect(self._on_search_portal_action)
            title = "NOVA SEARCH PORTAL"
            icon = "❖"
            default_size = (720, 540)
        elif app_id == "agent":
            widget = AgentHubWidget(self.ollama_client)
            title = "NOVA AUTONOMOUS AGENT"
            icon = "🚀"
            default_size = (800, 580)
        elif app_id in ("research", "research_agent"):
            widget = ResearchCockpitWidget()
            title = "NOVA RESEARCH AGENT"
            icon = "🌐"
            default_size = (840, 600)
        elif app_id == "vault":
            widget = VaultWidget(self.ollama_client)
            title = "NOVA DOCUMENT VAULT"
            icon = "📚"
            default_size = (760, 540)
        elif app_id in ("pajama", "pajama_studio", "studio", "pajama-studio"):
            widget = PajamaStudioWidget(self.ollama_client)
            title = "PAJAMA SCRIPT STUDIO"
            icon = "⚡"
            default_size = (920, 640)
        elif app_id in ("winapps", "windows_apps", "apps", "app_hub"):
            widget = WindowsAppHubWidget(parent=self)
            if hasattr(self, "icon_manager"):
                widget.desktop_updated.connect(lambda: self.icon_manager.load_shortcuts() and self.icon_manager.render_icons(self.launch_app))
            title = "WINDOWS APPLICATION BRIDGE"
            icon = "🪟"
            default_size = (860, 600)
        elif app_id in ("recycle_bin", "trash"):
            widget = RecycleBinWidget()
            title = "RECYCLE BIN & RECOVERY"
            icon = "🗑️"
            default_size = (780, 520)
        elif app_id in ("startup", "startup_manager"):
            widget = StartupManager()
            title = "STARTUP APPLICATIONS"
            icon = "🚀"
            default_size = (720, 480)
        elif app_id in ("uninstaller", "app_uninstaller"):
            widget = AppUninstaller()
            title = "APP UNINSTALLER & CLEANER"
            icon = "📦"
            default_size = (740, 500)
        elif app_id in ("events", "event_viewer", "diagnostics"):
            widget = SystemEventViewer()
            title = "SYSTEM EVENT VIEWER"
            icon = "📜"
            default_size = (840, 560)
        elif app_id in ("datetime", "time_settings"):
            widget = DateTimeSettings()
            title = "DATE & TIME SETTINGS"
            icon = "🕒"
            default_size = (620, 420)
        elif app_id in ("accessibility", "a11y"):
            widget = AccessibilityCenter()
            widget.accessibility_changed.connect(self._on_accessibility_changed)
            title = "ACCESSIBILITY & USABILITY"
            icon = "♿"
            default_size = (680, 460)
        elif app_id in ("hotkeys", "shortcuts"):
            widget = HotkeyRebinderWidget()
            title = "HOTKEY REBINDER"
            icon = "⌨️"
            default_size = (680, 480)
        elif app_id in ("dojo", "pajama_dojo"):
            widget = PajamaDojoWidget()
            title = "PAJAMA DOJO ACADEMY"
            icon = "🥋"
            default_size = (860, 580)
        elif app_id in ("canvas", "2d_canvas", "games"):
            widget = PajamaCanvasWindow()
            title = "PAJAMA 2D GAME CANVAS"
            icon = "🎮"
            default_size = (540, 440)
        elif app_id in ("shell_tools", "wsl", "services", "dns"):
            widget = WindowsShellToolsWidget()
            title = "WINDOWS SUBSYSTEMS & SHELL TOOLS"
            icon = "🪟"
            default_size = (860, 600)
        elif app_id in ("media_hub", "cyberamp", "player", "music"):
            widget = MediaHubWidget()
            title = "CYBER MULTIMEDIA & AUDIO STUDIO"
            icon = "🎬"
            default_size = (840, 580)
        elif app_id in ("arcade_hub", "arcade", "retro_games", "invaders"):
            widget = ArcadeHubWidget()
            title = "NOVA RETRO ARCADE HUB"
            icon = "👾"
            default_size = (860, 600)
        elif app_id in ("network_tools", "companion", "lan", "speedtest"):
            widget = NetworkToolsWidget()
            title = "NETWORK TOOLS & COMPANION"
            icon = "🌐"
            default_size = (840, 560)
        elif app_id in ("security_fortress", "totp", "shredder", "panic"):
            widget = SecurityFortressWidget()
            title = "SECURITY FORTRESS & FORENSICS"
            icon = "🛡️"
            default_size = (760, 540)
        elif app_id in ("productivity_hub", "kanban", "pomodoro", "habits"):
            widget = ProductivityHubWidget()
            title = "PRODUCTIVITY & KANBAN MATRIX"
            icon = "📋"
            default_size = (860, 600)
        elif app_id in ("os_matrix", "kernel_matrix", "matrix", "cockpit"):
            widget = OSMatrixCockpitWidget()
            title = "100,000 KERNEL ARCHITECTURE MATRIX"
            icon = "🧬"
            default_size = (980, 650)
        elif app_id == "launcher":
            self.toggle_quick_launcher()
            return
        else:
            return

        # Create Window Frame container
        frame = WindowFrame(title, widget, icon_text=icon, parent=self.desktop_canvas)
        frame.window_closed.connect(lambda f, a=app_id: self.on_window_closed(a))
        frame.window_minimized.connect(lambda f, a=app_id: self.on_window_minimized(a))
        frame.window_focused.connect(lambda f, a=app_id: self.on_window_focused(a))

        # Position and size
        size = initial_size or default_size
        pw = max(900, self.desktop_canvas.width())
        ph = max(600, self.desktop_canvas.height())
        cx = max(20, (pw - size[0]) // 2)
        cy = max(20, (ph - size[1]) // 2)
        frame.normal_geometry = QRect(cx, cy, size[0], size[1])

        if initial_pos:
            frame.resize(size[0], size[1])
            frame.move(initial_pos[0], initial_pos[1])
            frame.is_maximized = False
            frame.max_btn.setText("▢")
        else:
            # Maximized by default as specified
            frame.maximize_window()

        frame.show()
        frame.raise_()
        self.windows[app_id] = (frame, True)
        self.taskbar.update_active_windows(self.windows)

    def toggle_window(self, app_id: str):
        if app_id not in self.windows:
            return
        frame, is_visible = self.windows[app_id]
        if is_visible:
            # If active and on top, minimize; otherwise raise
            frame.hide()
            self.windows[app_id] = (frame, False)
        else:
            frame.show()
            frame.raise_()
            self.windows[app_id] = (frame, True)
        self.taskbar.update_active_windows(self.windows)

    def toggle_alt_tab(self):
        open_wins = []
        for app_id, (frame, is_visible) in self.windows.items():
            open_wins.append((frame.title_text, frame.icon_text, frame))
        if open_wins:
            self.alt_tab_hud.show_switcher(open_wins, parent_widget=self)

    def _on_alt_tab_selected(self, frame_obj):
        if frame_obj:
            frame_obj.show()
            frame_obj.raise_()

    def lock_screen(self):
        play_sound("alert")
        self.lock_screen_overlay.lock()

    def _on_usb_drive_inserted(self, drive_info: dict):
        mount = drive_info.get("mountpoint", "Removable")
        gb = drive_info.get("total_gb", 0)
        self.notify("USB Drive Detected", f"Volume {mount} ({gb} GB) mounted. Open in File Vault?", "info", 6000)
        play_sound("chime")

    def _run_auto_repair_check(self):
        report = AutoRepairMatrix.run_diagnostic_check()
        if report.get("repairs"):
            repairs_str = "; ".join(report["repairs"])
            self.notify("Auto-Repair Matrix", f"Memory optimized: {repairs_str}", "info", 4000)

    def on_window_closed(self, app_id: str):
        if app_id in self.windows:
            frame, _ = self.windows[app_id]
            self.windows[app_id] = (frame, False)
            self.taskbar.update_active_windows(self.windows)

    def on_window_minimized(self, app_id: str):
        if app_id in self.windows:
            frame, _ = self.windows[app_id]
            self.windows[app_id] = (frame, False)
            self.taskbar.update_active_windows(self.windows)

    def on_window_focused(self, app_id: str):
        if app_id in self.windows:
            frame, _ = self.windows[app_id]
            frame.raise_()
            self.windows[app_id] = (frame, True)
            self.taskbar.update_active_windows(self.windows)

    def toggle_quick_launcher(self):
        """Toggles the floating Raycast-style command palette."""
        if hasattr(self, "quick_launcher"):
            if self.quick_launcher.isVisible():
                self.quick_launcher.close()
            else:
                self.quick_launcher.show_centered()

    def _on_quick_launcher_action(self, action_type: str, payload: dict):
        """Handles actions dispatched from the Quick Launcher."""
        if action_type == "open_browser":
            self.launch_app("browser")
        elif action_type == "ask_ai":
            self.launch_app("chat")
        elif action_type == "ask_ai_query":
            self.launch_app("chat")
            if "chat" in self.windows:
                frame, _ = self.windows["chat"]
                if hasattr(frame, "content_widget"):
                    frame.content_widget.input_edit.setText(payload.get("value", ""))
        elif action_type == "open_notes":
            self.launch_app("notes")
        elif action_type == "open_note_id":
            self.launch_app("notes")
        elif action_type == "open_terminal":
            self.launch_app("terminal")
        elif action_type == "run_terminal":
            self.launch_app("terminal")
            if "terminal" in self.windows:
                frame, _ = self.windows["terminal"]
                if hasattr(frame, "content_widget"):
                    frame.content_widget.execute_input(payload.get("value", ""))
        elif action_type == "open_settings":
            self.launch_app("settings")
        elif action_type in ["open_vault", "open_vault_query"]:
            self.launch_app("vault")
            if action_type == "open_vault_query" and "vault" in self.windows:
                frame, _ = self.windows["vault"]
                if hasattr(frame, "content_widget"):
                    frame.content_widget.question_input.setText(payload.get("value", ""))
                    frame.content_widget.on_ask_vault()
        elif action_type == "notification":
            self.notify(payload.get("title", "Action"), payload.get("msg", ""), "info")

    def toggle_search(self):
        """Toggles the Spotlight-style Universal Search HUD."""
        if self.search_dialog.isVisible():
            self.search_dialog.hide()
        else:
            self.search_dialog.show_centered(self)

    def toggle_search_calc(self):
        """Opens Command Palette focused on calculator expression (Alt+C)."""
        self.toggle_search()
        if hasattr(self, "search_dialog") and self.search_dialog:
            self.search_dialog.input_edit.setText("25 * 40")
            self.search_dialog.input_edit.selectAll()

    def _on_workspace_applied(self, ws: dict):
        """Applies theme and notifies user when a workspace profile is activated."""
        theme = ws.get("theme", "Cosmic Cyan")
        self.apply_theme(theme)
        # Synchronize thumbnail bar active indicator
        card_map = {"study": "desktop", "research": "research", "coding": "dev", "personal": "personal"}
        target_card = card_map.get(ws.get("id"), "desktop")
        if hasattr(self, "desktop_canvas") and hasattr(self.desktop_canvas, "workspace_bar"):
            self.desktop_canvas.workspace_bar.set_active_workspace(target_card)
        self.notify("WORKSPACE PROFILE ACTIVATED", f"Switched to {ws['name']}\nFocus: {ws.get('description', '')}", "info", 3500)

    def _on_workspace_switched(self, ws: dict):
        self._on_workspace_applied(ws)

    def _on_automation_action(self, action_name: str, params: dict):
        """Dispatches sequential actions from Automation Studio."""
        if action_name == "launch_app":
            self.launch_app(params.get("app_id", "browser"))
        elif action_name == "switch_workspace":
            self.workspace_manager.switch_to(params.get("workspace_id", "study"))
        elif action_name == "purge_cache":
            from nova.database import purge_transient_cache
            purge_transient_cache()
            self.notify("AUTOMATION", "Purged transient system cache.", "info")
        elif action_name == "start_timer":
            self.launch_app("calendar")

    def _on_search_portal_action(self, action_type: str, payload: dict):
        """Dispatches results from independent NOVA Search portal."""
        if action_type == "web":
            self.launch_app("browser", url=payload.get("url"))
        elif action_type == "launch_app":
            self.launch_app(payload.get("app_id", "browser"))

    def toggle_quick_settings(self):
        """Toggles the Quick Settings flyout panel."""
        if self.quick_settings.isVisible():
            self.quick_settings.hide()
        else:
            self.quick_settings.refresh_status()
            btn = self.taskbar.quick_settings_btn
            g_pos = btn.mapToGlobal(QPoint(0, 0))
            x = max(10, g_pos.x() - self.quick_settings.width() + btn.width())
            y = max(10, g_pos.y() - self.quick_settings.height() - 8)
            self.quick_settings.move(x, y)
            self.quick_settings.show()
            self.quick_settings.raise_()

    def toggle_clipboard_history(self):
        """Toggles the Clipboard History HUD popup."""
        if self.clipboard_dialog.isVisible():
            self.clipboard_dialog.hide()
        else:
            self.clipboard_dialog.load_history()
            btn = self.taskbar.clip_btn
            g_pos = btn.mapToGlobal(QPoint(0, 0))
            x = max(10, g_pos.x() - 100)
            y = max(10, g_pos.y() - self.clipboard_dialog.height() - 8)
            self.clipboard_dialog.move(x, y)
            self.clipboard_dialog.show()
            self.clipboard_dialog.raise_()

    def toggle_voice_assistant(self):
        """Toggles the Siri-style NOVA Voice HUD assistant."""
        if hasattr(self, "voice_hud"):
            if self.voice_hud.isVisible():
                self.voice_hud.stop_current_action()
                self.voice_hud.hide()
            else:
                # Sync browser widget if browser window is currently open
                if "browser" in self.windows:
                    frame, _ = self.windows["browser"]
                    if hasattr(frame, "content_widget") and hasattr(self, "browser_voice_context"):
                        self.browser_voice_context.set_browser_widget(frame.content_widget)
                self.voice_hud.show_centered(self)

    def toggle_fullscreen(self):
        """Toggles between fullscreen and normal desktop trial mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def notify(self, title: str, message: str, level: str = "info", duration_ms: int = 4000):
        """Dispatches a non-blocking cybernetic toast notification to the canvas HUD."""
        if hasattr(self, "notification_manager") and self.notification_manager:
            return self.notification_manager.notify(title, message, level=level, duration_ms=duration_ms)

    def _on_clipboard_snippet_selected(self, text: str):
        clip = QApplication.clipboard()
        if clip:
            clip.setText(text)
        preview = (text[:45] + "..") if len(text) > 45 else text
        self.notify("CLIPBOARD READY", f"Loaded into clipboard:\n{preview}", "info", 2500)

    def _on_search_launch_requested(self, app_id: str, params: dict):
        if app_id == "browser" and "url" in params:
            self.launch_app("browser", url=params["url"])
        else:
            self.launch_app(app_id)

    def _check_reminders(self):
        try:
            due = get_due_reminders()
            for r in due:
                priority = r.get("priority", "NORMAL")
                content = r.get("content", "Reminder")
                self.notify(f"🔔 DUE REMINDER [{priority}]", content, "reminder", 8000)
                complete_reminder(r["id"])
        except Exception:
            pass

    def _refresh_ai_status(self):
        """Dispatches an asynchronous check of Ollama AI service status."""
        if self._ai_worker is not None and self._ai_worker.isRunning():
            return
        if hasattr(self, "taskbar") and self.taskbar:
            self.taskbar.set_ai_status(False, "", checking=True)
        self._ai_worker = AIStatusWorker(self.ollama_client, self)
        self._ai_worker.status_checked.connect(self._on_ai_status_ready)
        self._ai_worker.start()

    def _on_ai_status_ready(self, is_online: bool, model_name: str):
        """Updates the taskbar indicator and adapts polling backoff."""
        if hasattr(self, "taskbar") and self.taskbar:
            self.taskbar.set_ai_status(is_online, model_name, checking=False)
        # Adaptive backoff: poll less frequently when offline (60s) to save CPU/battery
        if hasattr(self, "ai_status_timer") and self.ai_status_timer.isActive():
            new_interval = 30000 if is_online else 60000
            if self.ai_status_timer.interval() != new_interval:
                self.ai_status_timer.setInterval(new_interval)

    def _cleanup_on_close(self):
        """Stops background threads and releases resources on shutdown without unsafe terminate()."""
        if hasattr(self, "reminder_timer") and self.reminder_timer.isActive():
            self.reminder_timer.stop()

        if hasattr(self, "ai_status_timer") and self.ai_status_timer.isActive():
            self.ai_status_timer.stop()

        if hasattr(self, "auto_repair_timer") and self.auto_repair_timer.isActive():
            self.auto_repair_timer.stop()

        if hasattr(self, "right_dashboard") and hasattr(self.right_dashboard, "cleanup"):
            self.right_dashboard.cleanup()

        if hasattr(self, "_ai_worker") and self._ai_worker is not None:
            if self._ai_worker.isRunning():
                self._ai_worker.cancel()
                self._ai_worker.quit()
                self._ai_worker.wait(1500)

        if hasattr(self, "voice_hud"):
            self.voice_hud.stop_current_action()
            self.voice_hud.hide()

        if hasattr(self, "_wake_worker") and self._wake_worker:
            self._wake_worker.cancel()
            self._wake_worker.wait(500)
        if hasattr(self, "quick_launcher") and self.quick_launcher:
            self.quick_launcher.close()

        if hasattr(self, "voice_engine"):
            self.voice_engine.cleanup()

        for app_id, (frame, _) in list(self.windows.items()):
            if hasattr(frame, "content_widget"):
                cw = frame.content_widget
                if hasattr(cw, "worker") and cw.worker:
                    try:
                        cw.worker.stop()
                    except Exception:
                        pass
                if hasattr(cw, "cleanup"):
                    cw.cleanup()

        # Final working set flush on shutdown
        try:
            from nova.memory_optimizer import get_memory_optimizer
            get_memory_optimizer().trim_current_process()
        except Exception:
            pass

    def confirm_exit(self):
        reply = QMessageBox.question(
            self,
            "Close NOVA OS",
            "Safely exit the NOVA OS AI Trial session and return to Windows?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._cleanup_on_close()
            QApplication.quit()

    def closeEvent(self, event):
        # Allow non-spontaneous (programmatic) close without blocking modal
        if not event.spontaneous():
            self._cleanup_on_close()
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Close NOVA OS",
            "Exit NOVA OS AI Trial session?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._cleanup_on_close()
            event.accept()
        else:
            event.ignore()
