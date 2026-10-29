"""
Empirical Benchmark for Stage 5: Performance and Reliability.
Measures process working set RSS (before and after trim),
idle CPU impact, and timer interval throttling.
"""
import os
import sys
import psutil
from pathlib import Path
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Headless mode for benchmark
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from nova.ui.main_window import MainWindow
from nova.memory_optimizer import get_memory_optimizer

def run_benchmark():
    app = QApplication.instance() or QApplication(sys.argv)
    p = psutil.Process(os.getpid())

    # 1. Instantiate Main Desktop Window
    win = MainWindow()
    app.processEvents()

    rss_initial_mb = p.memory_info().rss / (1024 * 1024)
    print(f"INITIAL_RSS_MB: {rss_initial_mb:.2f}")

    # 2. Trim working set
    opt = get_memory_optimizer()
    ok, freed = opt.trim_current_process()
    app.processEvents()

    rss_trimmed_mb = p.memory_info().rss / (1024 * 1024)
    print(f"TRIM_SUCCESS: {ok}")
    print(f"TRIMMED_RSS_MB: {rss_trimmed_mb:.2f}")
    print(f"RAM_FREED_MB: {freed:.2f}")

    # 3. Verify Budget < 120 MB
    within_budget = rss_trimmed_mb < 120.0
    print(f"WITHIN_120MB_BUDGET: {within_budget}")

    # 4. Timer Intervals in each mode
    win.apply_performance_mode("Balanced")
    balanced_interval = win.right_dashboard.timer.interval()
    
    win.apply_performance_mode("Low Resource / Battery Saver")
    saver_interval = win.right_dashboard.timer.interval()
    
    win.apply_performance_mode("High Fidelity")
    hifi_interval = win.right_dashboard.timer.interval()

    print(f"TIMER_BALANCED_MS: {balanced_interval}")
    print(f"TIMER_SAVER_MS: {saver_interval}")
    print(f"TIMER_HIFI_MS: {hifi_interval}")

    # 5. Clean teardown
    win._cleanup_on_close()
    win.close()
    app.processEvents()

    all_timers_stopped = not (
        win.reminder_timer.isActive() or
        win.ai_status_timer.isActive() or
        win.auto_repair_timer.isActive() or
        win.right_dashboard.timer.isActive()
    )
    print(f"CLEAN_TEARDOWN_ALL_TIMERS_STOPPED: {all_timers_stopped}")

if __name__ == "__main__":
    run_benchmark()
