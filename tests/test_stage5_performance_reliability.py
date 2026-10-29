"""
Targeted Verification Suite for Stage 5: Performance and Reliability.
Verifies memory trimming, working set reclamation, dynamic background polling
throttling, graceful teardown lifecycle, and low-RAM hardware optimizations.
"""

import os
import sys
import unittest
import psutil
from PySide6.QtWidgets import QApplication

from nova.memory_optimizer import MemoryOptimizer, get_memory_optimizer, flush_quantum_memory
from nova.hardware_optimizer import RAMCompressor, SSDHealthMonitor, CPUAffinityTuner
from nova.system_monitor import SystemMonitor
from nova.ui.main_window import MainWindow

# Ensure headless Qt application
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestStage5PerformanceReliability(unittest.TestCase):

    def test_01_working_set_memory_trimming(self):
        """Verifies physical working set trimming using Windows API."""
        opt = get_memory_optimizer()
        p = psutil.Process(os.getpid())
        rss_before_mb = p.memory_info().rss / (1024 * 1024)

        # Trigger working set trim
        ok, freed_mb = opt.trim_current_process()
        rss_after_mb = p.memory_info().rss / (1024 * 1024)

        self.assertTrue(ok)
        self.assertLessEqual(rss_after_mb, rss_before_mb + 2.0)
        # Verify status metrics
        status = opt.get_memory_status()
        self.assertIn("total_mb", status)
        self.assertIn("available_mb", status)
        self.assertIn("percent", status)

    def test_02_dynamic_telemetry_polling_throttling(self):
        """Verifies telemetry polling interval can be dynamically throttled to save CPU."""
        from nova.ui.right_dashboard import RightSystemDashboard

        monitor = SystemMonitor()
        dash = RightSystemDashboard(monitor)

        # Default interval: 1000 ms
        self.assertEqual(dash.timer.interval(), 1000)

        # Throttle for battery saver mode: 3000 ms
        dash.set_update_interval(3000)
        self.assertEqual(dash.timer.interval(), 3000)

        # Boost for high fidelity mode: 500 ms
        dash.set_update_interval(500)
        self.assertEqual(dash.timer.interval(), 500)

        # Cleanup
        dash.cleanup()
        self.assertFalse(dash.timer.isActive())

    def test_03_main_window_graceful_teardown(self):
        """Verifies MainWindow cleanly terminates all background timers and worker threads."""
        win = MainWindow()

        # Timers should be active initially
        self.assertTrue(win.reminder_timer.isActive())
        self.assertTrue(win.ai_status_timer.isActive())
        self.assertTrue(win.auto_repair_timer.isActive())
        self.assertTrue(win.right_dashboard.timer.isActive())

        # Perform cleanup
        win._cleanup_on_close()

        # Verify all timers stopped
        self.assertFalse(win.reminder_timer.isActive())
        self.assertFalse(win.ai_status_timer.isActive())
        self.assertFalse(win.auto_repair_timer.isActive())
        self.assertFalse(win.right_dashboard.timer.isActive())

        # Verify safe closure without exception
        win.close()
        app.processEvents()

    def test_04_performance_mode_throttling_propagation(self):
        """Verifies performance mode changes propagate and throttle background timers."""
        win = MainWindow()

        # 1. Low Resource / Battery Saver Mode
        win.apply_performance_mode("Low Resource / Battery Saver")
        self.assertEqual(win.right_dashboard.timer.interval(), 3000)

        # 2. High Fidelity Mode
        win.apply_performance_mode("High Fidelity")
        self.assertEqual(win.right_dashboard.timer.interval(), 500)

        # 3. Balanced Mode (Default)
        win.apply_performance_mode("Balanced")
        self.assertEqual(win.right_dashboard.timer.interval(), 1000)

        win._cleanup_on_close()
        win.close()
        app.processEvents()

    def test_05_ram_compression_and_ssd_diagnostics(self):
        """Verifies in-memory buffer compression and read-only SSD diagnostics."""
        bench = RAMCompressor.benchmark_compression(sample_size_kb=64)
        self.assertGreater(bench["ratio"], 2.0)
        self.assertGreater(bench["raw_kb"], 0)

        ssd_info = SSDHealthMonitor.get_ssd_health()
        self.assertIn("health_status", ssd_info)
        self.assertIn("read_mb", ssd_info)
        self.assertIn("write_mb", ssd_info)

        p_ok = CPUAffinityTuner.set_foreground_priority(high=False)
        self.assertTrue(p_ok)


if __name__ == "__main__":
    unittest.main()
