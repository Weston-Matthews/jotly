def test_create_and_get_folder(folders):
    folder_id = folders.create_folder('Work')
    folder = folders.get_folder(folder_id)
    assert folder.name == 'Work'
    assert folder.parent_id is None


def test_get_missing_folder_returns_none(folders):
    assert folders.get_folder(999) is None


def test_update_folder_renames(folders):
    folder_id = folders.create_folder('Old')
    folders.update_folder(folder_id, name='New')
    assert folders.get_folder(folder_id).name == 'New'


def test_update_folder_noop_when_no_fields(folders):
    folder_id = folders.create_folder('Same')
    before = folders.get_folder(folder_id)
    folders.update_folder(folder_id)
    after = folders.get_folder(folder_id)
    assert after.name == before.name
    assert after.updated_at == before.updated_at


def test_nested_folders_and_path(folders):
    root = folders.create_folder('Work')
    child = folders.create_folder('Client A', parent_id=root)
    leaf = folders.create_folder('Invoices', parent_id=child)
    path = folders.get_folder_path(leaf)
    assert [f.name for f in path] == ['Work', 'Client A', 'Invoices']


def test_get_all_folders_roots_and_children(folders):
    work = folders.create_folder('Work')
    home = folders.create_folder('Home')
    folders.create_folder('Nested', parent_id=work)
    roots = folders.get_all_folders()
    assert {f.name for f in roots} == {'Work', 'Home'}
    children = folders.get_all_folders(parent_id=work)
    assert [f.name for f in children] == ['Nested']
    assert home in {f.id for f in roots}


def test_delete_folder_cascades_children(folders):
    root = folders.create_folder('Work')
    child = folders.create_folder('Nested', parent_id=root)
    folders.delete_folder(root)
    assert folders.get_folder(root) is None
    assert folders.get_folder(child) is None


def test_delete_folder_nulls_notes_and_tasks(folders, notes, tasks):
    folder_id = folders.create_folder('Work')
    note_id = notes.create_note('Spec', 'body', folder_id=folder_id)
    task_id = tasks.create_task('Ship it', folder_id=folder_id)
    folders.delete_folder(folder_id)
    assert notes.get_note(note_id).folder_id is None
    assert tasks.get_task(task_id).folder_id is None
