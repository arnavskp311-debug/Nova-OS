#!/usr/bin/env bash
# ==============================================================================
# NOVA OS — Standalone Live Linux ISO Builder ("NovaOS-Live-x86_64.iso")
# Based on Debian 12 (Bookworm) Minimal, tailored for Intel Core i3 / 4 GB RAM.
# Supports Dual Hybrid Boot: Modern UEFI (GRUB) + Legacy BIOS (isolinux).
# ==============================================================================

set -euo pipefail

# Check for root / sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Error: This script must be run as root (use sudo bash scripts/build_iso.sh)." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-/tmp/nova_iso_build}"
ROOTFS="${BUILD_DIR}/rootfs"
ISO_DIR="${BUILD_DIR}/iso"
OUTPUT_ISO="${WORKSPACE_ROOT}/NovaOS-Live-x86_64.iso"
DEBIAN_MIRROR="${DEBIAN_MIRROR:-http://deb.debian.org/debian/}"
DEBIAN_RELEASE="bookworm"

echo "=============================================================================="
echo " NOVA OS — STANDALONE LIVE LINUX ISO BUILDER"
echo " Target Architecture: amd64 (Intel Core i3 / <= 4 GB RAM)"
echo " Base Distribution: Debian 12 (${DEBIAN_RELEASE})"
echo " Output Destination: ${OUTPUT_ISO}"
echo "=============================================================================="

# Ensure required host build packages are available
REQUIRED_TOOLS=(debootstrap mksquashfs xorriso isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin mtools dosfstools)
MISSING_TOOLS=()
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "${tool}" >/dev/null 2>&1 && [ ! -d "/usr/lib/ISOLINUX" ]; then
        MISSING_TOOLS+=("${tool}")
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo "[*] Installing missing build utilities via apt: ${MISSING_TOOLS[*]}..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y debootstrap squashfs-tools xorriso isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin mtools dosfstools
fi

