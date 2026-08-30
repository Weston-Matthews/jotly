"""
Main Screen - folders, notes, and a preview of open tasks
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

from models.note import NoteManager
from ui.theme import (
    ACCENT,
    DROP,
    HOLD,
    HINT,
    MUTED,
    SURFACE,
    TEXT,
    FlatButton,
    FlatInput,
    switch_screen,
)
from ui.widgets.dialogs import prompt_text
from ui.widgets.drag_ghost import DragGhost
from ui.widgets.folder_tray import FolderBrowseTray

HOLD_SECONDS = 0.7


class DropFolderButton(FlatButton):
    """Folder row that can receive a dragged note."""

    def __init__(self, folder, **kwargs):
        kwargs.setdefault('kind', 'folder')
        super().__init__(**kwargs)
        self.folder = folder
        self.is_drop_target = True


class DraggableNoteButton(FlatButton):
    """Tap to open, drag onto a folder (or Home) to move."""

    def __init__(self, note, host, **kwargs):
        kwargs.setdefault('kind', 'note')
        super().__init__(**kwargs)
        self.note = note
        self.host = host
        self._dragging = False
        self._origin = None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        touch.grab(self)
        self._dragging = False
        self._origin = (self.x, self.y)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        if abs(touch.dx) + abs(touch.dy) > dp(12):
            if not self._dragging:
                self._dragging = True
                self.opacity = 0.28
                self.host.begin_note_drag(self)
        if self._dragging:
            self.host.move_note_ghost(touch.pos)
            self.host.on_note_drag(touch)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        if self._dragging:
            self.host.end_note_ghost()
            self.host.drop_note(self.note, touch)
            self.opacity = 1
            self.host.refresh_content()
        else:
            self.host.open_note(self.note)
        return True


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_folder = None
        self.folder_drop_targets = []
        self.home_drop_target = None
        self._hold_event = None
        self._hold_target = None
        self._highlighted = []
        self._hover_widget = None
        self._ghost = None
        self._search_ev = None
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
            halign='left',
            color=MUTED,
            font_size='13sp',
        )
        self.breadcrumb.bind(size=self.breadcrumb.setter('text_size'))
        main_layout.add_widget(self.breadcrumb)
        self.drag_hint = Label(
            text='',
            size_hint_y=None,
            height=dp(18),
            color=HINT,
            font_size='12sp',
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
                text=f'📁  {folder.name}',
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
            self.content_grid.add_widget(self._note_row(note, draggable=True))

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

    def _touch_hits(self, widget, touch):
        return widget.collide_point(*widget.to_widget(*touch.pos))

    def begin_note_drag(self, note_btn):
        self.drag_hint.text = 'Drop on a folder  ·  hold ← Up to browse  ·  release elsewhere to cancel'
        self._paint_targets(idle=False)
        self.end_note_ghost()
        self._ghost = DragGhost(note_btn.text, note_btn.size)
        self._ghost.attach(note_btn.center)

    def move_note_ghost(self, pos):
        if self._ghost is not None:
            self._ghost.follow(pos)

    def end_note_ghost(self):
        if self._ghost is not None:
            self._ghost.detach()
            self._ghost = None

    def _paint_targets(self, idle=True):
        for btn in self.folder_drop_targets:
            if idle:
                btn.set_kind('folder')
            else:
                btn.background_color = (0.28, 0.36, 0.48, 1)
        if self.home_drop_target:
            if idle:
                self.home_drop_target.set_kind('neutral')
            else:
                self.home_drop_target.background_color = (0.28, 0.36, 0.48, 1)

    def _clear_highlights(self):
        self._hover_widget = None
        for widget in self._highlighted:
            if hasattr(widget, 'set_kind'):
                widget.set_kind(getattr(widget, 'kind', 'neutral'))
            else:
                widget.background_color = (1, 1, 1, 1)
        self._highlighted = []
        self._paint_targets(idle=True)
        for chip in getattr(self.folder_tray, 'chips', []):
            if hasattr(chip, 'set_kind'):
                chip.set_kind('folder')

    def _highlight(self, widget, color):
        if widget is None:
            return
        widget.background_color = color
        self._hover_widget = widget
        if widget not in self._highlighted:
            self._highlighted.append(widget)

    def _cancel_hold(self):
        if self._hold_event is not None:
            self._hold_event.cancel()
            self._hold_event = None
        self._hold_target = None

    def on_note_drag(self, touch):
        target_key = None
        open_parent = None

        chip = self.folder_tray.chip_under(touch) if self.folder_tray.is_open() else None
        hover = None
        hover_color = DROP
        hint = 'Release to cancel'

        if chip is not None:
            target_key = ('chip', chip.folder_id)
            open_parent = chip.folder_id
            hover = chip
            hint = f'Drop to move into {chip.text.replace("📁", "").replace("⌂", "").strip()}'
        elif self.home_drop_target and self._touch_hits(self.home_drop_target, touch):
            target_key = ('up', None)
            hover = self.home_drop_target
            hover_color = HOLD
            hint = 'Hold to browse folders  ·  drop now to move to parent / Home'
            if self.current_folder is None:
                open_parent = None
            else:
                folder = App.get_running_app().folder_manager.get_folder(self.current_folder)
                open_parent = folder.parent_id if folder else None
        else:
            for folder_btn in self.folder_drop_targets:
                if self._touch_hits(folder_btn, touch):
                    hover = folder_btn
                    hint = f'Drop to move into {folder_btn.folder.name}'
                    break

        if hover is not self._hover_widget:
            self._clear_highlights()
            self._paint_targets(idle=False)
            if hover is not None:
                self._highlight(hover, hover_color)
        self.drag_hint.text = hint

        if target_key != self._hold_target:
            self._cancel_hold()
            if target_key is not None:
                self._hold_target = target_key
                self._hold_event = Clock.schedule_once(
                    lambda _dt, parent=open_parent, key=target_key: self._open_hold_target(key, parent),
                    HOLD_SECONDS,
                )

    def _open_hold_target(self, key, parent_id):
        self._hold_event = None
        kind, folder_id = key
        if kind == 'up':
            self.folder_tray.show(parent_id)
        elif kind == 'chip':
            children = App.get_running_app().folder_manager.get_all_folders(folder_id)
            if folder_id is None:
                self.folder_tray.show(None)
            elif children:
                self.folder_tray.show(folder_id)

    def drop_note(self, note, touch):
        app = App.get_running_app()
        self._cancel_hold()
        self._clear_highlights()
        self.drag_hint.text = ''

        chip = self.folder_tray.chip_under(touch) if self.folder_tray.is_open() else None
        if chip is not None:
            app.note_manager.move_note(note.id, chip.folder_id)
            self.folder_tray.hide()
            return

        for folder_btn in self.folder_drop_targets:
            if self._touch_hits(folder_btn, touch):
                app.note_manager.move_note(note.id, folder_btn.folder.id)
                self.folder_tray.hide()
                return

        if self.home_drop_target and self._touch_hits(self.home_drop_target, touch):
            target = None
            if self.current_folder is not None:
                folder = app.folder_manager.get_folder(self.current_folder)
                target = folder.parent_id if folder else None
            app.note_manager.move_note(note.id, target)

        self.folder_tray.hide()

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
        self.open_task_list()

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
        app = App.get_running_app()
        app.task_manager.create_task('New Task', '', self.current_folder)
        self.refresh_content()

    def create_new_folder(self, instance):
        def _save(name):
            App.get_running_app().folder_manager.create_folder(
                name or 'New Folder', self.current_folder
            )
            self.refresh_content()

        prompt_text('New folder', 'New Folder', _save, hint='Folder name')

    def _note_label(self, note):
        app = App.get_running_app()
        tags = app.tag_manager.get_note_tags(note.id)
        tag_bit = '  '.join(f'#{t.name}' for t in tags[:4])
        preview = NoteManager.preview_text(note.content)
        bits = [f'📝  {note.title}']
        if tag_bit:
            bits.append(tag_bit)
        if preview:
            bits.append(preview)
        return '\n'.join(bits)

    def _note_row(self, note, draggable=True):
        row = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(6))
        if draggable:
            note_btn = DraggableNoteButton(
                note,
                self,
                text=self._note_label(note),
                halign='left',
                valign='middle',
            )
        else:
            note_btn = FlatButton(
                text=self._note_label(note),
                kind='note',
                halign='left',
                valign='middle',
            )
            note_btn.bind(on_press=lambda _x, n=note: self.open_note(n))
        rename_btn = FlatButton(text='Rename', kind='ghost', size_hint_x=None, width=dp(88))
        rename_btn.bind(on_press=lambda _x, n=note: self.rename_note(n))
        row.add_widget(note_btn)
        row.add_widget(rename_btn)
        return row

    def clip_inbox(self, _instance=None):
        def _save(text):
            if not text:
                return
            app = App.get_running_app()
            note_id = app.capture.capture_text(text, folder_id=self.current_folder)
            if note_id:
                self.refresh_content()
                self.open_note(app.note_manager.get_note(note_id))

        prompt_text('Clip text or a URL', '', _save, hint='Paste a link or a thought')

    def clip_file(self, _instance=None):
        from kivy.uix.boxlayout import BoxLayout as _Box
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup

        layout = _Box(orientation='vertical', padding=dp(8), spacing=dp(8))
        chooser = FileChooserListView(path='.')
        layout.add_widget(chooser)
        buttons = _Box(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = FlatButton(text='Cancel', kind='ghost')
        attach = FlatButton(text='Create note', kind='primary')
        buttons.add_widget(cancel)
        buttons.add_widget(attach)
        layout.add_widget(buttons)
        popup = Popup(
            title='Attach a file into a new note',
            content=layout,
            size_hint=(0.92, 0.8),
            title_color=TEXT,
            background='',
            background_color=SURFACE,
        )

        def _close(_x=None):
            popup.dismiss()

        def _go(_x=None):
            if chooser.selection:
                app = App.get_running_app()
                note_id = app.capture.capture_file(
                    chooser.selection[0], folder_id=self.current_folder
                )
                popup.dismiss()
                if note_id:
                    self.refresh_content()
                    self.open_note(app.note_manager.get_note(note_id))
                return
            popup.dismiss()

        cancel.bind(on_press=_close)
        attach.bind(on_press=_go)
        popup.open()

    def export_archive(self, _instance=None):
        app = App.get_running_app()
        dest = app.user_data_dir

        def _save(name):
            filename = name or 'jotly-backup.zip'
            if not filename.endswith('.zip'):
                filename += '.zip'
            path = filename if filename.startswith('/') else f'{dest}/{filename}'
            app.backup.export_archive(path)
            self.drag_hint.text = f'Exported to {path}'

        prompt_text('Export archive', 'jotly-backup.zip', _save, hint='Filename in app storage')

    def import_archive(self, _instance=None):
        from kivy.uix.boxlayout import BoxLayout as _Box
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup

        layout = _Box(orientation='vertical', padding=dp(8), spacing=dp(8))
        chooser = FileChooserListView(path=App.get_running_app().user_data_dir, filters=['*.zip'])
        layout.add_widget(chooser)
        buttons = _Box(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = FlatButton(text='Cancel', kind='ghost')
        load = FlatButton(text='Import', kind='primary')
        buttons.add_widget(cancel)
        buttons.add_widget(load)
        layout.add_widget(buttons)
        popup = Popup(
            title='Import Jotly archive',
            content=layout,
            size_hint=(0.92, 0.8),
            title_color=TEXT,
            background='',
            background_color=SURFACE,
        )

        def _close(_x=None):
            popup.dismiss()

        def _go(_x=None):
            if chooser.selection:
                counts = App.get_running_app().backup.import_archive(chooser.selection[0])
                self.drag_hint.text = (
                    f"Imported {counts['notes']} notes, {counts['tasks']} tasks"
                )
                self.refresh_content()
            popup.dismiss()

        cancel.bind(on_press=_close)
        load.bind(on_press=_go)
        popup.open()

    def search_notes(self, instance):
        query = self.search_input.text.strip()
        if not query:
            self.refresh_content()
            return

        app = App.get_running_app()
        self.content_grid.clear_widgets()
        notes = app.note_manager.search_notes(query)
        for note in notes:
            self.content_grid.add_widget(self._note_row(note, draggable=False))
        if not notes:
            self.content_grid.add_widget(
                Label(text='No results found', size_hint_y=None, height=dp(48), color=MUTED)
            )
