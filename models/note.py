"""
Note Model and Manager
Handles all note-related operations
"""


class Note:
    """Represents a single note."""

    def __init__(
        self,
        id=None,
        title='',
        content='',
        folder_id=None,
        created_at=None,
        updated_at=None,
    ):
        self.id = id
        self.title = title
        self.content = content  # Rich text stored as BBCode markup
        self.folder_id = folder_id
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            folder_id=row['folder_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'folder_id': self.folder_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class NoteManager:
    """Manages note operations. FTS is kept in sync by database triggers."""

    def __init__(self, db_manager):
        self.db = db_manager

    def create_note(self, title, content='', folder_id=None):
        timestamp = self.db.get_timestamp()
        self.db.execute(
            '''
            INSERT INTO notes (title, content, folder_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (title, content, folder_id, timestamp, timestamp),
        )
        note_id = self.db.cursor.lastrowid
        self.db.commit()
        return note_id

    def get_note(self, note_id):
        self.db.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
        row = self.db.fetchone()
        return Note.from_db_row(row) if row else None

    def update_note(self, note_id, title=None, content=None, folder_id=None):
        timestamp = self.db.get_timestamp()
        updates = []
        params = []

        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if content is not None:
            updates.append('content = ?')
            params.append(content)
        if folder_id is not None:
            updates.append('folder_id = ?')
            params.append(folder_id)

        if not updates:
            return

        updates.append('updated_at = ?')
        params.append(timestamp)
        params.append(note_id)

        query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, params)
        self.db.commit()

    def move_note(self, note_id, folder_id):
        """Move a note into a folder, or to Home when folder_id is None."""
        timestamp = self.db.get_timestamp()
        self.db.execute(
            'UPDATE notes SET folder_id = ?, updated_at = ? WHERE id = ?',
            (folder_id, timestamp, note_id),
        )
        self.db.commit()

    def delete_note(self, note_id):
        self.db.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        self.db.commit()

    def get_all_notes(self, folder_id=None):
        """Notes in one folder. folder_id=None means unfiled (root), not every note."""
        if folder_id is not None:
            self.db.execute(
                '''
                SELECT * FROM notes
                WHERE folder_id = ?
                ORDER BY updated_at DESC
                ''',
                (folder_id,),
            )
        else:
            self.db.execute(
                '''
                SELECT * FROM notes
                WHERE folder_id IS NULL
                ORDER BY updated_at DESC
                '''
            )
        rows = self.db.fetchall()
        return [Note.from_db_row(row) for row in rows]

    @staticmethod
    def _fts_phrase(query):
        """Treat user input as a phrase so hyphens/operators are not FTS syntax."""
        cleaned = query.strip().replace('"', '""')
        return f'"{cleaned}"'

    def search_notes(self, query, tag_id=None):
        if tag_id is not None and (not query or not str(query).strip()):
            self.db.execute(
                '''
                SELECT notes.* FROM notes
                JOIN note_tags ON notes.id = note_tags.note_id
                WHERE note_tags.tag_id = ?
                ORDER BY notes.updated_at DESC
                ''',
                (tag_id,),
            )
            return [Note.from_db_row(row) for row in self.db.fetchall()]

        if not query or not str(query).strip():
            return []

        raw = str(query).strip()
        tag_names = []
        leftover = []
        for token in raw.split():
            if token.startswith('#') and len(token) > 1:
                tag_names.append(token.lstrip('#'))
            else:
                leftover.append(token)
        phrase = ' '.join(leftover).strip()

        if tag_names and not phrase:
            placeholders = ','.join('?' * len(tag_names))
            lowered = [name.lower() for name in tag_names]
            self.db.execute(
                f'''
                SELECT DISTINCT notes.* FROM notes
                JOIN note_tags ON notes.id = note_tags.note_id
                JOIN tags ON tags.id = note_tags.tag_id
                WHERE lower(tags.name) IN ({placeholders})
                ORDER BY notes.updated_at DESC
                ''',
                lowered,
            )
            return [Note.from_db_row(row) for row in self.db.fetchall()]

        try:
            if getattr(self.db, 'fts_available', True):
                sql = '''
                    SELECT DISTINCT notes.* FROM notes
                    JOIN notes_fts ON notes.id = notes_fts.rowid
                    WHERE notes_fts MATCH ?
                '''
                params = [self._fts_phrase(phrase or raw)]
                if tag_id is not None:
                    sql += '''
                        AND notes.id IN (SELECT note_id FROM note_tags WHERE tag_id = ?)
                    '''
                    params.append(tag_id)
                if tag_names:
                    placeholders = ','.join('?' * len(tag_names))
                    sql += f'''
                        AND notes.id IN (
                            SELECT note_id FROM note_tags
                            JOIN tags ON tags.id = note_tags.tag_id
                            WHERE lower(tags.name) IN ({placeholders})
                        )
                    '''
                    params.extend(name.lower() for name in tag_names)
                sql += ' ORDER BY rank'
                self.db.execute(sql, params)
            else:
                # Fallback when FTS5 is unavailable (e.g. some Android builds)
                like = f'%{(phrase or raw).replace("%", "").replace("_", "")}%'
                sql = '''
                    SELECT DISTINCT notes.* FROM notes
                    WHERE (title LIKE ? OR content LIKE ?)
                '''
                params = [like, like]
                if tag_id is not None:
                    sql += '''
                        AND notes.id IN (SELECT note_id FROM note_tags WHERE tag_id = ?)
                    '''
                    params.append(tag_id)
                if tag_names:
                    placeholders = ','.join('?' * len(tag_names))
                    sql += f'''
                        AND notes.id IN (
                            SELECT note_id FROM note_tags
                            JOIN tags ON tags.id = note_tags.tag_id
                            WHERE lower(tags.name) IN ({placeholders})
                        )
                    '''
                    params.extend(name.lower() for name in tag_names)
                sql += ' ORDER BY updated_at DESC'
                self.db.execute(sql, params)
        except Exception:
            return []
        rows = self.db.fetchall()
        return [Note.from_db_row(row) for row in rows]

    @staticmethod
    def preview_text(content, limit=90):
        import re

        text = re.sub(r'\[/?[biu]\]', '', content or '')
        text = text.replace('☐', '•').replace('☑', '✓')
        text = ' '.join(text.split())
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + '…'
