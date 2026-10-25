"""
NOVA Vault & Document AI Q&A Interface.
Interactive offline document repository with drag-and-drop ingestion,
file list management, BM25 chunk viewer, and grounded AI chat.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QSplitter, QFileDialog, QMessageBox,
    QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

from nova.vault import get_vault, DocumentVault
from nova.ollama_client import OllamaClient
from nova.config import DEFAULT_MODEL
from nova.sound_fx import play_sound

class VaultQueryWorker(QThread):
    """Streams RAG question-answering responses based on verified document sources."""
    chunk_received = Signal(str)
    finished = Signal(str, list)
    error = Signal(str)

    def __init__(self, client: OllamaClient, vault: DocumentVault, query: str, model: str = DEFAULT_MODEL, parent=None):
        super().__init__(parent)
        self.client = client
        self.vault = vault
        self.query = query
        self.model = model
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return

            prompt, sources = self.vault.build_rag_prompt(self.query, top_k=4)
            if not sources:
                self.error.emit("No relevant document sources found in the vault matching your inquiry.")
                return

            if not self.client.check_connection():
                self.error.emit("Ollama AI is offline. Please make sure Ollama is active.")
                return

            full_resp = []
            for chunk in self.client.stream_chat([{"role": "user", "content": prompt}], model=self.model):
                if self._is_cancelled:
                    return
                full_resp.append(chunk)
                self.chunk_received.emit(chunk)

            if not self._is_cancelled:
                self.finished.emit("".join(full_resp), sources)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class VaultWidget(QWidget):
    """Document repository and offline grounded Q&A workbench."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client or OllamaClient()
        self.vault = get_vault()
        self.active_worker: Optional[VaultQueryWorker] = None
        self.setAcceptDrops(True)

        self.setup_ui()
        self.load_documents()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Bar
        header = QHBoxLayout()
        title = QLabel("NOVA VAULT // OFFLINE DOCUMENT INTELLIGENCE")
        title.setObjectName("HeaderTitle")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00F0FF;")
        header.addWidget(title)
        header.addStretch()

        self.ingest_btn = QPushButton("+ Ingest Files")
        self.ingest_btn.setObjectName("PrimaryButton")
        self.ingest_btn.setStyleSheet("""
            QPushButton {
                background: #00f0ff;
                color: #030816;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #33f3ff;
            }
        """)
        self.ingest_btn.clicked.connect(self.on_browse_files)
        header.addWidget(self.ingest_btn)

        self.clear_btn = QPushButton("Clear Vault")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 0, 85, 0.15);
                color: #ff3366;
                border: 1px solid rgba(255, 0, 85, 0.4);
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 0, 85, 0.3);
            }
        """)
        self.clear_btn.clicked.connect(self.on_clear_vault)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        # Main Horizontal Splitter (Left: Ingested Documents, Right: AI Q&A)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # Left Panel (Document List & Drop Zone)
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(8)

        doc_header = QLabel("Ingested Knowledge Sources:")
        doc_header.setStyleSheet("color: #A9BCD4; font-weight: bold; font-size: 12px;")
        left_layout.addWidget(doc_header)

        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet("""
            QListWidget {
                background-color: #0A0E19;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
                color: #EAF4FF;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(255,255,255,0.06);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 240, 255, 0.15);
                color: #00F0FF;
            }
        """)
        left_layout.addWidget(self.doc_list)

        drop_hint = QLabel("💡 Drag & drop .pdf, .txt, .md, .py files anywhere into this window.")
        drop_hint.setStyleSheet("color: #718096; font-size: 11px;")
        left_layout.addWidget(drop_hint)

        splitter.addWidget(left_panel)

        # Right Panel (Grounded Q&A & Answer Streaming)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(8)

        qa_header = QLabel("Offline Document Q&A & Semantic Synthesis:")
        qa_header.setStyleSheet("color: #A9BCD4; font-weight: bold; font-size: 12px;")
        right_layout.addWidget(qa_header)

        # Question input bar
        q_row = QHBoxLayout()
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask a question verified against your documents (e.g. summarize section 2)...")
        self.question_input.setStyleSheet("""
            QLineEdit {
                background-color: #0A0E19;
                color: #EAF4FF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #00F0FF;
            }
        """)
        self.question_input.returnPressed.connect(self.on_ask_vault)
        q_row.addWidget(self.question_input)

        self.ask_btn = QPushButton("Ask Vault AI")
        self.ask_btn.setStyleSheet("""
            QPushButton {
                background: #00F0FF;
                color: #050811;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #50f5ff;
            }
        """)
        self.ask_btn.clicked.connect(self.on_ask_vault)
        q_row.addWidget(self.ask_btn)
        right_layout.addLayout(q_row)

        # AI Answer Text Area
        self.answer_edit = QTextEdit()
        self.answer_edit.setReadOnly(True)
        self.answer_edit.setPlaceholderText("Grounded responses and citations from your documents will stream here...")
        self.answer_edit.setStyleSheet("""
            QTextEdit {
                background-color: #050811;
                color: #EAF4FF;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        right_layout.addWidget(self.answer_edit)

        # Sources Citation Box
        self.sources_lbl = QLabel("Verified Sources: None")
        self.sources_lbl.setStyleSheet("color: #00F0FF; font-size: 11px; font-weight: bold;")
        right_layout.addWidget(self.sources_lbl)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def load_documents(self):
        """Refreshes the document list in the left panel."""
        self.doc_list.clear()
        docs = self.vault.list_documents()
        for d in docs:
            size_kb = round(d["file_size"] / 1024, 1)
            item = QListWidgetItem(f"📄 {d['filename']}  ({size_kb} KB, {d['word_count']} words, {d['chunk_count']} chunks)")
            item.setData(Qt.UserRole, d["id"])
            self.doc_list.addItem(item)
        if not docs:
            item = QListWidgetItem("No documents ingested yet. Click '+ Ingest Files' or drag files here.")
            item.setForeground(Qt.gray)
            self.doc_list.addItem(item)

    def on_browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents to Ingest into NOVA Vault",
            "",
            "Documents (*.txt *.md *.py *.pdf *.json *.csv *.log);;All Files (*.*)"
        )
        if not files:
            return

        ingested_count = 0
        for f in files:
            ok, msg, _ = self.vault.ingest_document(f)
            if ok:
                ingested_count += 1

        self.load_documents()
        play_sound("success")
        QMessageBox.information(self, "Vault Ingestion Complete", f"Successfully ingested {ingested_count} file(s) into local knowledge base.")

    def on_clear_vault(self):
        reply = QMessageBox.question(
            self,
            "Clear Document Vault",
            "Are you sure you wish to delete all indexed documents and chunks from the vault?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.vault.clear_vault()
            self.load_documents()
            self.answer_edit.clear()
            self.sources_lbl.setText("Verified Sources: None")
            play_sound("chime")

    def on_ask_vault(self):
        query = self.question_input.text().strip()
        if not query:
            return

        self.answer_edit.clear()
        self.sources_lbl.setText("Searching document vault...")
        self.ask_btn.setEnabled(False)
        self.ask_btn.setText("Synthesizing...")

        play_sound("blip")
        self.active_worker = VaultQueryWorker(self.ollama_client, self.vault, query, parent=None)
        self.active_worker.chunk_received.connect(self.on_chunk_received)
        self.active_worker.finished.connect(self.on_query_finished)
        self.active_worker.error.connect(self.on_query_error)
        self.active_worker.start()

    @Slot(str)
    def on_chunk_received(self, chunk: str):
        self.answer_edit.insertPlainText(chunk)

    @Slot(str, list)
    def on_query_finished(self, full_text: str, sources: list):
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Ask Vault AI")
        source_names = list({s["filename"] for s in sources})
        self.sources_lbl.setText(f"Verified Sources ({len(sources)} citations): {', '.join(source_names)}")
        play_sound("chime")
        self.active_worker = None

    @Slot(str)
    def on_query_error(self, err_msg: str):
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Ask Vault AI")
        self.sources_lbl.setText("Error during inquiry")
        self.answer_edit.setPlainText(f"[VAULT ERROR]: {err_msg}")
        play_sound("alert")
        self.active_worker = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        count = 0
        for u in urls:
            path = u.toLocalFile()
            if path and Path(path).is_file():
                ok, _, _ = self.vault.ingest_document(path)
                if ok:
                    count += 1
        if count > 0:
            play_sound("success")
            self.load_documents()

    def cleanup(self):
        """Cooperatively cancels worker thread."""
        if self.active_worker and self.active_worker.isRunning():
            try:
                self.active_worker.chunk_received.disconnect(self.on_chunk_received)
                self.active_worker.finished.disconnect(self.on_query_finished)
                self.active_worker.error.disconnect(self.on_query_error)
            except Exception:
                pass
            self.active_worker.cancel()
            self.active_worker.quit()
            self.active_worker.wait(1500)
            self.active_worker = None

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
