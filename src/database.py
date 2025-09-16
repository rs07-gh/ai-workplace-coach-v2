"""
Database models and management for the AI Coaching Framework.
Provides session management, window tracking, and recommendation storage.
"""

import json
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


class SessionStatus(Enum):
    CREATED = "created"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WindowStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GPTConfig:
    model: str = "gpt-5"  # Changed default from gpt-5-mini to gpt-5
    reasoning_effort: str = "medium"
    verbosity: str = "medium"
    # Note: GPT-5 models don't use temperature, top_p, or penalty parameters
    # These are managed through reasoning_effort and verbosity instead

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "verbosity": self.verbosity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GPTConfig':
        return cls(
            model=data.get("model", "gpt-5"),
            reasoning_effort=data.get("reasoning_effort", "medium"),
            verbosity=data.get("verbosity", "medium"),
        )


@dataclass
class ProcessingConfig:
    window_seconds: int = 30
    system_prompt: str = ""
    enable_web_search: bool = True
    enable_tool_calling: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_seconds": self.window_seconds,
            "system_prompt": self.system_prompt,
            "enable_web_search": self.enable_web_search,
            "enable_tool_calling": self.enable_tool_calling,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingConfig':
        return cls(
            window_seconds=data.get("window_seconds", 30),
            system_prompt=data.get("system_prompt", ""),
            enable_web_search=data.get("enable_web_search", True),
            enable_tool_calling=data.get("enable_tool_calling", True),
        )


