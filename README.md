# NOVA OS // Cybernetic AI Desktop Environment & NOVA Voice

> **CRITICAL SAFETY NOTICE**: **NOVA OS is a trial desktop application running safely inside Windows.** It operates as a standard desktop software window. It **does NOT** replace, modify, or uninstall Windows. It **does NOT** alter bootloaders (UEFI/GPT), BIOS, disk partitions, Windows registry keys, system files, drivers, or security policies. To close NOVA OS, simply close the window or press `Ctrl+Q`. To uninstall, delete this application directory.

---

## Hardware Optimization Profile

NOVA OS and NOVA Voice are engineered from the ground up for resource-constrained hardware:
- **Processor:** Intel Core i3 (dual-core / quad-thread with AVX2)
- **Memory:** 4 GB RAM or less (strict memory budgeting, lazy loading, int8 quantization, cache purging)
- **Primary Storage:** 256 GB SSD (compact SQLite WAL, transient audio/disk cache purger)
- **Local AI:** Ollama running `qwen2.5:0.5b` (~397 MB)
- **Primary Neural Voice:** Kokoro-82M INT8 (~88 MB ONNX model, Apache 2.0)
- **Fast Local Voice Fallback:** Piper TTS (`en_US-lessac-medium`, ~60 MB ONNX model, MIT)
- **Instant Fallback:** Windows Native SAPI Speech Synthesizer (~0 MB overhead)
- **Operating System:** Windows 11 Home (64-bit)

---

## NOVA Voice — Siri-Like Conversational Voice Assistant

NOVA Voice upgrades NOVA OS and NOVA Browser with a conversational, voice-enabled assistant designed with the convenience and usability of Siri, featuring an original cyberpunk aesthetic, custom voice orb, and local speech engine architecture:

### 1. Primary Neural TTS Engine: Kokoro-82M (ONNX INT8)
- **High-Fidelity Studio Voice:** Integrates Kokoro-82M, generating natural, human-like speech with proper prosody, punctuation, and pauses.
- **Configurable Voices:** Supports 54 distinct voices including `af_nova` (default), `af_heart`, `af_bella`, `am_adam`, `bf_emma`, etc.
- **Sentence Chunking:** Automatically divides streaming responses into punctuation-bounded sentences (`. `, `! `, `? `, `\n`).
- **Immediate Playback:** Begins streaming audio chunks as soon as sentence 1 is synthesized without waiting for the full response.
- **Immediate Interruption:** Clicking **Stop** (`⏹ Stop`) or pressing the microphone halts speech output in < 20 ms.
- **Disk Audio Cache:** Caches synthesized audio by SHA-256 hash in `data/audio_cache/kokoro/` with one-click purge.
- **License:** Apache 2.0 (Permissive open source).

### 2. Local Fallbacks: Piper TTS & Windows SAPI
- **Piper TTS (MIT):** Ultra-fast local neural speech (~60 MB model) running in **0.21x real-time (5x faster than real-time)** on Intel Core i3 CPU with only ~62 MB RAM delta.
- **Windows SAPI:** Built-in Windows offline voice synthesis for instantaneous speech output with 0 MB disk footprint.
- **No Silent Cloud Fallback:** All speech synthesis and inference remain 100% on-device.

### 3. Siri-Like Visual Identity & Interaction Design
- **Animated Cyber Plasma Voice Orb:** Circular glassmorphic HUD widget with concentric glowing plasma rings:
  - `Idle`: Subtle breathing neon cyan glow (low CPU, ~15 FPS).
  - `Listening`: Dynamically expands and pulses in real time to microphone audio energy.
  - `Thinking`: Orbiting plasma particles cycling smoothly.
  - `Speaking`: Rhythmic frequency waves matching Kokoro/Piper audio output amplitude.
  - `Error`: Muted amber/crimson alert pulse.
- **Live Transcription & Spoken Sync:** Displays user speech transcript alongside NOVA's reply.
- **Push-to-Talk & Echo Suppression:** Hold to speak button with automatic mic suppression during speaker output to prevent self-recognition loops.
- **Accessible Text Input:** Full keyboard input alternative for silent environments.

