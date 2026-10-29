#!/usr/bin/env bash
# ==============================================================================
# Helper Script to Test Boot NovaOS-Live-x86_64.iso in QEMU Virtual Machine
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ISO_PATH="${1:-${WORKSPACE_ROOT}/NovaOS-Live-x86_64.iso}"

if [ ! -f "${ISO_PATH}" ]; then
    echo "[-] Error: ISO not found at ${ISO_PATH}"
    echo "    Run 'sudo bash scripts/build_iso.sh' first."
    exit 1
fi

echo "[*] Launching QEMU to test ${ISO_PATH}..."
echo "    Memory: 2048 MB (mimics 4 GB RAM low-spec target)"
echo "    CPUs: 2 Cores"

ACCEL="-enable-kvm -cpu host"
if [ ! -e /dev/kvm ]; then
    echo "[!] KVM not detected. Running with standard TCG software emulation."
    ACCEL=""
fi

qemu-system-x86_64 \
    ${ACCEL} \
    -m 2048 \
    -smp 2 \
    -vga virtio \
    -display sdl,gl=on \
    -cdrom "${ISO_PATH}" \
    -boot d
