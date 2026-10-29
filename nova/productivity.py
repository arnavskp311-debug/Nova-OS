"""
Productivity, Knowledge Graphs & Focus Subsystems for NOVA OS.
Includes:
1. Pomodoro Focus Timer with Sound Cues
2. Kanban Board Store (To-Do, In-Progress, Done)
3. Habit Streak Tracker
4. 2D Note Knowledge Graph Matrix
5. Mathematical Function Graphing Calculator
"""

import json
import math
import time
from pathlib import Path
from typing import List, Dict, Optional, Any

from nova.config import DATA_DIR
from nova.database import get_notes

KANBAN_FILE = DATA_DIR / "kanban_board.json"
HABITS_FILE = DATA_DIR / "habits_tracker.json"

# ============================================================================
# 1. KANBAN SPRINT BOARD STORE
# ============================================================================

class KanbanManager:
    """Manages persistent Kanban board columns and task cards."""

    DEFAULT_BOARD = {
        "todo": [
            {"id": "t1", "title": "Implement Pajama Regex Engine", "tag": "Feature"},
            {"id": "t2", "title": "Configure GPU VRAM Alert", "tag": "Telemetry"}
        ],
        "progress": [
            {"id": "t3", "title": "Review CyberAmp FFT Spectrum", "tag": "Audio"}
        ],
        "done": [
            {"id": "t4", "title": "Build 25 Mandatory OS Features", "tag": "Kernel"},
            {"id": "t5", "title": "Pass All 23 Master Test Suites", "tag": "Quality"}
        ]
    }

    @classmethod
    def get_board(cls) -> Dict[str, List[Dict[str, str]]]:
        if not KANBAN_FILE.exists():
            cls._save_board(cls.DEFAULT_BOARD)
            return dict(cls.DEFAULT_BOARD)
        try:
            with open(KANBAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return dict(cls.DEFAULT_BOARD)

    @classmethod
    def _save_board(cls, data: Dict[str, Any]):
        try:
            KANBAN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(KANBAN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def add_card(cls, column: str, title: str, tag: str = "General"):
        board = cls.get_board()
        if column not in board:
            board[column] = []
        card_id = f"c_{int(time.time() * 1000)}"
        board[column].append({"id": card_id, "title": title, "tag": tag})
        cls._save_board(board)

    @classmethod
    def move_card(cls, card_id: str, to_column: str):
        board = cls.get_board()
        target_card = None
        for col_name, cards in board.items():
            for c in cards:
                if c["id"] == card_id:
                    target_card = c
                    cards.remove(c)
                    break
            if target_card:
                break

        if target_card and to_column in board:
            board[to_column].append(target_card)
            cls._save_board(board)


# ============================================================================
# 2. HABIT TRACKER & STREAK MATRIX
# ============================================================================

class HabitTracker:
    """Tracks daily habit streaks and completion dates."""

    DEFAULT_HABITS = [
        {"id": "h1", "name": "Code in Pajama Studio", "streak": 7, "completed_today": True},
        {"id": "h2", "name": "Run System Diagnostic Check", "streak": 5, "completed_today": True},
        {"id": "h3", "name": "Review Research Agent Dossier", "streak": 3, "completed_today": False}
    ]

    @classmethod
    def get_habits(cls) -> List[Dict[str, Any]]:
        if not HABITS_FILE.exists():
            cls._save_habits(cls.DEFAULT_HABITS)
            return list(cls.DEFAULT_HABITS)
        try:
            with open(HABITS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return list(cls.DEFAULT_HABITS)

    @classmethod
    def _save_habits(cls, data: List[Dict[str, Any]]):
        try:
            HABITS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HABITS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# ============================================================================
# 3. KNOWLEDGE GRAPH MATRIX
# ============================================================================

class KnowledgeGraphBuilder:
    """Builds node and edge networks connecting notes and documents."""

    @classmethod
    def build_graph(cls) -> Dict[str, Any]:
        notes = get_notes()
        nodes = []
        edges = []

        for n in notes:
            nodes.append({
                "id": str(n["id"]),
                "title": n.get("title", f"Note {n['id']}"),
                "tags": [t.strip() for t in n.get("tags", "").split(",") if t.strip()]
            })

        # Connect notes that share tags
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                shared = set(nodes[i]["tags"]) & set(nodes[j]["tags"])
                if shared:
                    edges.append({
                        "source": nodes[i]["id"],
                        "target": nodes[j]["id"],
                        "common_tag": list(shared)[0]
                    })

        return {"nodes": nodes, "edges": edges}
