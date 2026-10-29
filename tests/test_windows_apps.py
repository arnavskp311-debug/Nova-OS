"""
WINDOWS APPLICATION BRIDGE & SUBSYSTEM TEST SUITE.
Validates Windows application discovery, process tracking, Pajama integration,
Agent tools, and WindowsAppHubWidget instantiation.
"""

import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ["QT_QPA_PLATFORM"] = "offscreen" 

from nova.windows_apps import get_windows_app_manager, WindowsAppInfo
from nova.pajama.runtime import execute_pajama
from nova.agent_engine import AgentEngine


class TestWindowsAppDiscovery(unittest.TestCase):
    """Verifies that Windows applications are discovered and categorized."""

    def setUp(self):
        self.mgr = get_windows_app_manager()

    def test_discover_standard_tools(self):
        apps = self.mgr.discover_apps()
        self.assertGreater(len(apps), 10, "Should discover more than 10 Windows apps")

        names = {a.name.lower() for a in apps}
        self.assertIn("calculator", names)
        self.assertIn("notepad", names)
        self.assertIn("file explorer", names)
        self.assertIn("task manager", names)

    def test_process_monitoring(self):
        # Explorer is virtually always running on Windows
        is_explorer = self.mgr.is_process_running("explorer")
        self.assertTrue(is_explorer, "explorer.exe should be active")

        # Python is running this test
        is_python = self.mgr.is_process_running("python")
        self.assertTrue(is_python, "python process should be active")

    def test_list_active_processes(self):
        procs = self.mgr.list_active_processes(limit=10)
        self.assertTrue(len(procs) > 0)
        first = procs[0]
        self.assertIn("pid", first)
        self.assertIn("name", first)
        self.assertIn("memory_mb", first)
        self.assertGreater(first["memory_mb"], 0)


class TestPajamaWindowsIntegration(unittest.TestCase):
    """Verifies that Pajama scripts can check and control Windows applications."""

    def test_pajama_running_check(self):
        script = (
            'if running "python":\n'
            '    say "Python confirmed running"\n'
            'otherwise:\n'
            '    say "Not running"\n'
        )
        out = execute_pajama(script)
        self.assertIn("Python confirmed running", out)

    def test_pajama_windows_statements_parse(self):
        from nova.pajama.parser import parse_pajama, WindowsAppActionStmt
        ast = parse_pajama('launch "notepad"\nclose "calc"\nopen "C:\\\\doc.txt"\n')
        self.assertEqual(len(ast.statements), 3)
        self.assertIsInstance(ast.statements[0], WindowsAppActionStmt)
        self.assertEqual(ast.statements[0].verb, "launch")
        self.assertEqual(ast.statements[1].verb, "close")
        self.assertEqual(ast.statements[2].verb, "open")


class TestWindowsAppHubWidget(unittest.TestCase):
    """Verifies that the Windows App Hub UI widget initializes without error."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            cls.app = QApplication(sys.argv + ["-platform", "offscreen"])
        else:
            cls.app = QApplication.instance()

    def test_widget_creation(self):
        from nova.ui.widgets.windows_app_hub import WindowsAppHubWidget
        widget = WindowsAppHubWidget()
        self.assertIsNotNone(widget.tabs)
        self.assertEqual(widget.tabs.count(), 2)
        self.assertIsNotNone(widget.search_input)
        self.assertIsNotNone(widget.proc_table)
        widget.cleanup()


class TestAgentEngineWindowsTools(unittest.TestCase):
    """Verifies that the autonomous agent can list and launch Windows apps."""

    def test_agent_tools_registered(self):
        engine = AgentEngine()
        self.assertIn("windows_app_launch", engine.tools)
        self.assertIn("windows_process_list", engine.tools)
        self.assertIn("windows_process_kill", engine.tools)

        # Execute process list tool
        res = engine.execute_tool("windows_process_list", {"limit": 5})
        self.assertTrue(res.get("success"))
        self.assertIn("memory_mb", str(res.get("result")))


if __name__ == "__main__":
    unittest.main()
