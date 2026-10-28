"""
Main Screen - folders, notes, and a preview of open tasks

Coordinator only. Row widgets, drag handling, and capture/backup dialogs
live in ui/widgets/.
"""

from datetime import date

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ui.theme import (
    ACCENT,
    DEFAULT_FONT,
    HINT,
    MUTED,
    TEXT,
    FlatButton,
    FlatInput,
    switch_screen,
)
from ui.widgets.capture_dialogs import (
    clip_file as open_clip_file,
    clip_inbox as open_clip_inbox,
    export_archive as open_export_archive,
    import_archive as open_import_archive,
)
from ui.widgets.dialogs import prompt_text
from ui.widgets.folder_tray import FolderBrowseTray
from ui.widgets.note_drag_controller import NoteDragController
from ui.widgets.note_row import DropFolderButton, note_row


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_folder = None
        self.folder_drop_targets = []
        self.home_drop_target = None
        self._search_ev = None
        self.drag = NoteDragController(self)
        self.build_ui()

    def build_ui(self):
        main_layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))

        top_title = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(58), spacing=0)
        app_title = Label(
            text='Jotly',
            font_size='28sp',
            bold=True,
            color=TEXT,
            halign='center',
            valign='middle',
        )
        today_str = date.today().strftime('%A, %B %d, %Y')
        app_title_date = Label(text=today_str, color=MUTED, font_size='13sp', halign='center')
        top_title.add_widget(app_title)
        top_title.add_widget(app_title_date)
        main_layout.add_widget(top_title)

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.search_input = FlatInput(
            hint_text='Search notes…',
            multiline=False,
            size_hint_x=0.6,
            font_size='15sp',
        )
        self.search_input.bind(on_text_validate=self.search_notes)
        self.search_input.bind(text=self._on_search_text)
        top_bar.add_widget(self.search_input)
        top_bar.add_widget(FlatButton(text='+ Note', kind='primary', size_hint_x=0.2, on_press=self.create_new_note))
        top_bar.add_widget(FlatButton(text='+ Task', kind='success', size_hint_x=0.2, on_press=self.create_new_task))
        main_layout.add_widget(top_bar)

        util_bar = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        util_bar.add_widget(FlatButton(text='Clip', kind='ghost', on_press=self.clip_inbox))
        util_bar.add_widget(FlatButton(text='Attach', kind='ghost', on_press=self.clip_file))
        util_bar.add_widget(FlatButton(text='Export', kind='ghost', on_press=self.export_archive))
        util_bar.add_widget(FlatButton(text='Import', kind='ghost', on_press=self.import_archive))
        main_layout.add_widget(util_bar)

        self.breadcrumb = Label(
            text='Home',
            size_hint_y=None,
            height=dp(26),
            color=MUTED,
            font_size='13sp',
            font_name=DEFAULT_FONT,
        )
        self.breadcrumb.bind(size=self.breadcrumb.setter('text_size'))
        main_layout.add_widget(self.breadcrumb)
        self.drag_hint = Label(
            text='',
            size_hint_y=None,
            height=dp(18),
            color=HINT,
            font_size='12sp',
            font_name=DEFAULT_FONT,
        )
        main_layout.add_widget(self.drag_hint)

        scroll = ScrollView(bar_width=dp(3), bar_color=ACCENT, scroll_type=['bars', 'content'])
        self.content_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[0, dp(2)])
        self.content_grid.bind(minimum_height=self.content_grid.setter('height'))
        scroll.add_widget(self.content_grid)
        main_layout.add_widget(scroll)

        bottom_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.up_btn = FlatButton(text='← Up / Home', kind='neutral', size_hint_x=0.34, on_press=self.go_up)
        self.home_drop_target = self.up_btn
        bottom_bar.add_widget(self.up_btn)
        bottom_bar.add_widget(FlatButton(text='Tasks', kind='primary', size_hint_x=0.33, on_press=self.open_task_list))
        bottom_bar.add_widget(FlatButton(text='+ Folder', kind='neutral', size_hint_x=0.33, on_press=self.create_new_folder))
        main_layout.add_widget(bottom_bar)

        self.folder_tray = FolderBrowseTray(self)
        main_layout.add_widget(self.folder_tray)

        self.add_widget(main_layout)

    def on_pre_enter(self):
        # Paint the list before the slide finishes so the destination isn't empty.
        self.refresh_content()
        self._consume_share()

    def _consume_share(self):
        app = App.get_running_app()
        payload = getattr(app, 'pending_share', None)
        if not payload:
            return
        app.pending_share = None
        text = (payload.get('text') or '').strip()
        title = (payload.get('subject') or '').strip() or None
        if not text:
            return
        note_id = app.capture.capture_text(text, folder_id=self.current_folder, title=title)
        if note_id:
            note = app.note_manager.get_note(note_id)
            self.open_note(note)

    def on_enter(self):
        pass

    def _on_search_text(self, _instance, value):
        if self._search_ev is not None:
            self._search_ev.cancel()
        delay = 0.0 if not (value or '').strip() else 0.12
        self._search_ev = Clock.schedule_once(lambda _dt: self.search_notes(None), delay)

    def refresh_content(self):
        app = App.get_running_app()
        self.content_grid.clear_widgets()
        self.folder_drop_targets = []

        folders = app.folder_manager.get_all_folders(self.current_folder)
        for folder in folders:
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            folder_btn = DropFolderButton(
                folder,
                text=f'▸  {folder.name}',
                halign='left',
                valign='middle',
            )
            folder_btn.bind(on_press=lambda _x, f=folder: self.open_folder(f))
            rename_btn = FlatButton(text='Rename', kind='ghost', size_hint_x=None, width=dp(88))
            rename_btn.bind(on_press=lambda _x, f=folder: self.rename_folder(f))
            row.add_widget(folder_btn)
            row.add_widget(rename_btn)
            self.content_grid.add_widget(row)
            self.folder_drop_targets.append(folder_btn)

        notes = app.note_manager.get_all_notes(self.current_folder)
        for note in notes:
            self.content_grid.add_widget(note_row(note, self, draggable=True))

        tasks = app.task_manager.get_all_tasks(
            folder_id=self.current_folder,
            include_completed=False,
            unfiled_only=self.current_folder is None,
        )
        for task in tasks:
            star = '★ ' if task.starred else ''
            due = f'  · {task.due_date}' if task.due_date else ''
            task_btn = FlatButton(
                text=f'☐  {star}{task.title}{due}',
                kind='task',
                size_hint_y=None,
                height=dp(48),
                halign='left',
                valign='middle',
            )
            task_btn.bind(on_press=lambda _x, t=task: self.open_task(t))
            self.content_grid.add_widget(task_btn)

        if not folders and not notes and not tasks:
            self.content_grid.add_widget(
                Label(
                    text='Inbox is empty  ·  Clip a link, attach a file, or add a note',
                    size_hint_y=None,
                    height=dp(48),
                    color=MUTED,
                )
            )

        self.update_breadcrumb()

    def update_breadcrumb(self):
        if self.current_folder is None:
            self.breadcrumb.text = 'Home  ·  drag onto a folder, or hold ← Up to browse'
        else:
            app = App.get_running_app()
            path = app.folder_manager.get_folder_path(self.current_folder)
            path_text = ' › '.join(f.name for f in path)
            self.breadcrumb.text = path_text + '  ·  hold ← Up to browse parent folders'

    # Drag delegation — DraggableNoteButton still talks to the screen.
    def begin_note_drag(self, note_btn):
        self.drag.begin_note_drag(note_btn)

    def move_note_ghost(self, pos):
        self.drag.move_note_ghost(pos)

    def end_note_ghost(self):
        self.drag.end_note_ghost()

    def on_note_drag(self, pos):
        self.drag.on_note_drag(pos)

    def drop_note(self, note, pos):
        self.drag.drop_note(note, pos)

    def rename_folder(self, folder):
        def _save(name):
            if name:
                App.get_running_app().folder_manager.update_folder(folder.id, name=name)
                self.refresh_content()

        prompt_text('Rename folder', folder.name, _save)

    def rename_note(self, note):
        def _save(name):
            if name:
                App.get_running_app().note_manager.update_note(note.id, title=name)
                self.refresh_content()

        prompt_text('Rename note', note.title, _save)

    def open_folder(self, folder):
        self.current_folder = folder.id
        self.refresh_content()

    def open_note(self, note):
        editor_screen = self.manager.get_screen('note_editor')
        editor_screen.load_note(note)
        switch_screen(self.manager, 'note_editor', 'left')

    def open_task(self, task):
        editor = self.manager.get_screen('task_editor')
        editor.edit_task(task, return_to='main')
        switch_screen(self.manager, 'task_editor', 'left')

    def open_task_list(self, instance=None):
        task_screen = self.manager.get_screen('task_list')
        task_screen.set_context(self.current_folder)
        switch_screen(self.manager, 'task_list', 'left')

    def go_up(self, instance=None):
        if self.current_folder is None:
            return
        folder = App.get_running_app().folder_manager.get_folder(self.current_folder)
        self.current_folder = folder.parent_id if folder else None
        self.refresh_content()

    def create_new_note(self, instance):
        app = App.get_running_app()
        note_id = app.note_manager.create_note('Untitled Note', '', self.current_folder)
        note = app.note_manager.get_note(note_id)
        self.open_note(note)

    def create_new_task(self, instance):
        editor = self.manager.get_screen('task_editor')
        editor.new_task(self.current_folder, return_to='main')
        switch_screen(self.manager, 'task_editor', 'left')

    def create_new_folder(self, instance):
        def _save(name):
            App.get_running_app().folder_manager.create_folder(
                name or 'New Folder', self.current_folder
            )
            self.refresh_content()

        prompt_text('New folder', 'New Folder', _save, hint='Folder name')

    def clip_inbox(self, _instance=None):
        open_clip_inbox(self)

    def clip_file(self, _instance=None):
        open_clip_file(self)

    def export_archive(self, _instance=None):
        open_export_archive(self)

    def import_archive(self, _instance=None):
        open_import_archive(self)

    def search_notes(self, instance):
        query = self.search_input.text.strip()
        if not query:
            self.refresh_content()
            return

        app = App.get_running_app()
        self.content_grid.clear_widgets()
        notes = app.note_manager.search_notes(query)
        for note in notes:
            self.content_grid.add_widget(note_row(note, self, draggable=False))
        if not notes:
            self.content_grid.add_widget(
                Label(text='No results found', size_hint_y=None, height=dp(48), color=MUTED)
            )
