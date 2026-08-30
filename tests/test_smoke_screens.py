"""
Headless desktop smoke of the three Kivy screens.

Requires a window provider. In CI/sandbox use:
  SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 python3 -m pytest tests/test_smoke_screens.py -v
"""

import os
import tempfile

import pytest

# Force an offscreen window before Kivy binds a display.
os.environ.setdefault('KIVY_NO_ARGS', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'offscreen')
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')

from kivy.clock import Clock

from main import JotlyApp


class SmokeApp(JotlyApp):
    def __init__(self, data_dir, **kwargs):
        self._smoke_dir = data_dir
        super().__init__(**kwargs)

    @property
    def user_data_dir(self):
        return self._smoke_dir


def _button_texts(widget, acc=None):
    from kivy.uix.button import Button

    if acc is None:
        acc = []
    if isinstance(widget, Button):
        acc.append(widget.text)
    for child in getattr(widget, 'children', []):
        _button_texts(child, acc)
    return acc


def _label_texts(widget, acc=None):
    from kivy.uix.label import Label

    if acc is None:
        acc = []
    if isinstance(widget, Label):
        acc.append(widget.text)
    for child in getattr(widget, 'children', []):
        _label_texts(child, acc)
    return acc


def test_three_screens_smoke():
    data_dir = tempfile.mkdtemp(prefix='jotly-smoke-')
    app = SmokeApp(data_dir)
    errors = []

    def fail(msg):
        errors.append(msg)

    def step(_dt):
        try:
            sm = app.root
            main = sm.get_screen('main')
            editor = sm.get_screen('note_editor')
            tasks = sm.get_screen('task_list')

            assert sm.current == 'main'
            main.refresh_content()
            texts = _button_texts(main) + _label_texts(main)
            if 'Jotly' not in texts:
                fail(f'main screen missing title, got {texts[:8]}')
            if '+ Note' not in texts or '+ Task' not in texts or '+ Folder' not in texts:
                fail(f'main screen missing action buttons: {texts}')

            app.folder_manager.create_folder('New Folder')
            main.refresh_content()
            if not any('New Folder' in t for t in _button_texts(main)):
                fail('creating a folder did not show it on main')

            created_folders = app.folder_manager.get_all_folders()
            if not created_folders:
                fail('folder manager has no root folders after + Folder')
            else:
                folder = created_folders[0]
                main.open_folder(folder)
                if main.current_folder != folder.id:
                    fail('open_folder did not enter the folder')
                if main.breadcrumb.text == 'Home':
                    fail('breadcrumb still Home after entering folder')
                main.create_new_note(None)
                if editor.current_note is not None:
                    editor.title_input.text = 'Filed Note'
                    editor.editor.set_text('inside folder')
                    editor.go_back(None)
                main.go_up()
                if main.current_folder is not None:
                    fail('go_up did not return to Home')
                main.refresh_content()
                if any('Filed Note' in t for t in _button_texts(main)):
                    fail('filed note leaked onto Home')
                main.open_folder(folder)
                if not any('Filed Note' in t for t in _button_texts(main)):
                    fail('filed note missing inside folder')
                main.go_up()

            main.create_new_note(None)
            if sm.current != 'note_editor':
                fail(f'expected note_editor after + Note, got {sm.current}')

            if editor.current_note is None:
                fail('editor has no current_note after create')
            else:
                editor.title_input.text = 'Smoke Note'
                editor.editor.set_text('hello [b]world[/b]')
                editor.save_note(None)
                saved = app.note_manager.get_note(editor.current_note.id)
                if saved.title != 'Smoke Note':
                    fail(f'save did not persist title, got {saved.title!r}')
                if 'world' not in (saved.content or ''):
                    fail(f'save did not persist content, got {saved.content!r}')

            editor.go_back(None)
            if sm.current != 'main':
                fail(f'expected main after editor back, got {sm.current}')
            main.refresh_content()
            if not any('Smoke Note' in t for t in _button_texts(main)):
                fail(f'saved note missing from main list: {_button_texts(main)}')

            main.search_input.text = 'Smoke'
            main.search_notes(None)
            if not any('Smoke Note' in t for t in _button_texts(main)):
                fail('search did not find Smoke Note')

            main.search_input.text = 'zzzz-no-match'
            main.search_notes(None)
            labels = _label_texts(main)
            if 'No results found' not in labels:
                fail(f'empty search should show no-results, labels={labels}')

            main.search_input.text = ''
            main.refresh_content()
            main.create_new_task(None)
            if not any('New Task' in t for t in _button_texts(main)):
                fail('creating a task did not show it on main')

            main.open_task(None)
            if sm.current != 'task_list':
                fail(f'expected task_list, got {sm.current}')
            tasks.refresh_tasks()
            task_labels = _label_texts(tasks)
            if not any('New Task' in t for t in task_labels):
                fail(f'task list missing New Task: {task_labels}')

            created = app.task_manager.get_all_tasks()
            if not created:
                fail('no tasks in manager after UI create')
            else:
                tasks.toggle_task(created[0], True)
                again = app.task_manager.get_task(created[0].id)
                if not again.completed:
                    fail('toggle from task list did not persist')
                tasks.delete_task(created[0])
                if app.task_manager.get_task(created[0].id) is not None:
                    fail('delete from task list did not persist')

            tasks.create_task(None)
            if not app.task_manager.get_all_tasks():
                fail('+ New Task on task list did not create a row')

            tasks.go_back(None)
            if sm.current != 'main':
                fail(f'expected main after task list back, got {sm.current}')
        except Exception as exc:
            fail(f'unhandled: {type(exc).__name__}: {exc}')
        finally:
            app.stop()

    Clock.schedule_once(step, 0)
    app.run()

    assert not errors, 'Smoke failures:\n- ' + '\n- '.join(errors)
