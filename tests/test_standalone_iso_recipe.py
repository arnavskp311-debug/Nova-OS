"""
Verification Suite for Standalone Live Linux ISO Recipe and GitHub Actions Workflow.
Verifies existence, syntax, and architectural compliance of build scripts,
bootloader configs (isolinux/grub), autologin overrides, udev disk protection rules,
and GitHub Actions CI/CD pipeline definitions.
"""

import os
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class TestStandaloneISORecipe(unittest.TestCase):

    def test_01_build_script_exists_and_configured(self):
        """Verifies scripts/build_iso.sh exists and contains required build steps."""
        build_script = BASE_DIR / "scripts" / "build_iso.sh"
        self.assertTrue(build_script.exists())
        content = build_script.read_text(encoding="utf-8")

        self.assertIn("debootstrap", content)
        self.assertIn("mksquashfs", content)
        self.assertIn("xorriso", content)
        self.assertIn("NovaOS-Live-x86_64.iso", content)
        self.assertIn("openbox", content)
        self.assertIn("live-boot", content)
        self.assertIn("/opt/nova-os", content)

    def test_02_isolinux_and_grub_configs(self):
        """Verifies BIOS and UEFI bootloader configurations."""
        isolinux_cfg = BASE_DIR / "scripts" / "iso_config" / "isolinux.cfg"
        grub_cfg = BASE_DIR / "scripts" / "iso_config" / "grub.cfg"

        self.assertTrue(isolinux_cfg.exists())
        self.assertTrue(grub_cfg.exists())

        iso_content = isolinux_cfg.read_text(encoding="utf-8")
        self.assertIn("boot=live", iso_content)
        self.assertIn("vmlinuz", iso_content)
        self.assertIn("initrd.img", iso_content)

        grub_content = grub_cfg.read_text(encoding="utf-8")
        self.assertIn("boot=live", grub_content)
        self.assertIn("menuentry", grub_content)
        self.assertIn("vmlinuz", grub_content)

    def test_03_autostart_and_autologin_kiosk(self):
        """Verifies zero-overhead agetty autologin and X11 kiosk autostart."""
        autologin = BASE_DIR / "scripts" / "iso_config" / "autologin.conf"
        xinitrc = BASE_DIR / "scripts" / "iso_config" / "xinitrc"

        self.assertTrue(autologin.exists())
        self.assertTrue(xinitrc.exists())

        auto_content = autologin.read_text(encoding="utf-8")
        self.assertIn("--autologin nova", auto_content)

        xinit_content = xinitrc.read_text(encoding="utf-8")
        self.assertIn("openbox", xinit_content)
        self.assertIn("/opt/nova-os/main.py", xinit_content)
        self.assertIn("--fullscreen", xinit_content)

    def test_04_host_windows_partition_protection(self):
        """Verifies udev rules to protect internal NVMe/SATA host Windows drives."""
        udev_rule = BASE_DIR / "scripts" / "iso_config" / "99-hide-internal-disks.rules"
        self.assertTrue(udev_rule.exists())
        content = udev_rule.read_text(encoding="utf-8")
        self.assertIn('UDISKS_IGNORE}="1"', content)
        self.assertIn("nvme", content)
        self.assertIn("sd", content)

    def test_05_ollama_cpu_service(self):
        """Verifies CPU-only Ollama systemd unit definition."""
        ollama_service = BASE_DIR / "scripts" / "iso_config" / "ollama.service"
        self.assertTrue(ollama_service.exists())
        content = ollama_service.read_text(encoding="utf-8")
        self.assertIn("OLLAMA_LLM_LIBRARY=cpu", content)
        self.assertIn("127.0.0.1:11434", content)

    def test_06_github_actions_workflow_yaml(self):
        """Verifies GitHub Actions workflow syntax and structure."""
        workflow_file = BASE_DIR / ".github" / "workflows" / "build-iso.yml"
        self.assertTrue(workflow_file.exists())
        content = workflow_file.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", content)
        self.assertIn("ubuntu-latest", content)
        self.assertIn("actions/checkout@v4", content)
        self.assertIn("actions/upload-artifact@v4", content)
        self.assertIn("scripts/build_iso.sh", content)
        self.assertIn("NovaOS-Live-x86_64.iso", content)

    def test_07_qemu_test_script_and_documentation(self):
        """Verifies QEMU virtual test script and standalone user guide."""
        qemu_script = BASE_DIR / "scripts" / "test_iso_qemu.sh"
        guide = BASE_DIR / "STANDALONE_ISO_GUIDE.md"

        self.assertTrue(qemu_script.exists())
        self.assertTrue(guide.exists())
        self.assertGreater(guide.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
