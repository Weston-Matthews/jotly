"""Export and import a portable Jotly archive (zip + JSON + files)."""

import json
import os
import shutil
import tempfile
import zipfile


ARCHIVE_VERSION = 1


class BackupManager:
    def __init__(self, db_manager, folder_manager, note_manager, task_manager, tag_manager, attachment_manager):
        self.db = db_manager
        self.folders = folder_manager
        self.notes = note_manager
        self.tasks = task_manager
        self.tags = tag_manager
        self.attachments = attachment_manager

    def _all_folders(self):
        self.db.execute('SELECT * FROM folders ORDER BY id')
        from models.folder import Folder

        return [Folder.from_db_row(row) for row in self.db.fetchall()]

    def _all_notes(self):
        self.db.execute('SELECT * FROM notes ORDER BY id')
        from models.note import Note

        return [Note.from_db_row(row) for row in self.db.fetchall()]

    def export_archive(self, dest_path):
        payload = {
            'version': ARCHIVE_VERSION,
            'exported_at': self.db.get_timestamp(),
            'folders': [f.to_dict() for f in self._all_folders()],
            'notes': [],
            'tasks': [t.to_dict() for t in self.tasks.get_all_tasks()],
            'tags': [t.to_dict() for t in self.tags.get_all_tags()],
        }
        for note in self._all_notes():
            item = note.to_dict()
            item['tags'] = [t.name for t in self.tags.get_note_tags(note.id)]
            item['attachments'] = [a.to_dict() for a in self.attachments.list_for_note(note.id)]
            payload['notes'].append(item)

        os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or '.', exist_ok=True)
        with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('jotly.json', json.dumps(payload, indent=2))
            for note in payload['notes']:
                for att in note['attachments']:
                    src = os.path.join(
                        self.attachments.root_dir,
                        str(note['id']),
                        att['stored_name'],
                    )
                    if os.path.isfile(src):
                        zf.write(
                            src,
                            arcname=f"attachments/{note['id']}/{att['stored_name']}",
                        )
        return dest_path

    def import_archive(self, src_path):
        if not src_path or not zipfile.is_zipfile(src_path):
            raise ValueError('Not a Jotly archive')

        tmp = tempfile.mkdtemp(prefix='jotly-import-')
        try:
            with zipfile.ZipFile(src_path, 'r') as zf:
                zf.extractall(tmp)
            data_path = os.path.join(tmp, 'jotly.json')
            if not os.path.isfile(data_path):
                raise ValueError('Archive is missing jotly.json')
            with open(data_path, encoding='utf-8') as handle:
                payload = json.load(handle)
            return self._load_payload(payload, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _load_payload(self, payload, unpacked_dir):
        folder_map = {}
        pending = list(payload.get('folders') or [])
        guard = 0
        while pending and guard < 10_000:
            guard += 1
            folder = pending.pop(0)
            old_parent = folder.get('parent_id')
            if old_parent is not None and old_parent not in folder_map:
                pending.append(folder)
                continue
            new_parent = folder_map.get(old_parent) if old_parent is not None else None
            new_id = self.folders.create_folder(folder.get('name') or 'Folder', new_parent)
            folder_map[folder['id']] = new_id

        counts = {'folders': len(folder_map), 'notes': 0, 'tasks': 0, 'tags': 0, 'attachments': 0}

        for raw in payload.get('notes') or []:
            folder_id = raw.get('folder_id')
            mapped_folder = folder_map.get(folder_id) if folder_id is not None else None
            note_id = self.notes.create_note(
                raw.get('title') or 'Untitled Note',
                raw.get('content') or '',
                mapped_folder,
            )
            self.tags.set_note_tags(note_id, raw.get('tags') or [])
            counts['notes'] += 1
            for att in raw.get('attachments') or []:
                stored = att.get('stored_name')
                src = os.path.join(
                    unpacked_dir,
                    'attachments',
                    str(raw.get('id')),
                    stored or '',
                )
                if os.path.isfile(src):
                    self.attachments.attach_file(
                        note_id, src, filename=att.get('filename') or stored
                    )
                    counts['attachments'] += 1

        for raw in payload.get('tasks') or []:
            folder_id = raw.get('folder_id')
            mapped_folder = folder_map.get(folder_id) if folder_id is not None else None
            task_id = self.tasks.create_task(
                raw.get('title') or 'Task',
                raw.get('description') or '',
                mapped_folder,
                due_date=raw.get('due_date'),
                starred=bool(raw.get('starred')),
            )
            if raw.get('completed'):
                self.tasks.update_task(task_id, completed=True)
            counts['tasks'] += 1

        counts['tags'] = len(self.tags.get_all_tags())
        return counts
