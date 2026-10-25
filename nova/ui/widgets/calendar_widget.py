"""
Calendar, Reminders & Timers Widget for NOVA OS (Feature 13).
Displays full monthly calendar, today's schedule, priority reminders, and focus timers.
Matching Panel 13 of the reference design.
"""

from datetime import datetime, date
import calendar
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QGridLayout, QCalendarWidget, QCheckBox, QInputDialog,
    QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate
from PySide6.QtGui import QFont, QColor

from nova.database import (
    get_calendar_events, create_calendar_event, delete_calendar_event,
    get_reminders, create_reminder, complete_reminder, delete_reminder
)


class CalendarRemindersWidget(QWidget):
    notification_requested = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.focus_seconds = 25 * 60
        self.timer_running = False

        self.setup_ui()
        self.load_today_schedule()
        self.load_reminders()

        # Focus countdown timer
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_focus_timer)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("📅")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("CALENDAR, REMINDERS & FOCUS TIMERS")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        add_event_btn = QPushButton("➕ Add Event")
        add_event_btn.setStyleSheet("""
            QPushButton {
                background: #111d33;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #00f0ff;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
        """)
        add_event_btn.clicked.connect(self.prompt_add_event)
        head.addWidget(add_event_btn)

        add_rem_btn = QPushButton("🔔 Add Reminder")
        add_rem_btn.setStyleSheet("""
            QPushButton {
                background: #111d33;
                border: 1px solid #b026ff;
                border-radius: 4px;
                color: #e2b3ff;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #b026ff;
                color: #ffffff;
            }
        """)
        add_rem_btn.clicked.connect(self.prompt_add_reminder)
        head.addWidget(add_rem_btn)
        main_layout.addLayout(head)

        # Split: Left Calendar Grid, Right Today Agenda & Reminders
        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        # Left Calendar Frame
        cal_frame = QFrame()
        cal_frame.setStyleSheet("""
            QFrame {
                background: #080d1a;
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        cal_layout = QVBoxLayout(cal_frame)
        cal_layout.setSpacing(8)

        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.setStyleSheet("""
            QCalendarWidget QWidget {
                alternate-background-color: #090e1a;
                background-color: #080d1a;
                color: #cbd5e1;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #ffffff;
                background-color: #0b1222;
                selection-background-color: #0052cc;
                selection-color: #ffffff;
            }
            QCalendarWidget QMenu {
                background-color: #0c1424;
                color: #ffffff;
            }
            QCalendarWidget QSpinBox {
                background-color: #0d1527;
                color: #ffffff;
            }
            QCalendarWidget QToolButton {
                background-color: #111d33;
                color: #00f0ff;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.calendar_widget.selectionChanged.connect(self.on_date_selected)
        cal_layout.addWidget(self.calendar_widget)

        # Focus Countdown Timer Box (Matching Pomodoro requirement)
        timer_box = QFrame()
        timer_box.setStyleSheet("background: #0f182e; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 6px; padding: 6px;")
        t_layout = QHBoxLayout(timer_box)
        t_layout.setSpacing(8)

        t_lbl = QLabel("⏱ FOCUS TIMER:")
        t_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        t_layout.addWidget(t_lbl)

        self.timer_display = QLabel("25:00")
        self.timer_display.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; font-family: monospace;")
        t_layout.addWidget(self.timer_display)

        self.timer_btn = QPushButton("Start")
        self.timer_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
        """)
        self.timer_btn.clicked.connect(self.toggle_focus_timer)
        t_layout.addWidget(self.timer_btn)

        reset_t_btn = QPushButton("Reset")
        reset_t_btn.setStyleSheet("background: #111a2e; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: #94a3b8; padding: 4px 8px;")
        reset_t_btn.clicked.connect(self.reset_focus_timer)
        t_layout.addWidget(reset_t_btn)

        cal_layout.addWidget(timer_box)
        split_layout.addWidget(cal_frame, stretch=1)

        # Right Side: Today Agenda + Reminders (Matching Panel 13)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # 1. Today Agenda Section
        agenda_frame = QFrame()
        agenda_frame.setStyleSheet("""
            QFrame {
                background: #080d1a;
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        agenda_layout = QVBoxLayout(agenda_frame)
        agenda_layout.setSpacing(6)

        self.agenda_title = QLabel("TODAY'S SCHEDULE")
        self.agenda_title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        agenda_layout.addWidget(self.agenda_title)

        self.events_list = QListWidget()
        self.events_list.setFixedHeight(120)
        self.events_list.setStyleSheet("""
            QListWidget {
                background: #0d1527;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                color: #e2e8f0;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """)
        agenda_layout.addWidget(self.events_list)
        right_panel.addWidget(agenda_frame)

        # 2. Reminders Checklist Section
        rem_frame = QFrame()
        rem_frame.setStyleSheet("""
            QFrame {
                background: #080d1a;
                border: 1px solid rgba(176, 38, 255, 0.25);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        rem_layout = QVBoxLayout(rem_frame)
        rem_layout.setSpacing(6)

        rem_title = QLabel("URGENT REMINDERS")
        rem_title.setStyleSheet("color: #b026ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        rem_layout.addWidget(rem_title)

        self.reminders_list = QListWidget()
        self.reminders_list.setStyleSheet("""
            QListWidget {
                background: #0d1527;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                color: #e2e8f0;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """)
        self.reminders_list.itemClicked.connect(self.on_reminder_item_clicked)
        rem_layout.addWidget(self.reminders_list)
        right_panel.addWidget(rem_frame)

        split_layout.addLayout(right_panel, stretch=1)
        main_layout.addLayout(split_layout)

    def load_today_schedule(self):
        self.events_list.clear()
        today_str = datetime.now().strftime("%Y-%m-%d")
        events = get_calendar_events(today_str)
        if not events:
            # Fallback to all upcoming events
            events = get_calendar_events()

        for ev in events:
            t_span = f"{ev.get('start_time', '')} - {ev.get('end_time', '')}" if ev.get('start_time') else "All Day"
            item_text = f"🔷 {t_span}  •  {ev['title']}  [{ev.get('category', 'General')}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ev)
            self.events_list.addItem(item)

        if self.events_list.count() == 0:
            self.events_list.addItem("No scheduled events for today.")

    def load_reminders(self):
        self.reminders_list.clear()
        rems = get_reminders(include_completed=False)
        for r in rems:
            p_badge = f"[{r.get('priority', 'NORMAL')}]"
            rem_title = r.get("title") or r.get("content") or "Reminder"
            item_text = f"🔘 {rem_title}   {p_badge} (Due: {r.get('due_at', '')})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, r)
            self.reminders_list.addItem(item)

        if self.reminders_list.count() == 0:
            self.reminders_list.addItem("All reminders completed! 🎉")

    def on_date_selected(self):
        sel_date = self.calendar_widget.selectedDate().toString("yyyy-MM-dd")
        events = get_calendar_events(sel_date)
        self.events_list.clear()
        self.agenda_title.setText(f"SCHEDULE FOR {sel_date}")
        for ev in events:
            t_span = f"{ev.get('start_time', '')} - {ev.get('end_time', '')}" if ev.get('start_time') else "All Day"
            item = QListWidgetItem(f"🔷 {t_span}  •  {ev['title']}")
            item.setData(Qt.UserRole, ev)
            self.events_list.addItem(item)
        if self.events_list.count() == 0:
            self.events_list.addItem(f"No events scheduled for {sel_date}.")

    def prompt_add_event(self):
        title, ok = QInputDialog.getText(self, "Add Event", "Enter event title:")
        if ok and title.strip():
            sel_date = self.calendar_widget.selectedDate().toString("yyyy-MM-dd")
            s_time, _ = QInputDialog.getText(self, "Start Time", "Enter start time (e.g. 10:00 AM):", text="10:00 AM")
            e_time, _ = QInputDialog.getText(self, "End Time", "Enter end time (e.g. 11:30 AM):", text="11:30 AM")
            create_calendar_event(title.strip(), sel_date, s_time.strip(), e_time.strip(), "General")
            self.load_today_schedule()
            self.notification_requested.emit("EVENT SCHEDULED", f"Added '{title}' on {sel_date}", "info")

    def prompt_add_reminder(self):
        content, ok = QInputDialog.getText(self, "New Reminder", "Enter reminder task:")
        if ok and content.strip():
            from datetime import timedelta
            due = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
            create_reminder(content.strip(), due, "NORMAL")
            self.load_reminders()
            self.notification_requested.emit("REMINDER SET", f"Scheduled: '{content}'", "reminder")

    def on_reminder_item_clicked(self, item: QListWidgetItem):
        r = item.data(Qt.UserRole)
        if not r:
            return
        reply = QMessageBox.question(
            self, "Complete Reminder",
            f"Mark reminder as complete?\n'{r['content']}'",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            complete_reminder(r["id"])
            self.load_reminders()

    def toggle_focus_timer(self):
        if self.timer_running:
            self.countdown_timer.stop()
            self.timer_running = False
            self.timer_btn.setText("Resume")
        else:
            self.countdown_timer.start(1000)
            self.timer_running = True
            self.timer_btn.setText("Pause")

    def reset_focus_timer(self):
        self.countdown_timer.stop()
        self.timer_running = False
        self.focus_seconds = 25 * 60
        self.timer_display.setText("25:00")
        self.timer_btn.setText("Start")

    def _tick_focus_timer(self):
        if self.focus_seconds > 0:
            self.focus_seconds -= 1
            mins = self.focus_seconds // 60
            secs = self.focus_seconds % 60
            self.timer_display.setText(f"{mins:02d}:{secs:02d}")
        else:
            self.countdown_timer.stop()
            self.timer_running = False
            self.timer_btn.setText("Start")
            self.notification_requested.emit(
                "FOCUS SESSION COMPLETE",
                "Great work! 25-minute Pomodoro focus interval completed.",
                "success"
            )
            QMessageBox.information(self, "Focus Complete", "25-minute focus session finished! Time for a short break.")
