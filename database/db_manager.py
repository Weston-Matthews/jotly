"""
Database Manager - Handles all SQLite database operations
"""

import sqlite3
from datetime import datetime
import os


class DatabaseManager:
    # Manages SQLite database connection and operations
    
    def __init__(self, db_path='jotly.db'):
        # Initialize database connection and create tables if needed
        self.db_path = db_path;
        self.conn = sqlite3.connect(db_path);
        self.conn.row_factory = sqlite3.Row; # Return rows as dictionaries
        self.cursor = self.conn.cursor();
        self._create_tables();
    
    def _create_tables(self):
        # Create database tables if they don't exist
        
        # Folder table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE
            )
        ''');
        
        # Notes table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT IF NOT NULL,
                content TEXT,
                folder_id INTEGER,
                created_at TEXT IF NOT NULL,
                updated_at TEXT IF NOT NULL,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
            )
        ''');
        
        # Tasks table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT IF NOT NULL,
                description TEXT,
                completed INTEGER DEFAULT 0,
                folder_id INTEGER,
                created_at TEXT IF NOT NULL,
                updated_at TEXT IF NOT NULL,
                due_date TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
            )
        ''');
        
        # Create indices for better search performance
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_notes_title
            ON notes(title)
        ''');
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_notes_folder
            ON notes(folder_id)
        ''');
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tasks_folder
            ON tasks(folder_id)
        ''');
        
        # Full-text search virtual table for notes
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(title, content, content_rowid=id)
        ''');
        
        self.conn.commit();
    
    def execute(self, query, params=None):
        # Execute a query and return the cursor
        if params:
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)
    
    def fetchone(self):
        # Fetch one result
        return self.cursor.fetchone()
    
    def fetchall(self):
        # Fetch all results
        return self.cursor.fetchall()
    
    def commit(self):
        # Commit changes to database
        self.conn.commit();
    
    def close(self):
        # Close database connection
        self.conn.close();
    
    def get_timestamp(self):
        # Get the current timestamp in ISO format
        return datetime.now().isoformat()