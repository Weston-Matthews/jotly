def test_due_date_round_trip(tasks):
    task_id = tasks.create_task('Pay rent', due_date='2026-09-01')
    assert tasks.get_task(task_id).due_date == '2026-09-01'
    tasks.update_task(task_id, due_date='2026-09-15')
    assert tasks.get_task(task_id).due_date == '2026-09-15'
    tasks.update_task(task_id, due_date='')
    assert tasks.get_task(task_id).due_date is None


def test_star_floats_to_top(tasks):
    first = tasks.create_task('Later')
    second = tasks.create_task('Urgent')
    tasks.toggle_star(second)
    titles = [t.title for t in tasks.get_all_tasks()]
    assert titles[0] == 'Urgent'
    assert tasks.get_task(second).starred
    assert not tasks.get_task(first).starred


def test_reorder_tasks_persists(tasks):
    a = tasks.create_task('A')
    b = tasks.create_task('B')
    c = tasks.create_task('C')
    tasks.reorder_tasks([c, a, b])
    assert [t.title for t in tasks.get_all_tasks()] == ['C', 'A', 'B']


def test_starred_stays_above_reorder(tasks):
    a = tasks.create_task('A')
    b = tasks.create_task('B')
    tasks.toggle_star(a)
    tasks.reorder_tasks([b, a])
    titles = [t.title for t in tasks.get_all_tasks()]
    assert titles[0] == 'A'


def test_per_folder_task_isolation(tasks, folders):
    work = folders.create_folder('Work')
    home = folders.create_folder('Home')
    tasks.create_task('Work item', folder_id=work)
    tasks.create_task('Home item', folder_id=home)
    tasks.create_task('Loose')
    assert [t.title for t in tasks.get_all_tasks(folder_id=work)] == ['Work item']
    assert [t.title for t in tasks.get_all_tasks(folder_id=home)] == ['Home item']
    assert [t.title for t in tasks.get_all_tasks(unfiled_only=True)] == ['Loose']
