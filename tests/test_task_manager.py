def test_create_and_get_task(tasks):
    task_id = tasks.create_task('Buy milk', '2%', due_date='2026-09-01')
    task = tasks.get_task(task_id)
    assert task.title == 'Buy milk'
    assert task.description == '2%'
    assert task.completed in (0, False)
    assert task.due_date == '2026-09-01'


def test_get_missing_task_returns_none(tasks):
    assert tasks.get_task(999) is None


def test_update_task_fields(tasks):
    task_id = tasks.create_task('Old')
    tasks.update_task(task_id, title='New', description='details', due_date='2026-10-01')
    task = tasks.get_task(task_id)
    assert task.title == 'New'
    assert task.description == 'details'
    assert task.due_date == '2026-10-01'


def test_toggle_task(tasks):
    task_id = tasks.create_task('Toggle me')
    tasks.toggle_task(task_id)
    assert tasks.get_task(task_id).completed
    tasks.toggle_task(task_id)
    assert not tasks.get_task(task_id).completed


def test_toggle_missing_task_is_safe(tasks):
    tasks.toggle_task(999)


def test_delete_task(tasks):
    task_id = tasks.create_task('Remove')
    tasks.delete_task(task_id)
    assert tasks.get_task(task_id) is None


def test_get_all_tasks_hides_completed_when_asked(tasks):
    open_id = tasks.create_task('Open')
    done_id = tasks.create_task('Done')
    tasks.update_task(done_id, completed=1)
    all_tasks = tasks.get_all_tasks(include_completed=True)
    open_only = tasks.get_all_tasks(include_completed=False)
    assert {t.id for t in all_tasks} == {open_id, done_id}
    assert [t.id for t in open_only] == [open_id]


def test_get_all_tasks_filters_by_folder(tasks, folders):
    home = folders.create_folder('Home')
    tasks.create_task('In folder', folder_id=home)
    tasks.create_task('Unfiled')
    assert [t.title for t in tasks.get_all_tasks(folder_id=home)] == ['In folder']
    assert [t.title for t in tasks.get_all_tasks(unfiled_only=True)] == ['Unfiled']
    titles = [t.title for t in tasks.get_all_tasks()]
    assert set(titles) == {'In folder', 'Unfiled'}


def test_get_all_tasks_folder_and_hide_completed(tasks, folders):
    home = folders.create_folder('Home')
    open_id = tasks.create_task('Still open', folder_id=home)
    done_id = tasks.create_task('Finished', folder_id=home)
    tasks.update_task(done_id, completed=1)
    visible = tasks.get_all_tasks(folder_id=home, include_completed=False)
    assert [t.id for t in visible] == [open_id]
