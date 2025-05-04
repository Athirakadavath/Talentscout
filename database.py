"""Database utilities for TalentScout chatbot"""
import sqlite3
import json
import os
from datetime import datetime

class CandidateDatabase:
    def __init__(self, db_path="candidates.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create candidates table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            experience TEXT,
            position TEXT,
            location TEXT,
            tech_stack TEXT,
            application_time TIMESTAMP,
            status TEXT DEFAULT 'new',
            conversation_history TEXT,
            notes TEXT
        )
        ''')

        conn.commit()
        conn.close()

    def save_candidate(self, candidate_info, conversation_history=None):
        """Save candidate information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Convert tech_stack list to JSON string
        if isinstance(candidate_info.get('tech_stack', []), list):
            tech_stack_json = json.dumps(candidate_info.get('tech_stack', []))
        else:
            tech_stack_json = json.dumps([])

        # Convert conversation history to JSON string
        if conversation_history:
            conv_history_json = json.dumps(conversation_history)
        else:
            conv_history_json = json.dumps([])

        try:
            cursor.execute('''
            INSERT INTO candidates
            (name, email, phone, experience, position, location, tech_stack,
            application_time, conversation_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                candidate_info.get('name', ''),
                candidate_info.get('email', ''),
                candidate_info.get('phone', ''),
                candidate_info.get('experience', ''),
                candidate_info.get('position', ''),
                candidate_info.get('location', ''),
                tech_stack_json,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                conv_history_json
            ))

            conn.commit()
            result = {"success": True, "candidate_id": cursor.lastrowid}
        except sqlite3.IntegrityError:
            # Handle duplicate email
            result = {"success": False, "error": "Candidate with this email already exists"}
        finally:
            conn.close()

        return result

    def get_candidate_by_email(self, email):
        """Retrieve candidate by email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM candidates WHERE email = ?", (email,))
        result = cursor.fetchone()

        conn.close()

        if result:
            # Parse JSON fields
            candidate = dict(result)
            candidate['tech_stack'] = json.loads(candidate['tech_stack'])
            candidate['conversation_history'] = json.loads(candidate['conversation_history'])
            return candidate
        return None

    def list_recent_candidates(self, limit=50):
        """List recent candidates"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, name, email, position, application_time, status
        FROM candidates ORDER BY application_time DESC LIMIT ?
        ''', (limit,))

        candidates = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return candidates