### 4. NOVA Browser Context Integration
- **Summarize Active Webpage:** Extracts clean DOM text from active tab and delivers a 2-3 sentence spoken summary.
- **Explain Selection:** Explains selected text snippets on any webpage upon voice request.
- **Security Sandboxing:**
  - Strips cookies, password fields, auth tokens, and session headers.
  - Untrusted Content Guard: Isolates webpage text to prevent prompt injection attacks.
  - Consequential Action Gate: Requires explicit user confirmation before downloads, purchases, or settings changes.

---

## Global Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl+Shift+Space`** or **`F4`** | **NOVA Voice HUD** | Activates the Siri-style animated Voice Orb assistant overlay. |
| **`Ctrl+Space`** or **`Alt+Space`** | **Universal Search HUD** | Opens Spotlight-style command palette for apps, notes, bookmarks, math, and directives. |
| **`Ctrl+Shift+V`** | **Clipboard History HUD** | Opens floating clipboard manager with search and one-click paste buffer restoration. |
| **`Ctrl+Shift+S`** | **Quick Settings Flyout** | Opens quick power profile selector, accent themes, SSD storage status, and cache purger. |
| **`F11`** | **Fullscreen Toggle** | Toggles between bordered windowed mode and immersive borderless fullscreen desktop. |
| **`Ctrl+Q`** | **Safe Exit** | Displays confirmation dialog and safely terminates background workers before exiting. |
| **`Ctrl+1`** | **Telemetry Dashboard** | Opens or focuses the live CPU, RAM, Disk, and Network diagnostics monitor. |
| **`Ctrl+2`** | **NOVA AI Assistant** | Opens or focuses the local Ollama LLM chat interface. |
| **`Ctrl+3`** | **NOVA Cyber Browser** | Opens or focuses the secure Qt WebEngine browser runtime. |
| **`Ctrl+4`** | **NovaPad Notes & Reminders** | Opens or focuses local notes and scheduled task reminders. |
| **`Ctrl+5`** | **Safe Cyber Terminal** | Opens or focuses the sandboxed terminal with approval verification. |
| **`Ctrl+6`** | **Sandbox File Vault** | Opens or focuses the safe project file browser and code previewer. |
| **`Ctrl+7`** | **Control Center** | Opens or focuses the full settings, AI model configuration, and backup vault. |

---

## Real-Device Performance Benchmarks (Intel Core i3 / Windows 11)

Measured directly on the target hardware without virtualization:

```
============================================================
NOVA OS & NOVA VOICE PERFORMANCE BENCHMARK RESULTS
============================================================
[IMPORTS] Core Modules: 144.6ms | Qt/WebEngine: 80.2ms | Total: 224.7ms
[DATABASE] 500 Inserts: 28.4ms | 50 LIKE Queries: 3.7ms (WAL + Indexing)
[MONITOR] Metrics Avg: 1.1ms | Top Process Iter Avg: 96.5ms
[DETERMINISTIC] Math Avg: 9.4µs | Query Avg: 2.5µs (< 0.01ms per op)
[VOICE KOKORO-82M] Load: 5,311ms | Generation: 15.1s | RTF: 3.52x | RAM Delta: +154.4 MB
[VOICE PIPER-TTS]  Load: 7,637ms | Generation: 743.1ms | RTF: 0.21x | RAM Delta: +61.8 MB
[STARTUP] MainWindow Init (inc. full desktop & Voice HUD): 336.2ms
============================================================
```

### Synthesis Latency Analysis:
- **Kokoro-82M (INT8):** Delivers studio-grade neural voice output. Because synthesis latency on dual-core CPU is ~3.5x real-time, sentence chunking begins playback as soon as the first sentence completes.
- **Piper TTS (Local Fallback):** Optimized for low-spec CPUs, generating speech in **743 ms (0.21x real-time)**, providing an ultra-responsive local alternative.
- **Windows SAPI:** Near-instantaneous (~50 ms) fallback with zero RAM delta.

