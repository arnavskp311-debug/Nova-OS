"""
Comprehensive Automated Unit Test Suite for NOVA OS 100,000-Primitive Architecture:
Tests all 10 foundational domains in nova.kernel_matrix and the OSMatrixCockpitWidget.
"""

import sys
import os
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from nova.kernel_matrix import (
    get_kernel_matrix_engine,
    Domain1_KernelCore,
    Domain2_DeviceDrivers,
    Domain3_StorageFabrics,
    Domain4_NetworkStack,
    Domain5_SecurityFortress,
    Domain6_MemoryVirtualization,
    Domain7_CompositorPipeline,
    Domain8_SystemAPIs,
    Domain9_DiagnosticsTracing,
    Domain10_HumanInterface
)
from nova.ui.widgets.os_matrix_cockpit import OSMatrixCockpitWidget

class TestOSKernelMatrix(unittest.TestCase):

    def setUp(self):
        self.engine = get_kernel_matrix_engine()

    def test_engine_summary(self):
        summary = self.engine.get_system_summary()
        self.assertEqual(summary["domains"], 10)
        self.assertEqual(summary["total_primitives"], 100000)
        self.assertIn("D1_Kernel_Core", summary["subsystems"])

    def test_domain1_kernel_core(self):
        cpuid = Domain1_KernelCore.decode_cpuid_features()
        self.assertIn("arch", cpuid)
        self.assertTrue(cpuid["instruction_sets"]["SSE"])

        tasks = [{"id": 1, "name": "test_task", "nice": 0, "burst_ms": 10}]
        cfs = Domain1_KernelCore.simulate_cfs_schedule(tasks)
        self.assertEqual(len(cfs["timeline"]), 1)

        idt = Domain1_KernelCore.get_virtual_idt_vectors()
        self.assertTrue(len(idt) >= 10)

        acpi = Domain1_KernelCore.get_acpi_power_matrix()
        self.assertIn("S0ix", acpi["sleep_states"])

    def test_domain2_device_drivers(self):
        results = Domain2_DeviceDrivers.query_pci_bus("Intel")
        self.assertTrue(len(results) >= 1)
        self.assertIn("0x8086", results[0]["vendor_id"])

        usb = Domain2_DeviceDrivers.get_usb_subsystem_tree()
        self.assertIn("controller", usb)
        self.assertTrue(len(usb["active_devices"]) >= 1)

    def test_domain3_storage_fabrics(self):
        cow = Domain3_StorageFabrics.simulate_btrfs_cow_snapshot(1001, "Test Extent Data")
        self.assertEqual(cow["filesystem"], "Btrfs / OpenZFS CoW Engine")
        self.assertTrue(len(cow["block_checksum"]) == 64)

        mft = Domain3_StorageFabrics.simulate_ntfs_mft_record("test.sys", 1024)
        self.assertEqual(mft["record_type"], "FILE")

        sched = Domain3_StorageFabrics.get_blk_mq_schedulers()
        self.assertIn("bfq", sched["available_schedulers"])

    def test_domain4_network_stack(self):
        bbr = Domain4_NetworkStack.compute_tcp_bbr_window(20.0, 1000.0)
        self.assertEqual(bbr["congestion_algorithm"], "TCP BBR v3")
        self.assertTrue(bbr["calculated_cwnd_packets"] > 0)

        ipv4 = Domain4_NetworkStack.decode_ipv4_packet_header("10.0.0.1", "10.0.0.2", "TCP")
        self.assertEqual(ipv4["version"], 4)
        self.assertEqual(ipv4["protocol_name"], "TCP")

        pass_filter, _ = Domain4_NetworkStack.simulate_ebpf_packet_filter(80, 80)
        self.assertTrue(pass_filter)

    def test_domain5_security_fortress(self):
        pcrs = Domain5_SecurityFortress.get_virtual_tpm_pcrs()
        self.assertTrue(len(pcrs) >= 8)

        sb = Domain5_SecurityFortress.verify_secure_boot_chain()
        self.assertEqual(sb["secure_boot_state"], "ENFORCED")

    def test_domain6_memory_virtualization(self):
        walk = Domain6_MemoryVirtualization.simulate_5level_paging_walk("0x7FFF00001000")
        self.assertIn("indices", walk)
        self.assertIn("PML5_index", walk["indices"])
        self.assertTrue(walk["physical_address"].startswith("0x"))

        slub = Domain6_MemoryVirtualization.get_slub_allocator_status()
        self.assertTrue(len(slub) >= 3)

    def test_domain7_compositor_pipeline(self):
        comp = Domain7_CompositorPipeline.get_display_compositor_state()
        self.assertIn("Wayland", comp["compositor_protocol"])
        self.assertEqual(comp["color_science"]["bit_depth"], "10-bit per channel (1.07 Billion Colors)")

    def test_domain8_system_apis(self):
        scs = Domain8_SystemAPIs.query_syscalls("read")
        self.assertTrue(len(scs) >= 1)
        self.assertEqual(scs[0]["name"], "read")

    def test_domain9_diagnostics_tracing(self):
        pmu = Domain9_DiagnosticsTracing.get_hardware_pmu_counters()
        self.assertTrue(pmu["ipc_instructions_per_cycle"] > 0)

        dump = Domain9_DiagnosticsTracing.generate_kernel_minidump()
        self.assertEqual(dump["bugcheck_code"], "0x00000139")

    def test_domain10_human_interface(self):
        bidi = Domain10_HumanInterface.analyze_bidi_text("مرحبا")
        self.assertEqual(bidi["primary_direction"], "Right-to-Left (RTL)")

        bidi_ltr = Domain10_HumanInterface.analyze_bidi_text("Hello NOVA")
        self.assertEqual(bidi_ltr["primary_direction"], "Left-to-Right (LTR)")

        at_tree = Domain10_HumanInterface.get_at_spi2_accessibility_tree()
        self.assertEqual(at_tree["role"], "application")

    def test_cockpit_widget_instantiation(self):
        cockpit = OSMatrixCockpitWidget()
        self.assertEqual(cockpit.tabs.count(), 10)
        cockpit.hide()

if __name__ == "__main__":
    unittest.main()
