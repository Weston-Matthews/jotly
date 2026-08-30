import os
import zipfile

from models.attachment import AttachmentManager
from models.backup import BackupManager
from models.capture import CaptureService
from models.tag import TagManager


def _stack(db, tmp_path):
    from models.folder import FolderManager
    from models.note import NoteManager
    from models.task import TaskManager

    notes = NoteManager(db)
    tasks = TaskManager(db)
    folders = FolderManager(db)
    tags = TagManager(db)
    attachments = AttachmentManager(db, str(tmp_path / 'attachments'))
    capture = CaptureService(notes, tags, attachments)
    backup = BackupManager(db, folders, notes, tasks, tags, attachments)
    return notes, tasks, folders, tags, attachments, capture, backup


def test_tags_round_trip(db):
    tags = TagManager(db)
    from models.note import NoteManager

    notes = NoteManager(db)
    note_id = notes.create_note('Recipe', 'pasta')
    tags.set_note_tags(note_id, ['Dinner', '#dinner', 'italian', ''])
    names = [t.name for t in tags.get_note_tags(note_id)]
    assert names == ['Dinner', 'italian']
    tags.add_tag_to_note(note_id, 'quick')
    tags.remove_tag_from_note(note_id, tags.get_by_name('italian').id)
    assert [t.name for t in tags.get_note_tags(note_id)] == ['Dinner', 'quick']


def test_search_by_hash_tag(db):
    from models.note import NoteManager

    notes = NoteManager(db)
    tags = TagManager(db)
    one = notes.create_note('Tomato soup', 'comfort food')
    notes.create_note('Unrelated', 'office wifi')
    tags.set_note_tags(one, ['recipes'])
    found = notes.search_notes('#recipes')
    assert [n.title for n in found] == ['Tomato soup']
    found = notes.search_notes('#recipes comfort')
    assert [n.title for n in found] == ['Tomato soup']


def test_capture_url_and_text(db, tmp_path):
    notes, _tasks, _folders, tags, _att, capture, _backup = _stack(db, tmp_path)
    url_id = capture.capture_text('https://example.com/weeknight-pasta')
    note = notes.get_note(url_id)
    assert 'example.com' in note.title
    assert note.content.startswith('https://')
    assert 'clip' in [t.name for t in tags.get_note_tags(url_id)]

    text_id = capture.capture_text('Buy oat milk\nsecond line')
    note = notes.get_note(text_id)
    assert note.title == 'Buy oat milk'


def test_capture_file_and_backup(db, tmp_path):
    notes, tasks, folders, tags, attachments, capture, backup = _stack(db, tmp_path)
    work = folders.create_folder('Work')
    src = tmp_path / 'receipt.jpg'
    src.write_bytes(b'\xff\xd8fake-jpeg')
    note_id = capture.capture_file(str(src), folder_id=work, extra_text='Lunch')
    items = attachments.list_for_note(note_id)
    assert len(items) == 1
    assert items[0].kind == 'image'
    assert os.path.isfile(attachments.path_for(items[0]))

    tasks.create_task('Call bank', folder_id=work, due_date='2026-09-01')
    archive = tmp_path / 'backup.zip'
    backup.export_archive(str(archive))
    assert zipfile.is_zipfile(archive)

    from database.db_manager import DatabaseManager

    fresh = DatabaseManager(':memory:')
    other = _stack(fresh, tmp_path / 'other')
    counts = other[6].import_archive(str(archive))
    assert counts['notes'] == 1
    assert counts['tasks'] == 1
    assert counts['attachments'] == 1
    imported = other[0].get_all_notes(folder_id=other[2].get_all_folders()[0].id)
    assert imported[0].title
    assert other[4].list_for_note(imported[0].id)


def test_preview_strips_markup():
    from models.note import NoteManager

    text = NoteManager.preview_text('[b]Hello[/b]   world\n☐ milk')
    assert '[' not in text
    assert text.startswith('Hello world')