# Cleanup trap for safely unmounting chroot pseudo-filesystems
cleanup() {
    echo "[*] Cleaning up build mounts..."
    set +e
    umount -l "${ROOTFS}/dev/pts" 2>/dev/null || true
    umount -l "${ROOTFS}/dev" 2>/dev/null || true
    umount -l "${ROOTFS}/proc" 2>/dev/null || true
    umount -l "${ROOTFS}/sys" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Prepare clean workspace
echo "[1/8] Preparing build directories in ${BUILD_DIR}..."
rm -rf "${BUILD_DIR}"
mkdir -p "${ROOTFS}" "${ISO_DIR}/live" "${ISO_DIR}/boot/isolinux" "${ISO_DIR}/boot/grub/x86_64-efi" "${ISO_DIR}/EFI/BOOT"

# 1. Debootstrap Minimal Rootfs
echo "[2/8] Bootstrapping Debian 12 (${DEBIAN_RELEASE}) minimal rootfs..."
debootstrap --arch=amd64 --variant=minbase "${DEBIAN_RELEASE}" "${ROOTFS}" "${DEBIAN_MIRROR}"

# 2. Configure Apt Sources & DNS
echo "[3/8] Configuring package repositories & chroot mounts..."
cat <<EOF > "${ROOTFS}/etc/apt/sources.list"
deb ${DEBIAN_MIRROR} ${DEBIAN_RELEASE} main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security ${DEBIAN_RELEASE}-security main contrib non-free non-free-firmware
deb ${DEBIAN_MIRROR} ${DEBIAN_RELEASE}-updates main contrib non-free non-free-firmware
EOF

cp /etc/resolv.conf "${ROOTFS}/etc/resolv.conf"

mount --bind /dev "${ROOTFS}/dev"
mount --bind /dev/pts "${ROOTFS}/dev/pts"
mount -t proc proc "${ROOTFS}/proc"
mount -t sysfs sysfs "${ROOTFS}/sys"

# 3. Provision Core Packages, Kernel, and Hardware Stack inside Chroot
echo "[4/8] Installing kernel, Intel graphics drivers, Openbox X11, and Python stack..."
cat <<'CHROOT_EXEC' | chroot "${ROOTFS}" /bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y

# Install LTS Linux Kernel & Live Boot
apt-get install -y --no-install-recommends \
    linux-image-amd64 live-boot live-config live-config-systemd systemd-sysv

# Install Intel UHD/HD Hardware Acceleration & Minimal X11 Server
apt-get install -y --no-install-recommends \
    xserver-xorg-core xserver-xorg-video-all xserver-xorg-input-all xinit \
    mesa-va-drivers intel-media-va-driver libgl1-mesa-dri mesa-utils libva-drm2 \
    firmware-linux-free

# Install Ultra-Lightweight Openbox Window Manager (< 25 MB RAM) & Compositor Tools
apt-get install -y --no-install-recommends \
    openbox x11-xserver-utils xdotool libnotify-bin

# Install Audio Server (ALSA + PipeWire for low-latency playback & voice recognition)
apt-get install -y --no-install-recommends \
    alsa-utils pipewire pipewire-audio-client-libraries pipewire-pulse wireplumber \
    libasound2 libasound2-plugins

# Install System Utilities & Python 3.11 Runtime
apt-get install -y --no-install-recommends \
    sudo curl wget ca-certificates git htop dbus-x11 \
    libnss3 libxcb-cursor0 libxkbcommon-x11-0 \
    python3 python3-pip python3-venv python3-dev

# Create default Live user "nova" with password "nova" and hardware groups
useradd -m -s /bin/bash -G sudo,audio,video,input,render nova
echo "nova:nova" | chpasswd
echo "root:nova" | chpasswd

# Configure passwordless sudo for live session
echo "nova ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/nova
chmod 0440 /etc/sudoers.d/nova

# Configure zero-overhead systemd autologin on tty1
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat <<'EOF' > /etc/systemd/system/getty@tty1.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin nova --noclear %I $TERM
Type=idle
EOF

# Setup bash autostart into X11 for user "nova" on tty1
cat <<'EOF' > /home/nova/.profile
# Autostart X11 session if logged in on tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx -- -nocursor -keeptty > /dev/null 2>&1
fi
EOF

# Configure Host Windows Partition Protection
# Automatically masks host NVMe/SATA partitions from accidental mounting
mkdir -p /etc/udev/rules.d
cat <<'EOF' > /etc/udev/rules.d/99-hide-internal-disks.rules
KERNEL=="nvme[0-9]*n[0-9]*", ENV{UDISKS_IGNORE}="1"
KERNEL=="sd[a-z]*", ENV{UDISKS_IGNORE}="1"
EOF

# Download and install local Ollama AI daemon (configured for CPU mode)
echo "[*] Installing Ollama local inference daemon (CPU-only)..."
if curl -fsSL https://ollama.com/install.sh | sh; then
    mkdir -p /etc/systemd/system
    cat <<'EOF' > /etc/systemd/system/ollama.service
[Unit]
Description=Ollama AI Daemon (Nova OS CPU-Only Mode)
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=nova
Group=nova
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_LLM_LIBRARY=cpu"
Environment="OLLAMA_NUM_PARALLEL=1"

[Install]
WantedBy=multi-user.target
EOF
    systemctl enable ollama.service || true
else
    echo "[!] Note: Live Ollama download failed; fallback service will start if binary is present."
fi

# Set hostname
echo "nova-os" > /etc/hostname
echo "127.0.0.1 localhost nova-os" > /etc/hosts

apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
CHROOT_EXEC

# 4. Bundle Nova OS Codebase and Install Dependencies
echo "[5/8] Bundling Nova OS codebase into /opt/nova-os..."
mkdir -p "${ROOTFS}/opt/nova-os"
cp -r "${WORKSPACE_ROOT}/nova" "${ROOTFS}/opt/nova-os/"
cp -r "${WORKSPACE_ROOT}/data" "${ROOTFS}/opt/nova-os/"
cp "${WORKSPACE_ROOT}/main.py" "${ROOTFS}/opt/nova-os/"
cp "${WORKSPACE_ROOT}/requirements.txt" "${ROOTFS}/opt/nova-os/"

# Copy iso configuration files
cp "${SCRIPT_DIR}/iso_config/xinitrc" "${ROOTFS}/home/nova/.xinitrc"
chmod +x "${ROOTFS}/home/nova/.xinitrc"
chown -R 1000:1000 "${ROOTFS}/home/nova"

# Install Python requirements and pre-initialize database inside chroot
echo "[*] Installing Python libraries in live environment..."
cat <<'CHROOT_PIP' | chroot "${ROOTFS}" /bin/bash
set -euo pipefail
pip3 install --no-cache-dir --break-system-packages -r /opt/nova-os/requirements.txt || {
    echo "[*] Standard pip install fallback..."
    pip3 install --no-cache-dir --break-system-packages PySide6 psutil requests numpy sounddevice
}

# Pre-initialize SQLite database & seed default data
cd /opt/nova-os
python3 -c "from nova.database import init_db; init_db()" || true
chown -R nova:nova /opt/nova-os
CHROOT_PIP

# 5. Extract Kernel and Initramfs for Bootloader
echo "[6/8] Extracting kernel and initramfs..."
VMLINUZ="$(ls -1 "${ROOTFS}/boot"/vmlinuz-* | sort -V | tail -n 1)"
INITRD="$(ls -1 "${ROOTFS}/boot"/initrd.img-* | sort -V | tail -n 1)"

cp "${VMLINUZ}" "${ISO_DIR}/boot/vmlinuz"
cp "${INITRD}" "${ISO_DIR}/boot/initrd.img"

# 6. Compress Rootfs into SquashFS
echo "[7/8] Compressing rootfs into filesystem.squashfs (XZ compression)..."
mksquashfs "${ROOTFS}" "${ISO_DIR}/live/filesystem.squashfs" \
    -comp xz -Xbcj x86 -b 1024k -noappend \
    -wildcards \
    -e "proc/*" -e "sys/*" -e "dev/*" -e "tmp/*" -e "var/tmp/*"

# 7. Configure Hybrid Bootloaders (UEFI & Legacy BIOS)
echo "[8/8] Configuring UEFI GRUB and Legacy BIOS ISOLINUX..."

# A. Legacy BIOS Config
cp "${SCRIPT_DIR}/iso_config/isolinux.cfg" "${ISO_DIR}/boot/isolinux/isolinux.cfg"
if [ -d "/usr/lib/ISOLINUX" ]; then
    cp /usr/lib/ISOLINUX/isolinux.bin "${ISO_DIR}/boot/isolinux/"
    cp /usr/lib/syslinux/modules/bios/*.c32 "${ISO_DIR}/boot/isolinux/" 2>/dev/null || cp /usr/lib/ISOLINUX/*.c32 "${ISO_DIR}/boot/isolinux/"
else
    # Fallback to syslinux path
    cp /usr/lib/syslinux/bios/isolinux.bin "${ISO_DIR}/boot/isolinux/" 2>/dev/null || true
    cp /usr/lib/syslinux/bios/*.c32 "${ISO_DIR}/boot/isolinux/" 2>/dev/null || true
fi

# B. UEFI Bootloader Config (FAT efiboot.img with BOOTX64.EFI)
cp "${SCRIPT_DIR}/iso_config/grub.cfg" "${ISO_DIR}/boot/grub/grub.cfg"
cp "${SCRIPT_DIR}/iso_config/grub.cfg" "${ISO_DIR}/EFI/BOOT/grub.cfg"

# Build standalone GRUB EFI binary
grub-mkstandalone \
    --format=x86_64-efi \
    --output="${ISO_DIR}/EFI/BOOT/BOOTX64.EFI" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=${SCRIPT_DIR}/iso_config/grub.cfg"

# Create bootable FAT efiboot.img for UEFI El Torito
EFIBOOT_IMG="${ISO_DIR}/boot/grub/efiboot.img"
truncate -s 10M "${EFIBOOT_IMG}"
mkfs.vfat -F 12 -n "EFI" "${EFIBOOT_IMG}"
mmd -i "${EFIBOOT_IMG}" ::EFI ::EFI/BOOT
mcopy -i "${EFIBOOT_IMG}" "${ISO_DIR}/EFI/BOOT/BOOTX64.EFI" ::EFI/BOOT/BOOTX64.EFI
mcopy -i "${EFIBOOT_IMG}" "${SCRIPT_DIR}/iso_config/grub.cfg" ::EFI/BOOT/grub.cfg

# 8. Build Hybrid ISO using xorriso
echo "[*] Assembling bootable hybrid ISO with xorriso..."
ISOHDPFX="/usr/lib/ISOLINUX/isohdpfx.bin"
if [ ! -f "${ISOHDPFX}" ]; then
    ISOHDPFX="$(find /usr/lib/syslinux -name isohdpfx.bin 2>/dev/null | head -n 1)"
fi

xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "NOVAOS_LIVE" \
    -eltorito-boot boot/isolinux/isolinux.bin \
    -eltorito-catalog boot/isolinux/boot.cat \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    -isohybrid-mbr "${ISOHDPFX}" \
    -eltorito-alt-boot \
    -e boot/grub/efiboot.img \
    -no-emul-boot -isohybrid-gpt-basdat \
    -output "${OUTPUT_ISO}" \
    "${ISO_DIR}"

# Generate SHA-256 Checksum
cd "${WORKSPACE_ROOT}"
sha256sum "$(basename "${OUTPUT_ISO}")" > "${OUTPUT_ISO}.sha256"

echo "=============================================================================="
echo " [SUCCESS] NOVA OS STANDALONE LIVE ISO BUILT SUCCESSFULLY!"
echo " ISO Location: ${OUTPUT_ISO}"
echo " File Size: $(du -h "${OUTPUT_ISO}" | cut -f1)"
echo " SHA-256 Checksum: $(cat "${OUTPUT_ISO}.sha256")"
echo "=============================================================================="
