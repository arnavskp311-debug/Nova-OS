# NOVA OS — Lightweight Linux Base Evaluation & Standalone Roadmap
**Target Hardware:** Intel Core i3 | 4 GB RAM or less | 256 GB SSD  
**Current Status:** Windows 11 Desktop Application Trial (Zero host modification)  
**Future Scope:** Independent, self-contained OS evaluation via VM and Live USB

---

## 1. Executive Summary & Non-Destructive Principles

NOVA OS is currently deployed as a safe, isolated, high-performance desktop environment running on top of Windows 11 Home. It executes entirely in user space without administrator privileges, preserving Windows bootloaders (UEFI/GPT), system files, partitions, and drivers.

To evaluate transitioning NOVA OS into an independent, bootable operating system tailored for resource-constrained hardware (4 GB RAM, dual-core/quad-thread Core i3), this document establishes an architectural evaluation of lightweight Linux foundations and provides a **zero-risk testing methodology** using Virtual Machines (VMs) and Live USBs.

> [!IMPORTANT]
> **Safety Guarantee:** Testing an independent OS must NEVER alter the user's host Windows installation or SSD partitions. All initial evaluation is conducted exclusively inside isolated virtualized environments (QEMU/KVM, VirtualBox) or read-only/persistent Live USB sessions without mounting internal drives.

---

## 2. Linux Distribution Candidate Comparison

For hardware with 4 GB of RAM, the underlying operating system baseline must consume **under 250 MB of RAM at idle**, leaving **~3.7 GB of RAM** free for the PySide6 UI, Qt WebEngine browser tabs, and the Ollama `qwen2.5:0.5b` neural model (~450 MB).

| Distribution | Init System | C Library | Idle RAM Footprint | Binary PySide6 / Qt6 Support | Evaluation Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Debian 12 (Minimal/Netinst)** | systemd | glibc | ~180 MB – 220 MB | **Native & Flawless** (via `python3-pyqt6` / PySide6 pip wheels) | **Recommended (Primary Choice)** |
| **Void Linux (glibc)** | runit | glibc | ~110 MB – 140 MB | Native (xbps + pip) | **Strong Alternative** |
| **Alpine Linux** | OpenRC | musl libc | **~60 MB – 85 MB** | Limited (musl lacks prebuilt PySide6/QtWebEngine wheels; requires compilation or glibc chroot) | *Complex Maintenance* |
| **Arch Linux (Minimal)** | systemd | glibc | ~220 MB – 260 MB | Native (pacman) | *Rolling updates risk breakages* |

### Detailed Candidate Analysis

### Option A: Debian 12 "Bookworm" Minimal (Recommended)
- **Advantages:**
  - Standard `glibc` with universal pre-compiled Python binary wheels (`pip install PySide6 psutil`).
  - Pre-packaged `libqt6webengine6-data` and hardware acceleration support for Intel HD/UHD graphics via Mesa.
  - Unrivaled stability, long-term support (LTS), and predictable package lifecycle.
  - Idle memory: ~190 MB when configured without a display manager (direct `startx` or `greetd`).
- **Disadvantages:**
  - Slightly larger disk footprint (~1.8 GB base install vs ~400 MB for Alpine).

### Option B: Void Linux (glibc variant)
- **Advantages:**
  - Uses `runit` instead of `systemd`, resulting in near-instant boot times (< 3 seconds) and lower idle memory (~120 MB).
  - Clean separation of packages with `xbps`.
- **Disadvantages:**
  - Smaller community repository; occasional manual compilation needed for niche dependencies.

### Option C: Alpine Linux
- **Advantages:**
  - Incredibly tiny (~80 MB idle RAM, 200 MB disk image).
- **Disadvantages:**
  - Uses `musl libc`. PySide6 and QtWebEngine binary wheels from PyPI are compiled against `glibc` and do not run out of the box on musl without an emulation layer (`gcompat`), which degrades performance.

---

## 3. Display Server & Compositor Architecture

To maintain 60 FPS fluidity on Intel Core i3 integrated graphics while saving memory:

```
+-------------------------------------------------------------+
|                      NOVA OS UI Shell                       |
|           (PySide6 / Qt WebEngine / System Monitor)          |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|              Compositor / Window Manager                    |
|       Option 1: labwc (Wayland / wlroots, ~45 MB RAM)       |
|       Option 2: Openbox (X11, ~25 MB RAM)                   |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|              Linux Kernel + Mesa Intel Drivers              |
|                   (Direct Rendering / DRI3)                 |
+-------------------------------------------------------------+
```

