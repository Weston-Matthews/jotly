"""Task Editor - every task field on one screen."""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from ui.theme import ACCENT, MUTED, TEXT, FlatButton, FlatInput, switch_screen
from ui.widgets.date_picker import pick_date
from ui.widgets.folder_picker import pick_folder


class TaskEditorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task = None          # None while creating a brand-new task
        self.folder_id = None
        self.due_date = None
        self.starred = False
        self.return_to = 'main'
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        top = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        top.add_widget(FlatButton(text='← Back', kind='neutral', on_release=self.go_back))
        self.save_btn = FlatButton(text='Save', kind='primary', on_release=self.save_and_close)
        top.add_widget(self.save_btn)
        self.delete_btn = FlatButton(text='Delete', kind='danger', on_release=self.delete_task)
        top.add_widget(self.delete_btn)
        root.add_widget(top)

        self.title_input = FlatInput(
            hint_text='What needs doing?',
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size='20sp',
        )
        self.title_input.bind(on_text_validate=lambda *_: self.save_and_close())
        root.add_widget(self.title_input)

        opts = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.done_box = CheckBox(size_hint_x=None, width=dp(40), color=ACCENT)
        opts.add_widget(self.done_box)
        opts.add_widget(Label(text='Done', color=TEXT, size_hint_x=None, width=dp(48)))
        self.star_btn = FlatButton(text='☆ Priority', kind='ghost', on_release=self.toggle_star)
        opts.add_widget(self.star_btn)
        self.due_btn = FlatButton(text='Due date', kind='ghost', on_release=self.pick_due)
        opts.add_widget(self.due_btn)
        root.add_widget(opts)

        self.folder_btn = FlatButton(
            text='Folder: Home', kind='folder', size_hint_y=None, height=dp(44),
            on_release=self.pick_folder,
        )
        root.add_widget(self.folder_btn)

        root.add_widget(Label(text='Notes', color=MUTED, size_hint_y=None, height=dp(20),
                              halign='left', text_size=(None, None)))
        self.desc_input = FlatInput(hint_text='Details (optional)', multiline=True)
        root.add_widget(self.desc_input)
        self.add_widget(root)

    # --- entry points -------------------------------------------------
    def new_task(self, folder_id, return_to='main'):
        self.task = None
        self._load('', '', False, folder_id, None, False, return_to)

    def edit_task(self, task, return_to='main'):
        self.task = task
        self._load(task.title, task.description or '', task.completed,
                   task.folder_id, task.due_date, task.starred, return_to)

    def _load(self, title, desc, done, folder_id, due, starred, return_to):
        self.return_to = return_to
        self.title_input.text = title
        self.desc_input.text = desc
        self.done_box.active = bool(done)
        self.folder_id = folder_id
        self.due_date = due
        self.starred = bool(starred)
        self.delete_btn.disabled = self.task is None
        self._refresh_chips()

    def on_enter(self):
        # Focus after the slide so the soft keyboard opens on the title.
        self.title_input.focus = True

    # --- field actions ------------------------------------------------
    def _refresh_chips(self):
        self.star_btn.text = '★ Priority' if self.starred else '☆ Priority'
        self.star_btn.set_kind('accent' if self.starred else 'ghost')
        self.due_btn.text = self.due_date or 'Due date'
        self.due_btn.set_kind('primary' if self.due_date else 'ghost')
        name = 'Home'
        if self.folder_id is not None:
            folder = App.get_running_app().folder_manager.get_folder(self.folder_id)
            name = folder.name if folder else 'Home'
        self.folder_btn.text = f'Folder: {name}  ›'

    def toggle_star(self, *_):
        self.starred = not self.starred
        self._refresh_chips()

    def pick_due(self, *_):
        def _set(value):
            self.due_date = value or None
            self._refresh_chips()
        pick_date(self.due_date, _set)

    def pick_folder(self, *_):
        def _set(folder_id):
            self.folder_id = folder_id
            self._refresh_chips()
        pick_folder('Task folder', self.folder_id, _set)

    # --- persistence --------------------------------------------------
    def save(self):
        title = self.title_input.text.strip()
        if not title:
            return False  # don't create blank/default tasks
        tm = App.get_running_app().task_manager
        fields = dict(
            description=self.desc_input.text,
            due_date=self.due_date,
            starred=self.starred,
        )
        if self.task is None:
            task_id = tm.create_task(title, folder_id=self.folder_id, **fields)
            if self.done_box.active:
                tm.update_task(task_id, completed=True)
            self.task = tm.get_task(task_id)
        else:
            tm.update_task(self.task.id, title=title, completed=self.done_box.active,
                           folder_id=self.folder_id, **fields)
        return True

    def save_and_close(self, *_):
        if self.save():
            self._close()
        else:
            self.title_input.hint_text = 'Give the task a title'
            self.title_input.focus = True

    def go_back(self, *_):
        # Back keeps edits if there is a title; an empty new task is discarded.
        self.save()
        self._close()

    def delete_task(self, *_):
        if self.task is not None:
            App.get_running_app().task_manager.delete_task(self.task.id)
        self._close()

    def _close(self):
        self.title_input.focus = False
        self.task = None
        switch_screen(self.manager, self.return_to, 'right')
