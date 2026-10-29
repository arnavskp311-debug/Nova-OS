"""
Interactive Cyber Media Studio & Retro Player for NOVA OS.
Features:
1. CyberAmp Retro Winamp Audio Player with FFT Spectrum Visualizer
2. Screen Snipper & Capture Tool
3. Screen Color Eyedropper & Palette Picker
4. Pixel Art 16x16 Sprite Canvas
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QListWidget, QSlider,
    QFileDialog, QFrame, QGridLayout, QApplication
)
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor

from nova.multimedia import CyberAmpEngine, ScreenSnipper, ColorEyedropper, ChiptuneSequencer

class CyberVisualizerWidget(QWidget):
    """Dynamic FFT audio spectrum visualizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        self.bars = [5] * 16

    def set_spectrum(self, bars: list):
        self.bars = bars
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(8, 12, 22))

        w = self.width()
        num_bars = len(self.bars)
        bar_w = (w - (num_bars * 3)) // num_bars

        for i, val in enumerate(self.bars):
            h = int((val / 100.0) * (self.height() - 8))
            x = i * (bar_w + 3) + 2
            y = self.height() - h - 4

            # Cyber gradient coloring
            if val > 75:
                color = QColor(255, 42, 85)
            elif val > 45:
                color = QColor(0, 240, 255)
            else:
                color = QColor(0, 255, 136)

            painter.fillRect(x, y, bar_w, h, color)

        painter.end()