1. **Wayland with `labwc` (Recommended for modern stack):**
   - Lightweight stacking Wayland compositor modeled after Openbox.
   - Built on `wlroots`; provides tear-free vsync rendering on Intel HD Graphics.
   - Total memory footprint: ~45 MB RAM.
2. **X11 with `openbox` (Recommended for simplest setup):**
   - Mature, robust, rock-solid multi-window management.
   - Total memory footprint: ~25 MB RAM.
3. **Kiosk Mode with `cage`:**
   - Single-window Wayland kiosk compositor that launches only NOVA OS fullscreen. Best if NOVA OS acts as the exclusive desktop environment.

---

## 4. Hardware Sizing & Memory Budget (4 GB RAM)

Target memory allocation during peak workload on standalone Linux:

| Subsystem / Process | Windows 11 Base (Current) | Standalone Debian Minimal (Target) | Savings for AI / Apps |
| :--- | :--- | :--- | :--- |
| **Kernel & OS Services** | ~1,600 MB – 2,200 MB | **~210 MB** | **+1,600 MB freed** |
| **NOVA OS Shell (PySide6)** | ~95 MB | ~85 MB | Identical |
| **Ollama Daemon (`qwen2.5:0.5b`)** | ~480 MB | ~440 MB | Fast CPU AVX2 inference |
| **NOVA Browser (2 Active Tabs)** | ~320 MB | ~280 MB | Hardware GPU acceleration |
| **Available Free Headroom** | **~1,200 MB** | **~2,985 MB** | **2.5x more headroom** |

*Conclusion:* On a 4 GB RAM machine, moving to a lightweight Linux base frees up almost **3 GB of RAM**, completely eliminating swap thrashing on 256 GB SSDs.

---

## 5. VM Testing Roadmap (Phase 1 — Zero Risk)

Prior to creating any USB media or bootloader configs, develop and verify NOVA OS inside a virtual machine:

### Step 1: Create Minimal Virtual Machine
- **Hypervisor:** VirtualBox, VMware Player, or Hyper-V (Windows Native).
- **Settings:**
  - Cores: 2 vCPUs
  - RAM: 2048 MB (mimics low-spec constraint)
  - Virtual Disk: 15 GB (Dynamically Allocated `.vdi` on SSD)
  - Video Memory: 64 MB (Enable 3D Acceleration)

### Step 2: Install Debian 12 Netinst
```bash
# During installation, uncheck GNOME, KDE, and standard desktop environments.
# Select ONLY: SSH Server (optional) and Standard System Utilities.
```

### Step 3: Install Graphics & Python Stack
```bash
sudo apt update && sudo apt install -y \
    xorg openbox lightdm python3 python3-pip python3-venv \
    libxcb-cursor0 libgl1-mesa-dri mesa-utils libnss3 libasound2 \
    curl git htop
```

### Step 4: Deploy NOVA OS
```bash
# Clone and prepare virtual environment
cd /opt
sudo git clone <repo_url> nova_os
cd nova_os
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# Configure autostart in Openbox:
mkdir -p ~/.config/openbox
echo "exec /opt/nova_os/venv/bin/python /opt/nova_os/main.py --fullscreen" > ~/.config/openbox/autostart
```

---

## 6. Live USB Testing Roadmap (Phase 2 — Non-Destructive Boot)

Once the VM image is validated, build a non-destructive Live USB that boots directly into RAM without touching the internal 256 GB Windows SSD:

1. **Tooling:** Use `Debian Live Build` (`lb config && lb build`) or `Ventoy` with a persistent loop image.
2. **UEFI Boot:** Configure GRUB to boot with `toram` option, loading the rootfs into memory.
3. **Partition Isolation:** Disable automounting of internal NVMe/SATA partitions (`/dev/nvme0n1*`, `/dev/sda*`) via `udev` rules:
   ```udev
   # /etc/udev/rules.d/99-hide-internal-disks.rules
   KERNEL=="nvme[0-9]*n[0-9]*", ENV{UDISKS_IGNORE}="1"
   KERNEL=="sd[a-z]*", ENV{UDISKS_IGNORE}="1"
   ```
4. **Safety Check:** Boot on the target laptop. Verify Windows 11 continues to boot normally when the USB drive is unplugged.

---

## 7. Next Steps Summary
- **Current Milestone:** NOVA OS Windows 11 Desktop Edition is fully stable, low-RAM tuned, and feature complete.
- **Stage 7 Gate:** No disk partitioning or bare-metal dual booting will be performed until Phase 1 (VM) and Phase 2 (Live USB) have passed 100% of functional benchmarks.