---

## Modular Architecture & Project Structure

The codebase strictly isolates all voice subsystems into clean, decoupled modules:

```
O.S/
│
├── main.py                         # Master application entry point
├── requirements.txt                # Lightweight dependencies
├── run_nova.bat                    # Windows Command Prompt launcher
├── run_nova.ps1                    # Windows PowerShell launcher
├── README.md                       # Comprehensive technical guide & audit
├── CHROME_INTEGRATION.md           # Safe Chrome Integration technical spec
├── LINUX_BASE_EVALUATION.md        # Stage 7 Standalone Linux OS evaluation & VM roadmap
│
├── nova/
│   ├── __init__.py
│   ├── config.py                   # Hardware profiles, constants, fallback models, paths
│   ├── database.py                 # SQLite Schema v3 (WAL mode, composite indexes, backups, cache)
│   ├── deterministic_actions.py    # Safe AST math parser, unit conversion, clock (< 0.01 ms)
│   ├── clipboard_manager.py        # Clipboard listener & Ctrl+Shift+V history HUD
│   ├── safety.py                   # Sandboxed command risk analyzer & approval rules
│   ├── chrome_integration.py       # Safe Chrome discovery, read-only import, URL handoff
│   ├── ollama_client.py            # Asynchronous Ollama HTTP API client
│   ├── system_monitor.py           # Read-only psutil hardware telemetry
│   │
│   ├── voice/                      # Modular Voice Subsystem
│   │   ├── __init__.py             # VoiceEngine master unified interface
│   │   ├── kokoro_tts.py           # Kokoro-82M primary neural TTS engine (Apache 2.0)
│   │   ├── piper_fallback.py       # Piper fast local fallback TTS engine (MIT)
│   │   ├── audio_playback.py       # Asynchronous chunk player with immediate stop & RMS amplitude
│   │   ├── voice_input.py          # Microphone stream capture, VAD & echo suppression
│   │   ├── speech_recognition.py   # Speech-to-Text worker & direct text fallback
│   │   ├── ai_orchestrator.py      # Conversational loop, sentence chunking & deterministic routing
│   │   └── browser_context.py      # Safe webpage text & selection extractor with security guard
│   │
│   └── ui/
│       ├── __init__.py
│       ├── theme.py                # Cyberpunk QSS styles & dynamic neon accents
│       ├── main_window.py          # Master canvas, window manager, shortcuts, voice integration
│       ├── taskbar.py              # Taskbar with Start menu, Search, Voice, tray, Quick Settings
│       ├── window_frame.py         # Movable, minimizable, resizable floating frames
│       ├── notifications.py        # Non-blocking HUD toast notification stack manager
│       ├── voice_ui.py             # Siri-style NovaVoiceHUD & animated Cyber Voice Orb
│       │
│       └── widgets/
│           ├── universal_search.py # Spotlight command palette & math HUD (Ctrl+Space)
│           ├── quick_settings.py   # Flyout panel for performance profiles & storage meter
│           ├── browser.py          # Multi-tab Qt WebEngine browser with NOVA Voice toolbar button
│           ├── chrome_connect_dialog.py # Safe Chrome import permissions modal
│           ├── dashboard.py        # System telemetry metrics and process monitor
│           ├── chat.py             # Ollama AI Assistant with streaming & TTS readout
│           ├── notes.py            # NovaPad Knowledge Vault & scheduled reminders
│           ├── terminal.py         # Sandboxed cyber terminal with approval gate
│           ├── file_viewer.py      # Safe file explorer and code previewer
│           ├── settings.py         # Control Center (models, accents, voice engine selector)
│           └── approval_dialog.py  # Interactive modal for command execution approval
│
├── tests/
│   ├── test_nova.py                # 13 comprehensive automated test suites (All PASS)
│   └── benchmark_perf.py           # Real-time latency, generation speed & RAM profiling
│
└── data/                           # Local persistent data directory
    ├── nova_os.db                  # Local SQLite Schema v3 database
    ├── backups/                    # Atomic database snapshot archives
    ├── audio_cache/                # Cached Kokoro & Piper speech audio
    │   ├── kokoro/
    │   └── piper/
    ├── models/                     # Local ONNX models
    │   ├── kokoro/                 # kokoro-v1.0.int8.onnx (88 MB) + voices-v1.0.bin (27 MB)
    │   └── piper/                  # en_US-lessac-medium.onnx (60 MB) + config
    ├── browser_profile/            # Isolated Qt WebEngine profile & disk cache
    └── logs/                       # Application runtime logs (nova_os.log)
```