class DatabaseManager:
    def __init__(self, db_path: str = "coaching_sessions.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_file_path TEXT,
                    total_windows INTEGER DEFAULT 0,
                    completed_windows INTEGER DEFAULT 0,
                    gpt_config TEXT NOT NULL,
                    processing_config TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS windows (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    window_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    start_time REAL,
                    end_time REAL,
                    input_data TEXT,
                    output_data TEXT,
                    error_message TEXT,
                    processing_time_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                    UNIQUE (session_id, window_number)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_summaries (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    window_number INTEGER NOT NULL,
                    summary_data TEXT NOT NULL,
                    workflow_patterns TEXT,
                    tools_used TEXT,
                    previous_recommendations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                    UNIQUE (session_id, window_number)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    window_number INTEGER NOT NULL,
                    recommendation_text TEXT NOT NULL,
                    category TEXT,
                    confidence_score REAL,
                    implementation_steps TEXT,
                    expected_impact TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_windows_session_status ON windows(session_id, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_session ON recommendations(session_id)")

    def create_session(self, session_id: str, name: str, gpt_config: GPTConfig,
                      processing_config: ProcessingConfig, input_file_path: str = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO sessions (id, name, status, input_file_path, gpt_config, processing_config)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    name,
                    SessionStatus.CREATED.value,
                    input_file_path,
                    json.dumps(gpt_config.to_dict()),
                    json.dumps(processing_config.to_dict())
                ))
            return True
        except sqlite3.IntegrityError:
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sessions WHERE id = ?
            """, (session_id,))
            row = cursor.fetchone()

            if row:
                session_dict = dict(row)
                session_dict['gpt_config'] = GPTConfig.from_dict(json.loads(session_dict['gpt_config']))
                session_dict['processing_config'] = ProcessingConfig.from_dict(json.loads(session_dict['processing_config']))
                return session_dict
            return None

    def update_session_status(self, session_id: str, status: SessionStatus,
                            completed_windows: int = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                if completed_windows is not None:
                    conn.execute("""
                        UPDATE sessions
                        SET status = ?, completed_windows = ?, updated_at = CURRENT_TIMESTAMP,
                            completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
                        WHERE id = ?
                    """, (status.value, completed_windows, status.value, session_id))
                else:
                    conn.execute("""
                        UPDATE sessions
                        SET status = ?, updated_at = CURRENT_TIMESTAMP,
                            completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
                        WHERE id = ?
                    """, (status.value, status.value, session_id))
            return True
        except sqlite3.Error:
            return False

    def list_sessions(self, status: SessionStatus = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if status:
                cursor = conn.execute("""
                    SELECT id, name, status, total_windows, completed_windows, created_at, updated_at
                    FROM sessions WHERE status = ? ORDER BY updated_at DESC
                """, (status.value,))
            else:
                cursor = conn.execute("""
                    SELECT id, name, status, total_windows, completed_windows, created_at, updated_at
                    FROM sessions ORDER BY updated_at DESC
                """)

            return [dict(row) for row in cursor.fetchall()]

    def create_window(self, window_id: str, session_id: str, window_number: int,
                     start_time: float, end_time: float, input_data: Dict[str, Any]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO windows (id, session_id, window_number, status, start_time, end_time, input_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    window_id,
                    session_id,
                    window_number,
                    WindowStatus.PENDING.value,
                    start_time,
                    end_time,
                    json.dumps(input_data)
                ))
            return True
        except sqlite3.IntegrityError:
            return False

    def update_window_status(self, window_id: str, status: WindowStatus,
                           output_data: Dict[str, Any] = None, error_message: str = None,
                           processing_time: float = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE windows
                    SET status = ?, output_data = ?, error_message = ?, processing_time_seconds = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    status.value,
                    json.dumps(output_data) if output_data else None,
                    error_message,
                    processing_time,
                    window_id
                ))
            return True
        except sqlite3.Error:
            return False

    def get_session_windows(self, session_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM windows
                WHERE session_id = ?
                ORDER BY window_number
            """, (session_id,))

            windows = []
            for row in cursor.fetchall():
                window_dict = dict(row)
                if window_dict['input_data']:
                    window_dict['input_data'] = json.loads(window_dict['input_data'])
                if window_dict['output_data']:
                    window_dict['output_data'] = json.loads(window_dict['output_data'])
                windows.append(window_dict)

            return windows

    def save_context_summary(self, context_id: str, session_id: str, window_number: int,
                           summary_data: Dict[str, Any], workflow_patterns: List[str] = None,
                           tools_used: List[str] = None, previous_recommendations: List[str] = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO context_summaries
                    (id, session_id, window_number, summary_data, workflow_patterns, tools_used, previous_recommendations)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    context_id,
                    session_id,
                    window_number,
                    json.dumps(summary_data),
                    json.dumps(workflow_patterns or []),
                    json.dumps(tools_used or []),
                    json.dumps(previous_recommendations or [])
                ))
            return True
        except sqlite3.Error:
            return False

    def get_context_summary(self, session_id: str, window_number: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM context_summaries
                WHERE session_id = ? AND window_number = ?
            """, (session_id, window_number))

            row = cursor.fetchone()
            if row:
                context_dict = dict(row)
                context_dict['summary_data'] = json.loads(context_dict['summary_data'])
                context_dict['workflow_patterns'] = json.loads(context_dict['workflow_patterns'])
                context_dict['tools_used'] = json.loads(context_dict['tools_used'])
                context_dict['previous_recommendations'] = json.loads(context_dict['previous_recommendations'])
                return context_dict
            return None

    def save_recommendations(self, session_id: str, window_number: int,
                           recommendations: List[Dict[str, Any]]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                for rec in recommendations:
                    rec_id = f"{session_id}_w{window_number}_r{hash(rec.get('recommendation_text', ''))}"
                    conn.execute("""
                        INSERT OR REPLACE INTO recommendations
                        (id, session_id, window_number, recommendation_text, category,
                         confidence_score, implementation_steps, expected_impact)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rec_id,
                        session_id,
                        window_number,
                        rec.get('recommendation_text', ''),
                        rec.get('category', ''),
                        rec.get('confidence_score', 0.0),
                        json.dumps(rec.get('implementation_steps', [])),
                        rec.get('expected_impact', '')
                    ))
            return True
        except sqlite3.Error:
            return False

    def get_session_recommendations(self, session_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM recommendations
                WHERE session_id = ?
                ORDER BY window_number, created_at
            """, (session_id,))

            recommendations = []
            for row in cursor.fetchall():
                rec_dict = dict(row)
                if rec_dict['implementation_steps']:
                    rec_dict['implementation_steps'] = json.loads(rec_dict['implementation_steps'])
                recommendations.append(rec_dict)

            return recommendations

    def delete_session(self, session_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return True
        except sqlite3.Error:
            return False