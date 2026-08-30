def test_rename_note(notes):
    note_id = notes.create_note('Old title', 'body')
    notes.update_note(note_id, title='New title')
    assert notes.get_note(note_id).title == 'New title'


def test_rename_folder(folders):
    folder_id = folders.create_folder('Old')
    folders.update_folder(folder_id, name='New')
    assert folders.get_folder(folder_id).name == 'New'


def test_move_note_into_folder_and_back(notes, folders):
    work = folders.create_folder('Work')
    note_id = notes.create_note('Spec', 'body')
    assert notes.get_all_notes()[0].id == note_id
    notes.move_note(note_id, work)
    assert notes.get_all_notes() == []
    assert notes.get_all_notes(folder_id=work)[0].id == note_id
    notes.move_note(note_id, None)
    assert notes.get_note(note_id).folder_id is None
    assert notes.get_all_notes()[0].id == note_id