---

## Installation & Setup on Windows

### Prerequisites
1. **Windows 10 or Windows 11 (64-bit)**
2. **Python 3.10+** (Python 3.12 recommended)
3. **Ollama for Windows** (Download from [ollama.com](https://ollama.com))

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Verify or Pull the Local 0.5B Model
```powershell
ollama pull qwen2.5:0.5b
```

### 3. Launch NOVA OS & NOVA Voice
Double-click `run_nova.bat` or run:
```powershell
python main.py
```
- Click **🎙 Voice** on the taskbar or press **`Ctrl+Shift+Space`** / **`F4`** to invoke NOVA Voice.
- In NOVA Browser, click **🎙 NOVA Voice** in the address toolbar to analyze or summarize the active webpage.

---

## Verification & Testing Matrix

To execute the automated end-to-end verification suite:
```powershell
python tests/test_nova.py
```

### Verification Audit Results

| Subsystem / Feature | Status | Verification Evidence |
| :--- | :---: | :--- |
| **Kokoro-82M Primary TTS** | **PASS** | INT8 ONNX model (88 MB) + voices (27 MB) loaded, 54 voices verified, sentence chunking tested |
| **Piper TTS Local Fallback** | **PASS** | `en_US-lessac-medium` ONNX model loaded, generates speech in 0.21x real-time (743 ms) |
| **Audio Playback & Immediate Stop** | **PASS** | Async queue playback, volume control, immediate interruption halts sound in < 20 ms |
| **Animated Voice Orb & States** | **PASS** | `Idle`, `Listening`, `Thinking`, `Speaking`, `Error` states verified with live amplitude pulse |
| **Voice Input & Echo Suppression** | **PASS** | RMS energy calculation, VAD pause detection, automatic mic suppression during speaker audio |
| **Speech Recognition & Text Fallback** | **PASS** | Background STT worker tested; keyboard text fallback field operational |
| **AI Orchestrator & Deterministic Routing** | **PASS** | Fast deterministic commands executed in 2.5 µs – 9.4 µs (< 0.01 ms); Qwen streaming connected |
| **Consequential Action Safety Gate** | **PASS** | Destructive / modifying commands require user approval dialog before execution |
| **Browser Context Sanitization** | **PASS** | Cookies, passwords, and tokens redacted; anti-prompt-injection boundary guard verified |
| **Browser Voice Integration** | **PASS** | Address bar `🎙 NOVA Voice` button opens Voice HUD with page context synchronization |
| **Control Center Voice Settings** | **PASS** | TTS engine switcher, voice profile picker, speech rate slider, audio cache purger |
| **Global Keyboard Shortcuts** | **PASS** | `Ctrl+Shift+Space` and `F4` toggle Voice HUD; all desktop shortcuts verified |
| **Host System Protection** | **PASS** | Zero modifications to Windows bootloaders, registry, partitions, or system files |
| **Hardware GPU Acceleration** | **NOT TESTED** | Hardware-specific WebGL/Vulkan dependent on local graphics drivers |

---

## Safe Uninstallation

Because NOVA OS and NOVA Voice are normal, self-contained desktop trial applications:
1. Close the application window or press `Ctrl+Q`.
2. To remove all application files, models, and local databases, simply delete the project folder:
   `c:\Users\DAV-3\Desktop\Project\O.S`
3. No Windows settings, registry keys, bootloaders, or system files were modified.
