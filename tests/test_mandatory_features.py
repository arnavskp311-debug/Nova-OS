"""
Comprehensive Verification Suite for NOVA OS Mandatory Features:
1. Master Volume & Audio Endpoint Controls (nova.hardware)
2. Wi-Fi Scanner & Connection Management (nova.hardware)
3. Battery Telemetry & Power Profiles (nova.hardware)
4. Display Brightness & Night Light Filter (nova.hardware & tray_flyouts)
5. Bluetooth Peripheral Hub (nova.hardware)
6. Aero Edge Window Snapping (nova.ui.window_snapping)
7. Virtual Desktops / Multi-Workspace Switcher (nova.ui.virtual_desktops)
8. Visual Alt+Tab App Switcher HUD (nova.ui.alt_tab_hud)
9. Borderless Kiosk & Window Management
10. Cyber Lock Screen (nova.ui.lock_screen)
11. Multi-User Accounts & Profile Isolation (nova.users)
12. Visual UAC Elevation Prompt (nova.ui.uac_dialog)
13. Encrypted Credential Vault (nova.credentials)
14. Recycle Bin & 1-Click Restore (nova.recycle_bin)
15. USB Drive Auto-Detection & Safe Eject (nova.usb_manager)
16. Default App Associations (nova.file_associations)
17. Global File Search Indexer (nova.file_indexer)
18. Startup Applications Manager (nova.ui.widgets.startup_manager)
19. App Uninstaller Wizard (nova.ui.widgets.uninstaller)
20. System Event Viewer (nova.ui.widgets.event_viewer)
21. System Restore Points & Rollback (nova.snapshots)
22. NTP Date, Time & Timezone Settings (nova.ui.datetime_settings)
23. Keyboard Layout Switcher Pill (nova.ui.keyboard_switcher)
24. Accessibility Center (nova.ui.accessibility)
25. Customizable Global Hotkey Rebinder (nova.hotkeys)
26. Pajama 2D Game Canvas (nova.pajama.canvas)
27. Pajama Dojo Coding Academy (nova.pajama.dojo)
28. Pajama Vision Multimodal Analyzer (nova.pajama.vision)
29. Self-Healing Watchdog Engine (nova.auto_repair)
"""

import sys
import os
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure Qt offscreen for headless environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QRect

app = QApplication.instance() or QApplication([])

