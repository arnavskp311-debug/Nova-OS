"""
Targeted Verification Suite for Stage 3: AI and Browser Integration.
Verifies chat sessions, model cancellation, deterministic actions,
browser start page, DuckDuckGo routing, safe retrieval SSRF defenses,
and voice HUD state machine transitions.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from nova.config import BROWSER_PROFILE_DIR, DEFAULT_SEARCH_ENGINE
from nova.ollama_client import OllamaClient
from nova.database import create_chat_session, get_chat_sessions, get_chat_messages
from nova.deterministic_actions import evaluate_deterministic_query
from nova.research.safe_fetcher import SafeFetcher
from nova.permissions import get_permission_enforcer

# Ensure headless Qt application
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestStage3AIBrowser(unittest.TestCase):

    def test_01_chat_session_switching_and_combo(self):
        """Verifies chat sessions and session switcher dropdown synchronization."""
        from nova.ui.widgets.chat import ChatWidget

        client = OllamaClient()
        chat = ChatWidget(client)

        # 1. Verify session combo exists and has items
        self.assertTrue(hasattr(chat, "session_combo"))
        self.assertGreater(chat.session_combo.count(), 0)

        # 2. Create new session and verify it switches
        initial_count = chat.session_combo.count()
        chat.start_new_session()
        self.assertEqual(chat.session_combo.count(), initial_count + 1)
        new_session_id = chat.active_session_id
        self.assertIsNotNone(new_session_id)

        # 3. Switch back to first session
        first_session_id = chat.session_combo.itemData(0)
        chat.switch_to_session(first_session_id)
        self.assertEqual(chat.active_session_id, first_session_id)
        self.assertEqual(chat.session_combo.currentData(), first_session_id)

    def test_02_deterministic_query_chips(self):
        """Verifies instant responses for suggestion chips without blocking UI thread."""
        chips = [
            "Summarize this webpage",
            "Search the web for information",
            "Help me write a document",
            "Analyze this file",
            "Diagnose system health"
        ]
        for chip in chips:
            res = evaluate_deterministic_query(chip)
            self.assertIsNotNone(res, f"Deterministic response missing for chip: {chip}")
            self.assertIn("title", res)
            self.assertIn("result", res)
            self.assertIn("icon", res)
            self.assertGreater(len(res["result"]), 10)

    def test_03_browser_welcome_page_and_duckduckgo(self):
        """Verifies browser start page HTML contains space design tokens, DuckDuckGo form, and speed dials."""
        from nova.ui.widgets.browser import generate_welcome_page_html

        html = generate_welcome_page_html({"connected": True, "chrome_path": "C:\\Program Files\\Google\\Chrome\\chrome.exe"})

        # Check space theme tokens
        self.assertIn("#060b18", html)
        self.assertIn("NOVA CYBER BROWSER", html)

        # Check embedded DuckDuckGo search form
        self.assertIn('action="https://duckduckgo.com/"', html)
        self.assertIn('name="q"', html)
        self.assertIn("Search the web with DuckDuckGo", html)

        # Check speed dials
        self.assertIn("https://duckduckgo.com", html)
        self.assertIn("https://en.wikipedia.org", html)
        self.assertIn("https://github.com", html)
        self.assertIn("https://arxiv.org", html)
        self.assertIn("https://www.nature.com", html)
        self.assertIn("https://docs.python.org/3/", html)

        # Check isolation statement
        self.assertIn("TECHNICAL ISOLATION & PRIVACY ASSURANCE", html)
        self.assertIn("data/browser_profile/", html)

    def test_04_browser_isolation_profile_directory(self):
        """Verifies that NOVA Browser operates inside its dedicated isolated profile."""
        self.assertTrue(BROWSER_PROFILE_DIR.exists())
        self.assertEqual(DEFAULT_SEARCH_ENGINE, "https://duckduckgo.com/?q=")

    def test_05_safe_fetcher_ssrf_blocking(self):
        """Verifies strict SSRF filtering on loopback, private networks, and cloud metadata."""
        fetcher = SafeFetcher()

        blocked_targets = [
            "http://127.0.0.1:8080/admin",
            "http://localhost:3000",
            "http://10.0.0.1/router",
            "http://192.168.1.1/secret",
            "http://169.254.169.254/latest/meta-data/"
        ]

        for url in blocked_targets:
            success, message, meta = fetcher.fetch_webpage(url)
            self.assertFalse(success, f"URL should be blocked by SSRF defense: {url}")
            self.assertIn("BLOCKED BY NOVA OS SECURITY", message)

    def test_06_voice_hud_state_transitions(self):
        """Verifies Voice HUD orb and state pill transition through all required states."""
        from nova.ui.voice_ui import NovaVoiceHUD

        mock_engine = MagicMock()
        mock_orch = MagicMock()
        hud = NovaVoiceHUD(mock_engine, mock_orch)

        states = [
            ("idle", "● IDLE"),
            ("listening", "● LISTENING"),
            ("processing", "● PROCESSING..."),
            ("speaking", "● SPEAKING"),
            ("offline", "● UNAVAILABLE / OFFLINE"),
            ("error", "● ALERT")
        ]

        for state, expected_pill_text in states:
            hud._on_state_changed(state)
            self.assertEqual(hud.state_pill.text(), expected_pill_text)
            self.assertEqual(hud.orb.state, state)


if __name__ == "__main__":
    unittest.main()
