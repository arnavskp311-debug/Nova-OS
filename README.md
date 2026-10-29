# NOVA OS — Personalized Premium Space Desktop & Live Linux Workstation

[![Build Standalone Live Linux ISO](https://github.com/arnavskp311-debug/NovaOS/actions/workflows/build-iso.yml/badge.svg)](https://github.com/arnavskp311-debug/NovaOS/actions/workflows/build-iso.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows | Linux Live ISO](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20Live%20ISO-darkcyan.svg)](#)
[![RAM Budget: <120MB](https://img.shields.io/badge/RAM%20Budget-%3C120MB-brightgreen.svg)](#)

> **NOVA OS** is an autonomous, privacy-first desktop environment engineered for resource-constrained hardware (**Intel Core i3 / $\le$ 4 GB RAM**). It operates as both a **lightweight desktop environment on Windows** and a **bootable, standalone Live Linux ISO** (`NovaOS-Live-x86_64.iso`) based on Debian 12 Bookworm Minimal.

---

## Key Highlights

- **Deep Space Visual Identity**: Premium dark navy surface, subtle ice-blue/cyan accents, procedural deep space wallpaper, glassmorphic floating dock, and collapsible right-side system telemetry dashboard.
- **Dual Runtime Profiles**:
  1. **Windows Desktop Suite**: Runs safely in user space on Windows without modifying partitions, bootloaders, registry, or host security policies.
  2. **Standalone Live Linux ISO**: Boots directly on bare metal (UEFI & BIOS) via USB with an ultra-lightweight Openbox/X11 kiosk session (< 220 MB RAM idle).
- **Offline Autonomous AI Assistant**: Local Ollama LLM integration, instant deterministic query guidance (< 1ms), strict anti-prompt injection firewall, and source citations.
- **NOVA Secure Browser**: Sandboxed Chromium/QtWebEngine browser with built-in SSRF protection, private DuckDuckGo search, speed dials, and download security scanning (PE/MZ magic byte inspection).
- **Quantum Memory Optimizer**: Active working set trimming via Win32 64-bit kernel APIs (`EmptyWorkingSet` / `SetProcessWorkingSetSize`), reducing physical RAM footprint from ~132 MB down to **13.8 MB** (88.5% below the 120 MB budget).
- **Pajama Automation Engine**: Built-in forgiving DSL for OS scripting, automated memory flushing, file tasks, and sound notifications.
- **Security Quarantine Fortress**: Real-time download analyzer, SHA-256 fingerprinting, automated isolation vault, and WAL-safe SQLite backups.

---

## Hardware Optimization Profile

NOVA OS is engineered from the ground up for low-spec dual-core laptops and legacy workstations:
- **Processor**: Intel Core i3 (dual-core / quad-thread with AVX2) or AMD equivalent.
- **Memory**: 4 GB RAM or less (strict memory budgeting, dynamic timer throttling, inactive working set trimming).
- **Target Idle RAM**: **13.8 MB** on Windows (trimmed) / **< 220 MB** on Live Linux.
- **Storage**: 256 GB SSD / eMMC / USB 3.0 Live media.
- **Local AI Daemon**: Ollama running in CPU-only mode (`qwen2.5:0.5b` or `phi3:mini`).

---

## Desktop Environment & Visual Architecture

```
+-----------------------------------------------------------------------------------------+
| [❖ NOVA] [🔍 Universal Search]  [AI Ready]                 [CPU: 12% | RAM: 1.8GB | 11:25] |
+-----------------------------------------------------------------------------------------+
| [📁 Files]   |                                                    | [SYSTEM TELEMETRY]  |
| [🌐 Browser] |              MAXIMIZED WINDOW AREA                 | Time & Date         |
| [🤖 AI Hub]  |                                                    | Battery: 94%        |
| [📝 Notes]   |  - Rounded 12px corners                            | Network I/O         |
| [⚡ Terminal]|  - Deep space navy (#090C15)                        | Quick Actions       |
|              |  - Restrained cyan highlights                      | Auto-Repair Monitor |
+--------------+----------------------------------------------------+---------------------+
| [DOCK] [❖ Apps] [Files] [Browser] [AI] [Notes] [Terminal] [Settings] | [W1] [W2] [W3] [W4]  |
+-----------------------------------------------------------------------------------------+
```

### Global Hotkeys

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Escape`** | **Restore Desktop** | Restores any maximized application window back to the desktop shell. |
| **`Ctrl+Space`** / **`Alt+Space`** | **Universal Search** | Spotlight-style command palette for apps, settings, files, notes, and web. |
| **`Ctrl+Shift+Space`** / **`F4`** | **NOVA Voice HUD** | Siri-style animated plasma Voice Orb assistant overlay. |
| **`Ctrl+Shift+S`** | **Quick Settings** | Flyout for power profiles (Battery Saver, Balanced, High Fidelity) and RAM purger. |
| **`F11`** | **Fullscreen Toggle** | Toggles between windowed mode and full-screen desktop. |
| **`Ctrl+Q`** | **Safe Exit** | Displays confirmation dialog, terminates workers, and exits cleanly. |

---

## Running NOVA OS on Windows

### Prerequisites
- Python 3.11 or 3.12 (64-bit)
- Windows 10 or 11 (64-bit)

### Installation
```bash
# Clone the repository
git clone https://github.com/arnavskp311-debug/NovaOS.git
cd NovaOS

# Install dependencies
pip install -r requirements.txt

# Launch the desktop environment
python main.py
```

---

## Building the Standalone Live Linux ISO

Nova OS includes an automated recipe and GitHub Actions workflow to build a standalone, bootable Live Linux ISO (`NovaOS-Live-x86_64.iso`):

### Option A: 1-Click Cloud Build (GitHub Actions)
1. Navigate to the **Actions** tab in this GitHub repository.
2. Select **Build Standalone Live Linux ISO**.
3. Click **Run workflow** (or simply push to `main`).
4. Download the generated `NovaOS-Live-x86_64.iso` artifact or release asset.
5. Flash to a USB drive using [Rufus](https://rufus.ie/) or [Ventoy](https://www.ventoy.net/).

### Option B: Local Linux / WSL Build
```bash
# On Debian/Ubuntu x86_64 system:
sudo apt-get update
sudo apt-get install -y debootstrap squashfs-tools xorriso isolinux syslinux-efi grub-pc-bin grub-efi-amd64-bin mtools dosfstools

# Run the build script
chmod +x scripts/build_iso.sh
sudo ./scripts/build_iso.sh
```
See the complete guide in [`STANDALONE_ISO_GUIDE.md`](STANDALONE_ISO_GUIDE.md).

---

## Verification Test Suites

Nova OS features a 77-test regression suite covering all architectural subsystems:

```bash
# Run Stage 5 Performance & Reliability Tests
python -m unittest tests/test_stage5_performance_reliability.py

# Run Stage 4 Security & Quarantine Tests
python -m unittest tests/test_stage4_security_automation.py

# Run Stage 3 AI Assistant & Browser Tests
python -m unittest tests/test_stage3_ai_browser.py

# Run Standalone ISO Recipe Tests
python -m unittest tests/test_standalone_iso_recipe.py

# Run Mandatory Subsystems & Superpowers Tests
python -m unittest tests/test_mandatory_features.py
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