class MediaHubWidget(QWidget):
    """Interactive Multimedia Studio & CyberAmp player."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.amp_engine = CyberAmpEngine(self)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🎬")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("CYBER MULTIMEDIA & AUDIO STUDIO")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(0, 240, 255, 0.25); background: #090e1a; border-radius: 6px; }
            QTabBar::tab { background: #0f1629; color: #94a3b8; padding: 6px 14px; margin-right: 4px; border-radius: 4px; font-weight: 600; }
            QTabBar::tab:selected { background: #0052cc; color: #ffffff; border: 1px solid #00f0ff; }
        """)

        # Tab 1: CyberAmp
        self.tab_amp = self._create_cyberamp_tab()
        self.tabs.addTab(self.tab_amp, "🎵 CyberAmp Audio")

        # Tab 2: Screen Snipper
        self.tab_snip = self._create_snipper_tab()
        self.tabs.addTab(self.tab_snip, "📸 Screen Snipper")

        # Tab 3: Color Eyedropper
        self.tab_color = self._create_eyedropper_tab()
        self.tabs.addTab(self.tab_color, "🎨 Eyedropper & Palette")

        # Tab 4: Pixel Art
        self.tab_pixel = self._create_pixel_tab()
        self.tabs.addTab(self.tab_pixel, "👾 Pixel Sprite Editor")

        layout.addWidget(self.tabs)

    def _create_cyberamp_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # Visualizer
        self.viz = CyberVisualizerWidget()
        self.amp_engine.spectrum_updated.connect(self.viz.set_spectrum)
        lay.addWidget(self.viz)

        # Track title banner
        self.track_banner = QLabel("CYBERAMP READY • SELECT OR ADD TRACK")
        self.track_banner.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 11px; padding: 4px; background: #0c1222; border-radius: 4px;")
        self.amp_engine.playback_started.connect(lambda t: self.track_banner.setText(f"NOW PLAYING: {t}"))
        self.amp_engine.playback_stopped.connect(lambda: self.track_banner.setText("PLAYBACK PAUSED"))
        lay.addWidget(self.track_banner)

        # Playlist
        self.playlist_widget = QListWidget()
        self.playlist_widget.setStyleSheet("background: #070b14; color: #cbd5e1; border: 1px solid rgba(255,255,255,0.08);")
        # Add sample chiptunes
        for name in ["Cyberpunk Anthem (Chiptune)", "Hacker Pulse Wave (8-Bit)", "Victory Chime"]:
            self.playlist_widget.addItem(name)
        lay.addWidget(self.playlist_widget)

        # Player Controls Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(6)

        btn_style = "background: #111a30; border: 1px solid #00f0ff; border-radius: 4px; color: #ffffff; padding: 6px 12px; font-weight: bold;"

        prev_btn = QPushButton("⏮")
        prev_btn.setStyleSheet(btn_style)
        prev_btn.clicked.connect(self.amp_engine.prev_track)
        ctrl_bar.addWidget(prev_btn)

        play_btn = QPushButton("▶ Play")
        play_btn.setStyleSheet(btn_style)
        play_btn.clicked.connect(self._on_play_clicked)
        ctrl_bar.addWidget(play_btn)

        pause_btn = QPushButton("⏸ Pause")
        pause_btn.setStyleSheet(btn_style)
        pause_btn.clicked.connect(self.amp_engine.pause)
        ctrl_bar.addWidget(pause_btn)

        next_btn = QPushButton("⏭")
        next_btn.setStyleSheet(btn_style)
        next_btn.clicked.connect(self.amp_engine.next_track)
        ctrl_bar.addWidget(next_btn)

        ctrl_bar.addStretch()

        add_btn = QPushButton("📂 Open Audio...")
        add_btn.setStyleSheet("background: #1e152a; border: 1px solid #b026ff; color: #e2b3ff; border-radius: 4px; padding: 6px 12px;")
        add_btn.clicked.connect(self._add_file_to_playlist)
        ctrl_bar.addWidget(add_btn)

        lay.addLayout(ctrl_bar)
        return w

    def _on_play_clicked(self):
        curr = self.playlist_widget.currentRow()
        if curr == 0:
            ChiptuneSequencer.play_melody("cyber_anthem")
        elif curr == 1:
            ChiptuneSequencer.play_melody("hacker_pulse")
        elif curr == 2:
            ChiptuneSequencer.play_melody("victory_chime")
        self.amp_engine.play(curr if curr >= 0 else 0)

    def _add_file_to_playlist(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.flac *.ogg)")
        if fname:
            self.amp_engine.add_track(fname)
            self.playlist_widget.addItem(Path(fname).name)

    def _create_snipper_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        bar = QHBoxLayout()
        snip_btn = QPushButton("📸 Capture Full Screen Now")
        snip_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        snip_btn.clicked.connect(self._capture_screen)
        bar.addWidget(snip_btn)
        bar.addStretch()
        lay.addLayout(bar)

        self.preview_lbl = QLabel("No capture taken yet.")
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setStyleSheet("background: #070b14; border: 1px dashed rgba(0, 240, 255, 0.3); border-radius: 6px;")
        lay.addWidget(self.preview_lbl, stretch=1)
        return w

    def _capture_screen(self):
        pix = ScreenSnipper.capture_fullscreen()
        if pix:
            scaled = pix.scaled(480, 270, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_lbl.setPixmap(scaled)
            QApplication.clipboard().setPixmap(pix)

    def _create_eyedropper_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Click 'Pick Color' then click anywhere to grab pixel value:"))
        pick_btn = QPushButton("🎯 Pick Color Under Cursor")
        pick_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 8px; border-radius: 4px;")
        pick_btn.clicked.connect(self._pick_color)
        lay.addWidget(pick_btn)

        self.color_swatch = QLabel()
        self.color_swatch.setFixedHeight(50)
        self.color_swatch.setStyleSheet("background: #00f0ff; border-radius: 6px;")
        lay.addWidget(self.color_swatch)

        self.color_readout = QLabel("HEX: #00F0FF • RGB: rgb(0, 240, 255)")
        self.color_readout.setStyleSheet("color: #cbd5e1; font-family: 'Consolas'; font-size: 12px;")
        lay.addWidget(self.color_readout)
        lay.addStretch()
        return w

    def _pick_color(self):
        pos = QCursor.pos()
        col = ColorEyedropper.get_pixel_color(pos.x(), pos.y())
        formats = ColorEyedropper.color_to_formats(col)
        self.color_swatch.setStyleSheet(f"background: {formats['hex']}; border-radius: 6px;")
        self.color_readout.setText(f"HEX: {formats['hex']} • RGB: {formats['rgb']} • HSL: {formats['hsl']}")
        QApplication.clipboard().setText(formats['hex'])

    def _create_pixel_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.addWidget(QLabel("👾 16x16 Cyber Sprite Grid (Click pixels to paint)"))

        grid_frame = QFrame()
        grid_lay = QGridLayout(grid_frame)
        grid_lay.setSpacing(1)

        self.pixel_cells = []
        for r in range(16):
            row_cells = []
            for c in range(16):
                btn = QPushButton()
                btn.setFixedSize(14, 14)
                btn.setStyleSheet("background: #0d1424; border: 1px solid rgba(255,255,255,0.05);")
                btn.clicked.connect(lambda chk, b=btn: b.setStyleSheet("background: #00f0ff; border: none;"))
                grid_lay.addWidget(btn, r, c)
                row_cells.append(btn)
            self.pixel_cells.append(row_cells)

        lay.addWidget(grid_frame, alignment=Qt.AlignCenter)

        clear_btn = QPushButton("Clear Canvas")
        clear_btn.clicked.connect(lambda: [c.setStyleSheet("background: #0d1424; border: 1px solid rgba(255,255,255,0.05);") for row in self.pixel_cells for c in row])
        lay.addWidget(clear_btn, alignment=Qt.AlignCenter)
        return w
