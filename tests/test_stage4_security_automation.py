"""
Targeted Verification Suite for Stage 4: Security and Automation.
Verifies download scanning, hash computation, binary magic byte inspection,
executable quarantine & release lifecycle, privacy center controls,
online database backup/restore integrity, and emergency panic wipe.
"""

import sys
import unittest
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication

from nova.config import DATA_DIR, BACKUPS_DIR
from nova.database import (
    log_command, get_recent_command_logs, clear_command_logs,
    create_database_backup, check_database_integrity, get_database_backup_list,
    get_setting, set_setting
)
from nova.download_security import DownloadValidator
from nova.security_fortress import EmergencyPanicWipe
from nova.safety import RiskLevel, analyze_command
from nova.ui.widgets.approval_dialog import CommandApprovalDialog

# Ensure headless Qt application
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestStage4SecurityAutomation(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="nova_sec_test_"))

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_download_validator_safe_and_prohibited_inspection(self):
        """Verifies inspection of safe files vs dangerous executables and scripts."""
        # 1. Safe text file
        safe_file = self.test_dir / "research_notes.txt"
        safe_file.write_text("Safe research content", encoding="utf-8")
        res_safe = DownloadValidator.inspect_file(safe_file)
        self.assertTrue(res_safe["is_safe"])
        self.assertFalse(res_safe["is_executable"])
        self.assertEqual(len(res_safe["sha256"]), 64)

        # 2. Prohibited executable extension (.exe)
        exe_file = self.test_dir / "untrusted_payload.exe"
        exe_file.write_bytes(b"dummy executable bytes")
        res_exe = DownloadValidator.inspect_file(exe_file)
        self.assertFalse(res_exe["is_safe"])
        self.assertTrue(res_exe["is_executable"])
        self.assertIn(".exe", res_exe["reason"])

        # 3. Prohibited script extension (.bat)
        bat_file = self.test_dir / "run_script.bat"
        bat_file.write_text("@echo off\ncalc.exe", encoding="utf-8")
        res_bat = DownloadValidator.inspect_file(bat_file)
        self.assertFalse(res_bat["is_safe"])
        self.assertTrue(res_bat["is_executable"])

    def test_02_download_validator_magic_bytes_masked_detection(self):
        """Verifies detection of Windows MZ binary disguised under an innocent extension (.png)."""
        masked_file = self.test_dir / "innocent_photo.png"
        # MZ header followed by dummy bytes
        masked_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff")
        res = DownloadValidator.inspect_file(masked_file)

        self.assertFalse(res["is_safe"])
        self.assertTrue(res["is_executable"])
        self.assertTrue(res.get("is_masked", False))
        self.assertIn("MZ binary disguised", res["reason"])

    def test_03_quarantine_and_release_lifecycle(self):
        """Verifies end-to-end file quarantine, manifest logging, and 1-click release."""
        dangerous_file = self.test_dir / "malicious_tool.ps1"
        dangerous_file.write_text("Write-Host 'Risky payload'", encoding="utf-8")

        # 1. Quarantine file
        quarantine_id = DownloadValidator.quarantine_file(
            dangerous_file,
            source_url="http://example.com/malicious_tool.ps1",
            reason="Executable script detected"
        )
        self.assertIsNotNone(quarantine_id)
        # Original file should be removed from original location
        self.assertFalse(dangerous_file.exists())

        # 2. Verify manifest record
        manifest = DownloadValidator.get_manifest()
        entry = next((item for item in manifest if item["id"] == quarantine_id), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["original_name"], "malicious_tool.ps1")
        self.assertEqual(entry["status"], "QUARANTINED")

        # 3. Release file to safe destination
        release_dest = self.test_dir / "released_downloads"
        ok, msg = DownloadValidator.release_file(quarantine_id, dest_dir=release_dest)
        self.assertTrue(ok)
        released_file = release_dest / "malicious_tool.ps1"
        self.assertTrue(released_file.exists())

        # 4. Verify removed from manifest
        manifest_after = DownloadValidator.get_manifest()
        self.assertIsNone(next((item for item in manifest_after if item["id"] == quarantine_id), None))

    def test_04_command_audit_logging_and_clear(self):
        """Verifies recording and purging of command execution security logs."""
        log_command("test_security_audit_cmd", "HIGH", "TEST_STATUS", output="Test output", approved=True)
        logs = get_recent_command_logs(limit=10)
        self.assertTrue(any(l["command"] == "test_security_audit_cmd" for l in logs))

        # Clear audit logs
        cleared = clear_command_logs()
        self.assertGreaterEqual(cleared, 1)
        remaining = get_recent_command_logs(limit=10)
        self.assertEqual(len(remaining), 0)

    def test_05_online_database_backup_and_integrity(self):
        """Verifies SQLite online backup snapshot creation and integrity verification."""
        ok, msg, backup_path = create_database_backup()
        self.assertTrue(ok)
        self.assertIsNotNone(backup_path)
        self.assertTrue(backup_path.exists())
        self.assertGreater(backup_path.stat().st_size, 10240)  # > 10 KB

        # Check integrity of live DB
        int_ok, int_msg, ver = check_database_integrity()
        self.assertTrue(int_ok)
        self.assertGreaterEqual(ver, 1)

        # Check backup list
        backups = get_database_backup_list()
        self.assertGreater(len(backups), 0)

    def test_06_emergency_panic_wipe(self):
        """Verifies emergency panic wipe flushes memory and transient cache safely."""
        res = EmergencyPanicWipe.execute_panic()
        self.assertEqual(res["status"], "PANIC_DEFENSE_TRIGGERED")
        self.assertTrue(res["memory_flushed"])
        self.assertIn("timestamp", res)

    def test_07_privacy_settings_persistence(self):
        """Verifies that privacy toggles persist correctly in SQLite settings."""
        set_setting("auto_quarantine_enabled", True)
        set_setting("disable_telemetry", True)

        self.assertTrue(get_setting("auto_quarantine_enabled"))
        self.assertTrue(get_setting("disable_telemetry"))

        set_setting("auto_quarantine_enabled", False)
        self.assertFalse(get_setting("auto_quarantine_enabled"))
        # Reset back to True
        set_setting("auto_quarantine_enabled", True)


if __name__ == "__main__":
    unittest.main()
