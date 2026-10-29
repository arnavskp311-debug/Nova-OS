"""
NOVA OS: Unified OS Matrix & Kernel Cockpit Widget.
Interactive 10-Domain Control Hub for the 100,000 Architectural Primitives.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QSpinBox, QComboBox, QScrollArea, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

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

class OSMatrixCockpitWidget(QWidget):
    """Interactive GUI for inspecting and simulating all 100,000 OS primitives."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = get_kernel_matrix_engine()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("NOVA OS - 100,000 Kernel Architecture Matrix")
        self.resize(1000, 680)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header Banner
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🧬 KERNEL ARCHITECTURE MATRIX & COCKPIT")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setStyleSheet("color: #00FFCC;")
        h_layout.addWidget(title)

        status_lbl = QLabel("100,000 PRIMITIVES | 10 STRATEGIC DOMAINS | ACTIVE")
        status_lbl.setFont(QFont("Consolas", 9))
        status_lbl.setStyleSheet("color: #00E5FF; padding: 4px 8px; border: 1px solid #00E5FF; border-radius: 4px; background: rgba(0, 229, 255, 0.1);")
        h_layout.addStretch()
        h_layout.addWidget(status_lbl)

        main_layout.addWidget(header)

        # Tabs for all 10 domains
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #00E5FF; background: #0D1117; }
            QTabBar::tab { background: #161B22; color: #8B949E; padding: 6px 10px; font-family: Consolas; font-size: 11px; }
            QTabBar::tab:selected { background: #00E5FF; color: #000000; font-weight: bold; }
        """)

        self.tabs.addTab(self.create_d1_tab(), "D1: Kernel & CPU")
        self.tabs.addTab(self.create_d2_tab(), "D2: Drivers & PCI")
        self.tabs.addTab(self.create_d3_tab(), "D3: Storage & VFS")
        self.tabs.addTab(self.create_d4_tab(), "D4: Network & BBR")
        self.tabs.addTab(self.create_d5_tab(), "D5: Security & vTPM")
        self.tabs.addTab(self.create_d6_tab(), "D6: 5-Level Paging")
        self.tabs.addTab(self.create_d7_tab(), "D7: Compositor & HDR")
        self.tabs.addTab(self.create_d8_tab(), "D8: Syscalls & ABI")
        self.tabs.addTab(self.create_d9_tab(), "D9: PMU & Minidump")
        self.tabs.addTab(self.create_d10_tab(), "D10: I18N & BiDi")

        main_layout.addWidget(self.tabs)

    # --------------------------------------------------------------------------
    # TAB 1: KERNEL & CPU
    # --------------------------------------------------------------------------
    def create_d1_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        top_bar = QHBoxLayout()
        btn_refresh = QPushButton("Decode CPU Silicon Features & Mitigations")
        btn_refresh.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        btn_cfs = QPushButton("Simulate CFS Scheduler Timeline")
        btn_cfs.setStyleSheet("background: #238636; color: white; font-weight: bold; padding: 6px;")
        top_bar.addWidget(btn_refresh)
        top_bar.addWidget(btn_cfs)
        layout.addLayout(top_bar)

        self.d1_display = QTextEdit()
        self.d1_display.setReadOnly(True)
        self.d1_display.setFont(QFont("Consolas", 10))
        self.d1_display.setStyleSheet("background: #090D13; color: #7EE787; border: 1px solid #30363D;")
        layout.addWidget(self.d1_display)

        def on_refresh():
            data = Domain1_KernelCore.decode_cpuid_features()
            idt = Domain1_KernelCore.get_virtual_idt_vectors()
            acpi = Domain1_KernelCore.get_acpi_power_matrix()
            out = ["=== DOMAIN 1: CPU SILICON & KERNEL PRIMITIVES ===", ""]
            out.append(f"Processor Architecture: {data['arch']} ({data['processor']})")
            out.append(f"Privilege Levels: {', '.join(data['rings_supported'])}")
            out.append("\n[Instruction Sets & Hardware Extensions]")
            for k, v in data["instruction_sets"].items():
                out.append(f"  - {k:<12}: {'ENABLED' if v else 'DISABLED'}")
            out.append("\n[Microarchitectural Hardware Mitigations]")
            for k, v in data["mitigations"].items():
                out.append(f"  - {k:<15}: {v}")
            out.append("\n[ACPI Sleep & CPU Power States]")
            for k, v in acpi["sleep_states"].items():
                out.append(f"  - {k:<8}: {v}")
            out.append(f"  - CPU C-States: {', '.join(acpi['cpu_c_states'])}")
            out.append("\n[Virtual IDT Interrupt Vectors (Sample)]")
            for vec in idt[:8]:
                out.append(f"  Vector {vec['vector']:<3}: {vec['name']} [{vec['type']}]")
            self.d1_display.setText("\n".join(out))

        def on_cfs():
            tasks = [
                {"id": 101, "name": "nova_compositor", "nice": -10, "burst_ms": 15},
                {"id": 102, "name": "pajama_agent", "nice": 0, "burst_ms": 10},
                {"id": 103, "name": "background_indexer", "nice": 10, "burst_ms": 20}
            ]
            sched = Domain1_KernelCore.simulate_cfs_schedule(tasks)
            out = ["=== CFS / EEVDF SCHEDULER EXECUTION SIMULATION ===", ""]
            for item in sched["timeline"]:
                out.append(f"Task PID {item['task_id']} ({item['name']}):")
                out.append(f"  Nice: {item['nice']:<3} | Weight: {item['weight']} | Allocated: {item['allocated_ms']}ms | vRuntime Delta: {item['vruntime_delta']}")
            self.d1_display.setText("\n".join(out))

        btn_refresh.clicked.connect(on_refresh)
        btn_cfs.clicked.connect(on_cfs)
        on_refresh()
        return widget

    # --------------------------------------------------------------------------
    # TAB 2: DRIVERS & PCI BUS
    # --------------------------------------------------------------------------
    def create_d2_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel("Search 35,000+ Device Catalog:"))
        self.d2_search = QLineEdit()
        self.d2_search.setPlaceholderText("Filter by vendor, device name, or ID (e.g. Intel, NVIDIA, Realtek, 0x8086)...")
        self.d2_search.setStyleSheet("background: #161B22; color: white; padding: 4px; border: 1px solid #30363D;")
        search_bar.addWidget(self.d2_search)
        btn_search = QPushButton("Search Bus")
        btn_search.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 4px 10px;")
        search_bar.addWidget(btn_search)
        layout.addLayout(search_bar)

        self.d2_table = QTableWidget()
        self.d2_table.setColumnCount(5)
        self.d2_table.setHorizontalHeaderLabels(["BDF Slot", "Vendor ID", "Vendor", "Device ID", "Device Model"])
        self.d2_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.d2_table.setStyleSheet("background: #090D13; color: #58A6FF; gridline-color: #30363D;")
        layout.addWidget(self.d2_table)

        def populate_pci():
            results = Domain2_DeviceDrivers.query_pci_bus(self.d2_search.text())
            self.d2_table.setRowCount(len(results))
            for i, r in enumerate(results):
                self.d2_table.setItem(i, 0, QTableWidgetItem(r["bdf"]))
                self.d2_table.setItem(i, 1, QTableWidgetItem(r["vendor_id"]))
                self.d2_table.setItem(i, 2, QTableWidgetItem(r["vendor_name"]))
                self.d2_table.setItem(i, 3, QTableWidgetItem(r["device_id"]))
                self.d2_table.setItem(i, 4, QTableWidgetItem(r["device_name"]))

        btn_search.clicked.connect(populate_pci)
        self.d2_search.returnPressed.connect(populate_pci)
        populate_pci()
        return widget

    # --------------------------------------------------------------------------
    # TAB 3: STORAGE & MULTI-VFS
    # --------------------------------------------------------------------------
    def create_d3_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        top_bar = QHBoxLayout()
        btn_btrfs = QPushButton("Simulate Btrfs CoW Snapshot")
        btn_btrfs.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        btn_ntfs = QPushButton("Generate NTFS MFT Record")
        btn_ntfs.setStyleSheet("background: #238636; color: white; font-weight: bold; padding: 6px;")
        top_bar.addWidget(btn_btrfs)
        top_bar.addWidget(btn_ntfs)
        layout.addLayout(top_bar)

        self.d3_display = QTextEdit()
        self.d3_display.setReadOnly(True)
        self.d3_display.setFont(QFont("Consolas", 10))
        self.d3_display.setStyleSheet("background: #090D13; color: #F0883E; border: 1px solid #30363D;")
        layout.addWidget(self.d3_display)

        def on_btrfs():
            res = Domain3_StorageFabrics.simulate_btrfs_cow_snapshot(4194304, "NOVA OS Kernel Extent Data Block 0x7FFF")
            sched = Domain3_StorageFabrics.get_blk_mq_schedulers()
            out = ["=== BTRFS / ZFS COPY-ON-WRITE EXTENT SIMULATION ===", ""]
            out.append(f"Subvolume Snapshot ID: {res['snapshot_id']}")
            out.append(f"Source Inode: {res['source_inode']} | Generation: {res['cow_generation']}")
            out.append(f"Allocated 4KB Blocks: {res['allocated_blocks']} | Shared Extents: {res['shared_extents']}")
            out.append(f"Block Checksum ({res['checksum_algorithm']}): {res['block_checksum']}")
            out.append("\n[Block Layer Multi-Queue (blk-mq) Dispatcher]")
            out.append(f"Active Scheduler: {sched['active_scheduler']}")
            for k, v in sched["available_schedulers"].items():
                out.append(f"  - {k:<12}: {v}")
            self.d3_display.setText("\n".join(out))

        def on_ntfs():
            res = Domain3_StorageFabrics.simulate_ntfs_mft_record("SYSTEM.DAT", 40960)
            out = ["=== NTFS MASTER FILE TABLE (MFT) RECORD PARSING ===", ""]
            out.append(f"MFT Record Number: {res['mft_record_number']} [{res['record_type']}]")
            out.append(f"Filename: {res['filename']} | USN Journal: {res['usn_journal_id']}")
            out.append("\nMFT Resident / Non-Resident Attributes:")
            for attr in res["attributes"]:
                out.append(f"  - Type: {attr['type']}")
            self.d3_display.setText("\n".join(out))

        btn_btrfs.clicked.connect(on_btrfs)
        btn_ntfs.clicked.connect(on_ntfs)
        on_btrfs()
        return widget

    # --------------------------------------------------------------------------
    # TAB 4: NETWORK & BBR
    # --------------------------------------------------------------------------
    def create_d4_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        calc_bar = QHBoxLayout()
        calc_bar.addWidget(QLabel("RTT (ms):"))
        self.d4_rtt = QSpinBox()
        self.d4_rtt.setRange(1, 1000)
        self.d4_rtt.setValue(25)
        calc_bar.addWidget(self.d4_rtt)

        calc_bar.addWidget(QLabel("Bandwidth (Mbps):"))
        self.d4_bw = QSpinBox()
        self.d4_bw.setRange(1, 100000)
        self.d4_bw.setValue(1000)
        calc_bar.addWidget(self.d4_bw)

        btn_calc = QPushButton("Calculate TCP BBR Window")
        btn_calc.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        calc_bar.addWidget(btn_calc)
        layout.addLayout(calc_bar)

        self.d4_display = QTextEdit()
        self.d4_display.setReadOnly(True)
        self.d4_display.setFont(QFont("Consolas", 10))
        self.d4_display.setStyleSheet("background: #090D13; color: #58A6FF; border: 1px solid #30363D;")
        layout.addWidget(self.d4_display)

        def on_calc():
            bbr = Domain4_NetworkStack.compute_tcp_bbr_window(float(self.d4_rtt.value()), float(self.d4_bw.value()))
            ipv4 = Domain4_NetworkStack.decode_ipv4_packet_header("192.168.1.100", "1.1.1.1", "TCP")
            pass_filter, filter_msg = Domain4_NetworkStack.simulate_ebpf_packet_filter(443, 443)

            out = ["=== DOMAIN 4: NETWORKING PROTOCOLS & TCP BBR ENGINE ===", ""]
            out.append(f"Congestion Control: {bbr['congestion_algorithm']} [Mode: {bbr['mode']}]")
            out.append(f"Bandwidth-Delay Product (BDP): {bbr['bdp_bytes']:,} Bytes")
            out.append(f"Calculated Congestion Window (CWND): {bbr['calculated_cwnd_packets']} Packets (1460B MSS)")
            out.append(f"Pacing Gain: {bbr['pacing_gain']}x")
            out.append("\n[IPv4 Packet Header Decoding (RFC 791)]")
            out.append(f"  {ipv4['source_ip']} -> {ipv4['dest_ip']} [{ipv4['protocol_name']}] TTL={ipv4['ttl']}")
            out.append(f"  Header Length: {ipv4['ihl_bytes']}B | Total Length: {ipv4['total_length']}B | Checksum: {ipv4['checksum']}")
            out.append("\n[eBPF XDP Fast-Path Packet Filter]")
            out.append(f"  {filter_msg}")
            self.d4_display.setText("\n".join(out))

        btn_calc.clicked.connect(on_calc)
        on_calc()
        return widget

    # --------------------------------------------------------------------------
    # TAB 5: SECURITY & vTPM 2.0
    # --------------------------------------------------------------------------
    def create_d5_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_sb = QPushButton("Inspect Virtual TPM 2.0 PCR Bank & Secure Boot Chain")
        btn_sb.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        layout.addWidget(btn_sb)

        self.d5_display = QTextEdit()
        self.d5_display.setReadOnly(True)
        self.d5_display.setFont(QFont("Consolas", 10))
        self.d5_display.setStyleSheet("background: #090D13; color: #FF7B72; border: 1px solid #30363D;")
        layout.addWidget(self.d5_display)

        def on_sb():
            pcrs = Domain5_SecurityFortress.get_virtual_tpm_pcrs()
            sb = Domain5_SecurityFortress.verify_secure_boot_chain()
            out = ["=== DOMAIN 5: ZERO-TRUST BOOT & VIRTUAL TPM 2.0 PCR MATRIX ===", ""]
            out.append(f"Secure Boot State: {sb['secure_boot_state']}")
            out.append(f"Platform Key (PK): {sb['platform_key_pk']}")
            out.append(f"Authorized DB Signatures: {sb['signature_db_count']} | Revoked (DBX): {sb['revocation_dbx_count']}")
            out.append(f"Kernel Authenticode: {sb['kernel_signature']}")
            out.append("\n[TPM 2.0 Platform Configuration Registers (SHA-256 Measurements)]")
            for k, v in pcrs.items():
                out.append(f"  {k}:")
                out.append(f"    {v}")
            self.d5_display.setText("\n".join(out))

        btn_sb.clicked.connect(on_sb)
        on_sb()
        return widget

    # --------------------------------------------------------------------------
    # TAB 6: 5-LEVEL PAGING
    # --------------------------------------------------------------------------
    def create_d6_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("57-Bit Virtual Address (Hex):"))
        self.d6_input = QLineEdit("0x7FFF80001000")
        self.d6_input.setStyleSheet("background: #161B22; color: white; padding: 4px; border: 1px solid #30363D;")
        bar.addWidget(self.d6_input)
        btn_walk = QPushButton("Execute Page Table Walk")
        btn_walk.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        bar.addWidget(btn_walk)
        layout.addLayout(bar)

        self.d6_display = QTextEdit()
        self.d6_display.setReadOnly(True)
        self.d6_display.setFont(QFont("Consolas", 10))
        self.d6_display.setStyleSheet("background: #090D13; color: #7EE787; border: 1px solid #30363D;")
        layout.addWidget(self.d6_display)

        def on_walk():
            res = Domain6_MemoryVirtualization.simulate_5level_paging_walk(self.d6_input.text().strip())
            slub = Domain6_MemoryVirtualization.get_slub_allocator_status()
            out = ["=== 5-LEVEL PAGING (PML5) TRANSLATION ENGINE ===", ""]
            out.append(f"Virtual Address: {res['virtual_address']} -> Physical Address: {res['physical_address']}")
            out.append(f"Mode: {res['mode']}")
            out.append(f"Page Frame Number (PFN): {res['physical_frame_number']} ({res['page_size']})")
            out.append(f"Status: {res['tlb_status']}")
            out.append("\n[Page Table Hierarchy Indices]")
            for k, v in res["indices"].items():
                out.append(f"  - {k:<15}: {v}")
            out.append("\n[Active SLUB Kernel Caches]")
            for c in slub:
                out.append(f"  - {c['name']:<14}: {c['objsize']}B/obj | {c['active_objs']} objs | {c['slabs']} slabs | {c['utilization']}")
            self.d6_display.setText("\n".join(out))

        btn_walk.clicked.connect(on_walk)
        self.d6_input.returnPressed.connect(on_walk)
        on_walk()
        return widget

    # --------------------------------------------------------------------------
    # TAB 7: COMPOSITOR & HDR
    # --------------------------------------------------------------------------
    def create_d7_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.d7_display = QTextEdit()
        self.d7_display.setReadOnly(True)
        self.d7_display.setFont(QFont("Consolas", 10))
        self.d7_display.setStyleSheet("background: #090D13; color: #D2A8FF; border: 1px solid #30363D;")
        layout.addWidget(self.d7_display)

        state = Domain7_CompositorPipeline.get_display_compositor_state()
        out = ["=== DOMAIN 7: COMPOSITOR, VULKAN & COLOR SCIENCE ===", ""]
        out.append(f"Protocol: {state['compositor_protocol']}")
        out.append(f"VSync / Refresh: {state['vsync_mode']} (Target: {state['frame_time_target_ms']} ms)")
        out.append(f"Font Shaping: {state['font_engine']}")
        out.append("\n[HDR10 Color Pipeline & Gamut Mapping]")
        for k, v in state["color_science"].items():
            out.append(f"  - {k:<20}: {v}")
        self.d7_display.setText("\n".join(out))
        return widget

    # --------------------------------------------------------------------------
    # TAB 8: SYSCALLS & ABI
    # --------------------------------------------------------------------------
    def create_d8_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Query POSIX Syscall Table:"))
        self.d8_search = QLineEdit()
        self.d8_search.setPlaceholderText("Filter syscalls by name or category (e.g. read, clone, mmap, VFS)...")
        self.d8_search.setStyleSheet("background: #161B22; color: white; padding: 4px; border: 1px solid #30363D;")
        bar.addWidget(self.d8_search)
        btn_sc = QPushButton("Search")
        btn_sc.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 4px 10px;")
        bar.addWidget(btn_sc)
        layout.addLayout(bar)

        self.d8_table = QTableWidget()
        self.d8_table.setColumnCount(4)
        self.d8_table.setHorizontalHeaderLabels(["Syscall #", "Name", "Category", "C Signature"])
        self.d8_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.d8_table.setStyleSheet("background: #090D13; color: #79C0FF; gridline-color: #30363D;")
        layout.addWidget(self.d8_table)

        def populate_syscalls():
            scs = Domain8_SystemAPIs.query_syscalls(self.d8_search.text())
            self.d8_table.setRowCount(len(scs))
            for i, item in enumerate(scs):
                self.d8_table.setItem(i, 0, QTableWidgetItem(str(item["syscall_nr"])))
                self.d8_table.setItem(i, 1, QTableWidgetItem(item["name"]))
                self.d8_table.setItem(i, 2, QTableWidgetItem(item["category"]))
                self.d8_table.setItem(i, 3, QTableWidgetItem(item["sig"]))

        btn_sc.clicked.connect(populate_syscalls)
        self.d8_search.returnPressed.connect(populate_syscalls)
        populate_syscalls()
        return widget

    # --------------------------------------------------------------------------
    # TAB 9: PMU & MINIDUMP
    # --------------------------------------------------------------------------
    def create_d9_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        bar = QHBoxLayout()
        btn_pmu = QPushButton("Read PMU Performance Counters")
        btn_pmu.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        btn_dump = QPushButton("Generate Kernel Minidump")
        btn_dump.setStyleSheet("background: #DA3633; color: white; font-weight: bold; padding: 6px;")
        bar.addWidget(btn_pmu)
        bar.addWidget(btn_dump)
        layout.addLayout(bar)

        self.d9_display = QTextEdit()
        self.d9_display.setReadOnly(True)
        self.d9_display.setFont(QFont("Consolas", 10))
        self.d9_display.setStyleSheet("background: #090D13; color: #FFA657; border: 1px solid #30363D;")
        layout.addWidget(self.d9_display)

        def on_pmu():
            pmu = Domain9_DiagnosticsTracing.get_hardware_pmu_counters()
            out = ["=== HARDWARE PERFORMANCE MONITORING UNIT (PMU) COUNTERS ===", ""]
            for k, v in pmu.items():
                out.append(f"  - {k:<30}: {v}")
            self.d9_display.setText("\n".join(out))

        def on_dump():
            dump = Domain9_DiagnosticsTracing.generate_kernel_minidump()
            out = ["=== KERNEL CRASH DUMP & BSOD MINIDUMP GENERATION ===", ""]
            out.append(f"File: {dump['dump_file']}")
            out.append(f"Bugcheck: {dump['bugcheck_code']} ({dump['bugcheck_symbol']})")
            out.append(f"Instruction Pointer: {dump['faulting_ip']}")
            out.append("\nStack Backtrace:")
            for frame in dump["stack_trace"]:
                out.append(f"  {frame}")
            out.append(f"\nStatus: {dump['action']}")
            self.d9_display.setText("\n".join(out))

        btn_pmu.clicked.connect(on_pmu)
        btn_dump.clicked.connect(on_dump)
        on_pmu()
        return widget

    # --------------------------------------------------------------------------
    # TAB 10: I18N & BIDI
    # --------------------------------------------------------------------------
    def create_d10_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Analyze Text (BiDi / Unicode 16):"))
        self.d10_input = QLineEdit("مرحبا بكم في NOVA OS (Welcome to NOVA OS)")
        self.d10_input.setStyleSheet("background: #161B22; color: white; padding: 4px; border: 1px solid #30363D;")
        bar.addWidget(self.d10_input)
        btn_bidi = QPushButton("Analyze Script")
        btn_bidi.setStyleSheet("background: #00E5FF; color: black; font-weight: bold; padding: 6px;")
        bar.addWidget(btn_bidi)
        layout.addLayout(bar)

        self.d10_display = QTextEdit()
        self.d10_display.setReadOnly(True)
        self.d10_display.setFont(QFont("Consolas", 10))
        self.d10_display.setStyleSheet("background: #090D13; color: #58A6FF; border: 1px solid #30363D;")
        layout.addWidget(self.d10_display)

        def on_bidi():
            res = Domain10_HumanInterface.analyze_bidi_text(self.d10_input.text())
            at_tree = Domain10_HumanInterface.get_at_spi2_accessibility_tree()
            out = ["=== UNICODE 16.0 BIDI & ACCESSIBILITY SUBSYSTEM ===", ""]
            out.append(f"Input Text: {res['text']}")
            out.append(f"Primary Direction: {res['primary_direction']}")
            out.append(f"Mixed Directionality: {res['contains_bidi_mix']}")
            out.append(f"Standard: {res['unicode_standard']}")
            out.append("\n[AT-SPI2 Accessibility Object Tree]")
            out.append(f"Root: {at_tree['name']} [{at_tree['role']}] (States: {', '.join(at_tree['state'])})")
            out.append(f"TTS Engine Hook: {at_tree['screen_reader_engine']}")
            out.append("Accessible Nodes:")
            for ch in at_tree["children"]:
                out.append(f"  - [{ch['role']}] {ch['name']} (ID: {ch['accessible_id']})")
            self.d10_display.setText("\n".join(out))

        btn_bidi.clicked.connect(on_bidi)
        self.d10_input.returnPressed.connect(on_bidi)
        on_bidi()
        return widget