class TestMandatoryOSFeatures(unittest.TestCase):

    # 1. Volume & Audio Endpoint Controls
    def test_audio_controller(self):
        from nova.hardware import AudioController
        AudioController.set_master_volume(85)
        vol = AudioController.get_master_volume()
        self.assertEqual(vol, 85)

        is_mute = AudioController.toggle_mute()
        self.assertTrue(is_mute)
        is_mute_again = AudioController.toggle_mute()
        self.assertFalse(is_mute_again)

        endpoints = AudioController.get_audio_endpoints()
        self.assertTrue(len(endpoints) >= 1)

    # 2. Wi-Fi Scanner & Connection
    def test_wifi_controller(self):
        from nova.hardware import WifiController
        info = WifiController.get_current_connection()
        self.assertIn("ssid", info)
        self.assertIn("ip_address", info)

        networks = WifiController.scan_networks()
        self.assertTrue(len(networks) >= 1)
        self.assertIn("ssid", networks[0])

    # 3. Battery Telemetry & Power Profiles
    def test_battery_controller(self):
        from nova.hardware import BatteryController
        bat = BatteryController.get_battery_info()
        self.assertIn("percent", bat)
        self.assertIn("power_plugged", bat)

        ok = BatteryController.set_power_profile("balanced")
        self.assertTrue(ok)

    # 4. Display Brightness & Night Light Filter
    def test_display_controller(self):
        from nova.hardware import DisplayController
        DisplayController.set_brightness(75)
        self.assertEqual(DisplayController.get_brightness(), 75)

        active = DisplayController.toggle_night_light(True)
        self.assertTrue(active)
        self.assertTrue(DisplayController.is_night_light_active())
        inactive = DisplayController.toggle_night_light(False)
        self.assertFalse(inactive)

    # 5. Bluetooth Peripheral Hub
    def test_bluetooth_controller(self):
        from nova.hardware import BluetoothController
        devs = BluetoothController.get_devices()
        self.assertTrue(isinstance(devs, list))

    # 6. Aero Edge Window Snapping
    def test_window_snapping(self):
        from nova.ui.window_snapping import WindowSnapper, SnapZone
        parent_rect = QRect(0, 0, 1920, 1080)

        # Left snap
        left_win = QRect(5, 200, 800, 600)
        zone_left = WindowSnapper.detect_snap_zone(left_win, parent_rect)
        self.assertEqual(zone_left, SnapZone.LEFT)
        geom_left = WindowSnapper.get_snap_geometry(zone_left, parent_rect)
        self.assertEqual(geom_left.width(), 960)

        # Top maximize snap
        top_win = QRect(400, 5, 800, 600)
        zone_max = WindowSnapper.detect_snap_zone(top_win, parent_rect)
        self.assertEqual(zone_max, SnapZone.MAXIMIZE)
        geom_max = WindowSnapper.get_snap_geometry(zone_max, parent_rect)
        self.assertEqual(geom_max.width(), 1920)

    # 7. Virtual Desktops
    def test_virtual_desktops(self):
        from nova.ui.virtual_desktops import VirtualDesktopManager, VirtualDesktopPillWidget
        mgr = VirtualDesktopManager(count=3)
        self.assertEqual(mgr.current_desktop, 1)

        win_a = QWidget()
        win_b = QWidget()
        mgr.add_window(win_a, 1)
        mgr.add_window(win_b, 2)

        to_hide, to_show = mgr.switch_desktop(2)
        self.assertEqual(mgr.current_desktop, 2)
        self.assertIn(win_a, to_hide)
        self.assertIn(win_b, to_show)

        pill_widget = VirtualDesktopPillWidget(mgr)
        self.assertIsNotNone(pill_widget)

    # 8. Visual Alt+Tab App Switcher HUD
    def test_alt_tab_hud(self):
        from nova.ui.alt_tab_hud import AltTabHUD
        hud = AltTabHUD()
        dummy_windows = [
            ("Terminal", "💻", QWidget()),
            ("Browser", "🌐", QWidget()),
            ("NovaPad", "📝", QWidget())
        ]
        hud.show_switcher(dummy_windows)
        self.assertEqual(len(hud.cards), 3)
        hud.cycle_next()
        self.assertEqual(hud.selected_index, 2)
        hud.cycle_prev()
        self.assertEqual(hud.selected_index, 1)
        hud.hide()

    # 10. Cyber Lock Screen
    def test_cyber_lock_screen(self):
        from nova.ui.lock_screen import CyberLockScreen
        lock = CyberLockScreen()
        lock.clear_pin()
        lock.append_digit("0")
        lock.append_digit("0")
        lock.append_digit("0")
        lock.append_digit("0")
        self.assertEqual(lock.entered_pin, "0000")
        lock.verify_pin()
        self.assertEqual(lock.status_msg.text(), "ACCESS GRANTED")

    # 11. Multi-User Accounts
    def test_users_subsystem(self):
        from nova.users import UserManager
        users = UserManager.get_users()
        self.assertTrue(len(users) >= 2)
        cur = UserManager.get_current_user()
        self.assertIn("username", cur)
        home = UserManager.get_user_home_dir()
        self.assertTrue(home.exists())

    # 12. Visual UAC Elevation Prompt
    def test_uac_dialog(self):
        from nova.ui.uac_dialog import UACDialog
        uac = UACDialog("Privileged Disk Operation", "NOVA Storage Engine", "Format sandbox cache")
        self.assertIsNotNone(uac)
        self.assertEqual(uac.action_name, "Privileged Disk Operation")

    # 13. Secure Credential Vault
    def test_credential_vault(self):
        from nova.credentials import CredentialVault
        ok = CredentialVault.set_secret("OPENAI_API_KEY", "sk-mock-quantum-12345", master_pin="9999")
        self.assertTrue(ok)
        val = CredentialVault.get_secret("OPENAI_API_KEY", master_pin="9999")
        self.assertEqual(val, "sk-mock-quantum-12345")
        keys = CredentialVault.list_keys(master_pin="9999")
        self.assertIn("OPENAI_API_KEY", keys)
        del_ok = CredentialVault.delete_secret("OPENAI_API_KEY", master_pin="9999")
        self.assertTrue(del_ok)

    # 14. Recycle Bin & 1-Click Restore
    def test_recycle_bin(self):
        from nova.recycle_bin import RecycleBin, RecycleBinWidget
        test_file = BASE_DIR / "data" / "trash_test_probe.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Quarantine File Content", encoding="utf-8")

        item_id = RecycleBin.send_to_trash(str(test_file))
        self.assertIsNotNone(item_id)
        self.assertFalse(test_file.exists())

        restored = RecycleBin.restore(item_id)
        self.assertTrue(restored)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(encoding="utf-8"), "Quarantine File Content")

        # Cleanup
        if test_file.exists():
            test_file.unlink()

        widget = RecycleBinWidget()
        self.assertIsNotNone(widget)

    # 15. USB Manager
    def test_usb_manager(self):
        from nova.usb_manager import USBManager
        drives = USBManager.get_removable_drives()
        self.assertTrue(isinstance(drives, list))

    # 16. Default App Associations
    def test_file_associations(self):
        from nova.file_associations import FileAssociations
        app_pj = FileAssociations.get_app_for_file("script.pj")
        self.assertEqual(app_pj, "pajama")
        app_txt = FileAssociations.get_app_for_file("notes.txt")
        self.assertEqual(app_txt, "notes")
        app_html = FileAssociations.get_app_for_file("page.html")
        self.assertEqual(app_html, "browser")

    # 17. Global File Search Indexer
    def test_file_indexer(self):
        from nova.file_indexer import FileIndexer
        count = FileIndexer.build_index(search_root=BASE_DIR / "nova", max_files=100)
        self.assertTrue(count > 0)
        results = FileIndexer.search("config", limit=5)
        self.assertTrue(len(results) >= 1)

    # 18. Startup Applications Manager
    def test_startup_manager(self):
        from nova.ui.widgets.startup_manager import StartupManager
        widget = StartupManager()
        self.assertTrue(widget.table.rowCount() >= 1)

    # 19. App Uninstaller Wizard
    def test_uninstaller_widget(self):
        from nova.ui.widgets.uninstaller import AppUninstaller
        widget = AppUninstaller()
        self.assertIsNotNone(widget)

    # 20. System Event Viewer
    def test_event_viewer(self):
        from nova.ui.widgets.event_viewer import SystemEventViewer
        widget = SystemEventViewer()
        self.assertIsNotNone(widget)

    # 21. System Restore Points & Rollback
    def test_snapshots(self):
        from nova.snapshots import SnapshotManager
        snap_id = SnapshotManager.create_restore_point("Unit Test Checkpoint")
        self.assertIsNotNone(snap_id)
        points = SnapshotManager.list_restore_points()
        self.assertTrue(any(p["id"] == snap_id for p in points))
        del_ok = SnapshotManager.delete_restore_point(snap_id)
        self.assertTrue(del_ok)

    # 22. NTP Date, Time & Timezone Settings
    def test_datetime_settings(self):
        from nova.ui.datetime_settings import DateTimeSettings
        widget = DateTimeSettings()
        self.assertIsNotNone(widget)

    # 23. Keyboard Layout Switcher
    def test_keyboard_switcher(self):
        from nova.ui.keyboard_switcher import KeyboardSwitcherPill
        pill = KeyboardSwitcherPill()
        self.assertEqual(pill.text(), "ENG")
        pill.cycle_layout()
        self.assertEqual(pill.text(), "US")
        pill.cycle_layout()
        self.assertEqual(pill.text(), "INTL")

    # 24. Accessibility Center
    def test_accessibility_center(self):
        from nova.ui.accessibility import AccessibilityCenter
        widget = AccessibilityCenter()
        self.assertIsNotNone(widget)

    # 25. Customizable Global Hotkey Rebinder
    def test_hotkey_rebinder(self):
        from nova.hotkeys import HotkeyRegistry, HotkeyRebinderWidget
        hotkeys = HotkeyRegistry.get_hotkeys()
        self.assertIn("universal_search", hotkeys)
        self.assertEqual(hotkeys["universal_search"]["shortcut"], "Ctrl+Space")
        widget = HotkeyRebinderWidget()
        self.assertIsNotNone(widget)

    # 26. Pajama 2D Game Canvas
    def test_pajama_canvas(self):
        from nova.pajama.canvas import CyberCanvasWidget, PajamaCanvasWindow
        win = PajamaCanvasWindow()
        win.play_snake()
        self.assertEqual(win.canvas.game_mode, "snake")
        win.play_pong()
        self.assertEqual(win.canvas.game_mode, "pong")

    # 27. Pajama Dojo Coding Academy
    def test_pajama_dojo(self):
        from nova.pajama.dojo import PajamaDojoWidget, DOJO_CHALLENGES
        self.assertEqual(len(DOJO_CHALLENGES), 10)
        widget = PajamaDojoWidget()
        widget.on_level_selected(0)
        widget.evaluate_solution()
        self.assertIn("PASSED", widget.result_lbl.text())

    # 28. Pajama Vision Multimodal Analyzer
    def test_pajama_vision(self):
        from nova.pajama.vision import PajamaVision
        res = PajamaVision.analyze_image("non_existent_img.png")
        self.assertIn("not found", res.lower())

    # 29. Self-Healing Watchdog Engine
    def test_auto_repair_matrix(self):
        from nova.auto_repair import AutoRepairMatrix
        report = AutoRepairMatrix.run_diagnostic_check()
        self.assertIn("status", report)
        self.assertIn("ram_percent", report)


if __name__ == "__main__":
    unittest.main()
