"""Tags: many-to-many labels on notes."""


class Tag:
    def __init__(self, id=None, name='', created_at=None):
        self.id = id
        self.name = name
        self.created_at = created_at

    @classmethod
    def from_db_row(cls, row):
        return cls(id=row['id'], name=row['name'], created_at=row['created_at'])

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'created_at': self.created_at}


class TagManager:
    def __init__(self, db_manager):
        self.db = db_manager

    @staticmethod
    def normalize(name):
        raw = (name or '').strip().lstrip('#')
        return ' '.join(raw.split())

    def get_or_create(self, name):
        clean = self.normalize(name)
        if not clean:
            return None
        existing = self.get_by_name(clean)
        if existing:
            return existing.id
        timestamp = self.db.get_timestamp()
        self.db.execute(
            'INSERT INTO tags (name, created_at) VALUES (?, ?)',
            (clean, timestamp),
        )
        self.db.commit()
        return self.db.cursor.lastrowid

    def get_by_name(self, name):
        clean = self.normalize(name)
        if not clean:
            return None
        self.db.execute('SELECT * FROM tags WHERE name = ? COLLATE NOCASE', (clean,))
        row = self.db.fetchone()
        return Tag.from_db_row(row) if row else None

    def get_tag(self, tag_id):
        self.db.execute('SELECT * FROM tags WHERE id = ?', (tag_id,))
        row = self.db.fetchone()
        return Tag.from_db_row(row) if row else None

    def get_all_tags(self):
        self.db.execute('SELECT * FROM tags ORDER BY name COLLATE NOCASE')
        return [Tag.from_db_row(row) for row in self.db.fetchall()]

    def rename_tag(self, tag_id, name):
        clean = self.normalize(name)
        if not clean:
            return False
        other = self.get_by_name(clean)
        if other and other.id != tag_id:
            return False
        self.db.execute('UPDATE tags SET name = ? WHERE id = ?', (clean, tag_id))
        self.db.commit()
        return True

    def delete_tag(self, tag_id):
        self.db.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
        self.db.commit()

    def set_note_tags(self, note_id, names):
        seen = []
        ids = []
        for name in names or []:
            clean = self.normalize(name)
            if not clean or clean.lower() in seen:
                continue
            seen.append(clean.lower())
            tag_id = self.get_or_create(clean)
            if tag_id:
                ids.append(tag_id)
        self.db.execute('DELETE FROM note_tags WHERE note_id = ?', (note_id,))
        for tag_id in ids:
            self.db.execute(
                'INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)',
                (note_id, tag_id),
            )
        self.db.commit()
        return ids

    def add_tag_to_note(self, note_id, name):
        tag_id = self.get_or_create(name)
        if not tag_id:
            return None
        self.db.execute(
            'INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)',
            (note_id, tag_id),
        )
        self.db.commit()
        return tag_id

    def remove_tag_from_note(self, note_id, tag_id):
        self.db.execute(
            'DELETE FROM note_tags WHERE note_id = ? AND tag_id = ?',
            (note_id, tag_id),
        )
        self.db.commit()

    def get_note_tags(self, note_id):
        self.db.execute(
            '''
            SELECT tags.* FROM tags
            JOIN note_tags ON tags.id = note_tags.tag_id
            WHERE note_tags.note_id = ?
            ORDER BY tags.name COLLATE NOCASE
            ''',
            (note_id,),
        )
        return [Tag.from_db_row(row) for row in self.db.fetchall()]

    def get_notes_for_tag(self, tag_id):
        self.db.execute(
            '''
            SELECT notes.* FROM notes
            JOIN note_tags ON notes.id = note_tags.note_id
            WHERE note_tags.tag_id = ?
            ORDER BY notes.updated_at DESC
            ''',
            (tag_id,),
        )
        from models.note import Note

        return [Note.from_db_row(row) for row in self.db.fetchall()]
