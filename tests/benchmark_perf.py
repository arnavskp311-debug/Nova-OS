"""
Performance Profiling & Benchmark Suite for NOVA OS.
Measures baseline metrics: startup latency, DB query speed, telemetry overhead,
and UI main thread responsiveness.
"""

import time
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def benchmark_imports():
    t0 = time.perf_counter()
    import nova.config
    import nova.database
    import nova.safety
    import nova.system_monitor
    import nova.ollama_client
    import nova.chrome_integration
    t1 = time.perf_counter()
    
    from PySide6.QtWidgets import QApplication
    import PySide6.QtWebEngineWidgets
    t2 = time.perf_counter()

    return {
        "core_imports_ms": (t1 - t0) * 1000,
        "qt_webengine_imports_ms": (t2 - t1) * 1000,
        "total_import_ms": (t2 - t0) * 1000
    }

def benchmark_database():
    from nova.database import (
        init_db, add_browser_history, get_browser_history,
        add_browser_bookmark, get_browser_bookmarks, clear_browser_history
    )
    init_db()
    
    # Measure 500 inserts
    t0 = time.perf_counter()
    for i in range(500):
        add_browser_history(f"Page {i}", f"https://example.com/page/{i}", imported_from="Bench")
    t1 = time.perf_counter()

    # Measure 50 queries
    t2 = time.perf_counter()
    for i in range(50):
        get_browser_history(f"Page {i * 10}")
    t3 = time.perf_counter()

    # Cleanup
    clear_browser_history(only_imported=True)

    return {
        "insert_500_ms": (t1 - t0) * 1000,
        "query_50_ms": (t3 - t2) * 1000
    }

def benchmark_system_monitor():
    from nova.system_monitor import SystemMonitor
    mon = SystemMonitor()
    
    # Static info
    t0 = time.perf_counter()
    mon.get_static_info()
    t1 = time.perf_counter()

    # Realtime metrics
    t2 = time.perf_counter()
    for _ in range(5):
        mon.get_realtime_metrics()
    t3 = time.perf_counter()

    # Process iteration (often the biggest CPU hog on Windows)
    t4 = time.perf_counter()
    for _ in range(5):
        mon.get_top_processes(limit=8)
    t5 = time.perf_counter()

    return {
        "static_info_ms": (t1 - t0) * 1000,
        "metrics_avg_ms": ((t3 - t2) / 5) * 1000,
        "process_iter_avg_ms": ((t5 - t4) / 5) * 1000
    }

def benchmark_deterministic_actions():
    from nova.deterministic_actions import evaluate_deterministic_query, evaluate_math_expression
    
    # Measure 100 math evaluations
    t0 = time.perf_counter()
    for _ in range(100):
        evaluate_math_expression("sqrt(144) + 25 * 4 - (10 / 2)")
    t1 = time.perf_counter()

    # Measure 100 query evaluations
    t2 = time.perf_counter()
    for _ in range(100):
        evaluate_deterministic_query("16 gb to mb")
    t3 = time.perf_counter()

    return {
        "math_100_ms": (t1 - t0) * 1000,
        "math_avg_us": ((t1 - t0) / 100) * 1_000_000,
        "query_avg_us": ((t3 - t2) / 100) * 1_000_000
    }

def benchmark_nova_voice():
    from nova.voice import KokoroTTSEngine, PiperTTSEngine
    kokoro = KokoroTTSEngine()
    piper = PiperTTSEngine()

    # Disable cache for pure generation benchmark
    kokoro.enable_cache = False
    piper.enable_cache = False

    k_bench = kokoro.benchmark("This is a voice performance benchmark for NOVA OS on Kokoro.")
    p_bench = piper.benchmark("This is a voice performance benchmark for NOVA OS on Piper.")

    # Re-enable cache
    kokoro.enable_cache = True
    piper.enable_cache = True

    return {
        "kokoro": k_bench,
        "piper": p_bench
    }

def benchmark_startup_window():
    from PySide6.QtWidgets import QApplication
    from nova.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    
    t0 = time.perf_counter()
    win = MainWindow()
    t1 = time.perf_counter()

    if "dashboard" in win.windows:
        frame, _ = win.windows["dashboard"]
        if hasattr(frame.content_widget, "worker"):
            frame.content_widget.worker.stop()
    win.close()

    return {
        "main_window_init_ms": (t1 - t0) * 1000
    }

def run_benchmarks():
    print("=" * 60)
    print("NOVA OS PERFORMANCE BENCHMARK")
    print("=" * 60)

    imp = benchmark_imports()
    print(f"[IMPORTS] Core: {imp['core_imports_ms']:.1f}ms | Qt/WebEngine: {imp['qt_webengine_imports_ms']:.1f}ms | Total: {imp['total_import_ms']:.1f}ms")

    db = benchmark_database()
    print(f"[DATABASE] 500 Inserts: {db['insert_500_ms']:.1f}ms | 50 LIKE Queries: {db['query_50_ms']:.1f}ms")

    mon = benchmark_system_monitor()
    print(f"[MONITOR] Metrics Avg: {mon['metrics_avg_ms']:.1f}ms | Top Process Iter Avg: {mon['process_iter_avg_ms']:.1f}ms")

    det = benchmark_deterministic_actions()
    print(f"[DETERMINISTIC] Math Avg: {det['math_avg_us']:.1f}µs | Query Avg: {det['query_avg_us']:.1f}µs (< 0.1ms per op)")

    v_bench = benchmark_nova_voice()
    k = v_bench["kokoro"]
    p = v_bench["piper"]
    print(f"[VOICE KOKORO-82M] Load: {k.get('model_load_ms', 0):.1f}ms | Latency: {k.get('generation_latency_ms', 0):.1f}ms | RTF: {k.get('real_time_factor', 0):.3f}x | RAM: +{k.get('ram_load_delta_mb', 0)}MB")
    print(f"[VOICE PIPER-TTS]  Load: {p.get('model_load_ms', 0):.1f}ms | Latency: {p.get('generation_latency_ms', 0):.1f}ms | RTF: {p.get('real_time_factor', 0):.3f}x | RAM: +{p.get('ram_load_delta_mb', 0)}MB")

    win = benchmark_startup_window()
    print(f"[STARTUP] MainWindow Init (inc. default windows): {win['main_window_init_ms']:.1f}ms")
    print("=" * 60)

if __name__ == "__main__":
    run_benchmarks()
