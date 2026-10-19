"""
Database Manager - Handles all SQLite database operations
"""

import os
import sqlite3
from datetime import datetime


class DatabaseManager:
    """Manages SQLite connection, schema, and migrations."""

    def __init__(self, db_path='jotly.db'):
        self.db_path = db_path
        if db_path != ':memory:':
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.cursor = self.conn.cursor()
        self.fts_available = False
        self._create_tables()
        self._migrate_schema()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                folder_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER DEFAULT 0,
                folder_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                due_date TEXT,
                starred INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
            )
        ''')

        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)'
        )
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id)'
        )
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_tasks_folder ON tasks(folder_id)'
        )

        self._create_tag_tables()
        self._create_attachment_table()
        self._ensure_notes_fts()
        self.conn.commit()

    def _migrate_schema(self):
        """Fix legacy schema quirks from earlier drafts."""
        self._rebuild_table_if_dirty('notes', self._notes_create_sql())
        self._rebuild_table_if_dirty('tasks', self._tasks_create_sql())
        self._ensure_column('tasks', 'starred', 'INTEGER DEFAULT 0')
        self._ensure_column('tasks', 'sort_order', 'INTEGER DEFAULT 0')
        self._create_tag_tables()
        self._create_attachment_table()
        self._ensure_notes_fts()
        self.conn.commit()

    def _create_tag_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE,
                created_at TEXT NOT NULL,
                UNIQUE(name)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag_id)'
        )

    def _create_attachment_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                mime TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_attachments_note ON attachments(note_id)'
        )

    def _notes_create_sql(self):
        return '''
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                folder_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
            )
        '''

    def _tasks_create_sql(self):
        return '''
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER DEFAULT 0,
                folder_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                due_date TEXT,
                starred INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
            )
        '''

    def _ensure_column(self, table_name, column_name, ddl):
        cols = {row[1] for row in self.cursor.execute(f'PRAGMA table_info({table_name})')}
        if column_name not in cols:
            self.cursor.execute(
                f'ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}'
            )

    def _rebuild_table_if_dirty(self, table_name, create_sql):
        """Recreate a table if a column type still contains the old 'TEXT IF' typo."""
        columns = list(self.cursor.execute(f'PRAGMA table_info({table_name})'))
        dirty = any(' IF' in (col[2] or '') for col in columns)
        if not dirty:
            return

        tmp_name = f'{table_name}_migrating'
        col_names = ', '.join(col[1] for col in columns)
        self.cursor.execute(f'ALTER TABLE {table_name} RENAME TO {tmp_name}')
        self.cursor.execute(create_sql)
        self.cursor.execute(
            f'INSERT INTO {table_name} ({col_names}) SELECT {col_names} FROM {tmp_name}'
        )
        self.cursor.execute(f'DROP TABLE {tmp_name}')

        if table_name == 'notes':
            self.cursor.execute('DROP INDEX IF EXISTS idx_notes_title')
            self.cursor.execute('DROP INDEX IF EXISTS idx_notes_folder')
            self.cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)'
            )
            self.cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id)'
            )
        elif table_name == 'tasks':
            self.cursor.execute('DROP INDEX IF EXISTS idx_tasks_folder')
            self.cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_tasks_folder ON tasks(folder_id)'
            )

    def _ensure_notes_fts(self):
        """Use an external-content FTS5 table kept in sync by triggers.

        If the SQLite build lacks FTS5 (common on some Android recipes),
        fall back gracefully so the app can still start. Search will use LIKE.
        """
        try:
            row = self.cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='notes_fts'"
            ).fetchone()
            sql = row[0] if row else ''
            is_external = sql and "content='notes'" in sql.replace('"', "'")

            if row and not is_external:
                self.cursor.execute('DROP TABLE notes_fts')
                row = None

            if not row:
                self.cursor.execute('''
                    CREATE VIRTUAL TABLE notes_fts
                    USING fts5(
                        title,
                        content,
                        content='notes',
                        content_rowid='id'
                    )
                ''')

            self.cursor.execute('DROP TRIGGER IF EXISTS notes_ai')
            self.cursor.execute('DROP TRIGGER IF EXISTS notes_ad')
            self.cursor.execute('DROP TRIGGER IF EXISTS notes_au')

            self.cursor.execute('''
                CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
                    INSERT INTO notes_fts(rowid, title, content)
                    VALUES (new.id, new.title, new.content);
                END
            ''')
            self.cursor.execute('''
                CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, title, content)
                    VALUES ('delete', old.id, old.title, old.content);
                END
            ''')
            self.cursor.execute('''
                CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, title, content)
                    VALUES ('delete', old.id, old.title, old.content);
                    INSERT INTO notes_fts(rowid, title, content)
                    VALUES (new.id, new.title, new.content);
                END
            ''')

            self.cursor.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
            self.fts_available = True
        except sqlite3.OperationalError as exc:
            # Typical on Android when the sqlite3 recipe was built without FTS5.
            if 'fts5' in str(exc).lower() or 'no such module' in str(exc).lower():
                self.fts_available = False
                # Drop triggers first (they may reference the missing module),
                # then the table. Each statement is independent so one failure
                # does not prevent the others.
                for stmt in (
                    'DROP TRIGGER IF EXISTS notes_ai',
                    'DROP TRIGGER IF EXISTS notes_ad',
                    'DROP TRIGGER IF EXISTS notes_au',
                    'DROP TABLE IF EXISTS notes_fts',
                ):
                    try:
                        self.cursor.execute(stmt)
                    except sqlite3.Error:
                        pass
            else:
                raise

    def execute(self, query, params=None):
        if params is not None:
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def get_timestamp(self):
        return datetime.now().isoformat(timespec='seconds')
