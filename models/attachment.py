"""File attachments stored next to the database."""

import os
import shutil
import uuid


class Attachment:
    def __init__(
        self,
        id=None,
        note_id=None,
        kind='file',
        filename='',
        stored_name='',
        mime='',
        created_at=None,
    ):
        self.id = id
        self.note_id = note_id
        self.kind = kind
        self.filename = filename
        self.stored_name = stored_name
        self.mime = mime or ''
        self.created_at = created_at

    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            note_id=row['note_id'],
            kind=row['kind'],
            filename=row['filename'],
            stored_name=row['stored_name'],
            mime=row['mime'],
            created_at=row['created_at'],
        )

    def to_dict(self):
        return {
            'id': self.id,
            'note_id': self.note_id,
            'kind': self.kind,
            'filename': self.filename,
            'stored_name': self.stored_name,
            'mime': self.mime,
            'created_at': self.created_at,
        }


class AttachmentManager:
    IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}

    def __init__(self, db_manager, root_dir):
        self.db = db_manager
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def note_dir(self, note_id):
        path = os.path.join(self.root_dir, str(note_id))
        os.makedirs(path, exist_ok=True)
        return path

    def path_for(self, attachment):
        return os.path.join(self.root_dir, str(attachment.note_id), attachment.stored_name)

    def _kind_for(self, filename):
        ext = os.path.splitext(filename or '')[1].lower()
        return 'image' if ext in self.IMAGE_EXTS else 'file'

    def attach_file(self, note_id, src_path, filename=None):
        if not src_path or not os.path.isfile(src_path):
            return None
        original = filename or os.path.basename(src_path)
        ext = os.path.splitext(original)[1]
        stored = f'{uuid.uuid4().hex}{ext}'
        dest = os.path.join(self.note_dir(note_id), stored)
        shutil.copy2(src_path, dest)
        kind = self._kind_for(original)
        timestamp = self.db.get_timestamp()
        self.db.execute(
            '''
            INSERT INTO attachments (note_id, kind, filename, stored_name, mime, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (note_id, kind, original, stored, ext.lstrip('.'), timestamp),
        )
        self.db.commit()
        return self.db.cursor.lastrowid

    def attach_bytes(self, note_id, data, filename):
        if data is None:
            return None
        original = filename or 'clip.bin'
        ext = os.path.splitext(original)[1]
        stored = f'{uuid.uuid4().hex}{ext}'
        dest = os.path.join(self.note_dir(note_id), stored)
        with open(dest, 'wb') as handle:
            handle.write(data)
        kind = self._kind_for(original)
        timestamp = self.db.get_timestamp()
        self.db.execute(
            '''
            INSERT INTO attachments (note_id, kind, filename, stored_name, mime, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (note_id, kind, original, stored, ext.lstrip('.'), timestamp),
        )
        self.db.commit()
        return self.db.cursor.lastrowid

    def get_attachment(self, attachment_id):
        self.db.execute('SELECT * FROM attachments WHERE id = ?', (attachment_id,))
        row = self.db.fetchone()
        return Attachment.from_db_row(row) if row else None

    def list_for_note(self, note_id):
        self.db.execute(
            'SELECT * FROM attachments WHERE note_id = ? ORDER BY created_at ASC, id ASC',
            (note_id,),
        )
        return [Attachment.from_db_row(row) for row in self.db.fetchall()]

    def delete_attachment(self, attachment_id):
        item = self.get_attachment(attachment_id)
        if not item:
            return
        path = self.path_for(item)
        self.db.execute('DELETE FROM attachments WHERE id = ?', (attachment_id,))
        self.db.commit()
        if os.path.isfile(path):
            os.remove(path)

    def delete_for_note(self, note_id):
        for item in self.list_for_note(note_id):
            path = self.path_for(item)
            if os.path.isfile(path):
                os.remove(path)
        folder = os.path.join(self.root_dir, str(note_id))
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
        self.db.execute('DELETE FROM attachments WHERE note_id = ?', (note_id,))
        self.db.commit()
