"""
Task List Screen - per-folder tasks with stars, due dates, and drag reorder
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ui.theme import ACCENT, MUTED, TEXT, FlatButton, switch_screen
from ui.widgets.date_picker import pick_date
from ui.widgets.drag_ghost import DragGhost


class TaskRow(BoxLayout):
    def __init__(self, task, host, **kwargs):
        super().__init__(size_hint_y=None, height=dp(54), spacing=dp(4), **kwargs)
        self.task = task
        self.host = host
        self._dragging = False

        self.handle = FlatButton(text='≡', kind='ghost', size_hint_x=None, width=dp(36))
        self.handle.bind(on_touch_down=self._on_handle_down)
        self.handle.bind(on_touch_move=self._on_handle_move)
        self.handle.bind(on_touch_up=self._on_handle_up)
        self.add_widget(self.handle)

        self.checkbox = CheckBox(
            active=bool(task.completed),
            size_hint_x=None,
            width=dp(36),
            color=ACCENT,
        )
        self.checkbox.bind(active=self._on_check)
        self.add_widget(self.checkbox)

        self.star_btn = FlatButton(
            text='★' if task.starred else '☆',
            kind='accent' if task.starred else 'ghost',
            size_hint_x=None,
            width=dp(36),
        )
        self.star_btn.bind(on_press=lambda _x: host.star_task(self))
        self.add_widget(self.star_btn)

        self.title_label = Label(
            text=self._title_markup(),
            markup=True,
            halign='left',
            valign='middle',
            color=MUTED if task.completed else TEXT,
        )
        self.title_label.bind(size=lambda l, v: setattr(l, 'text_size', (v[0], None)))
        self.add_widget(self.title_label)

        self.due_btn = FlatButton(
            text=task.due_date or 'Due',
            kind='primary' if task.due_date else 'ghost',
            size_hint_x=None,
            width=dp(88),
            font_size='13sp',
        )
        self.due_btn.bind(on_press=lambda _x: host.edit_due_date(self))
        self.add_widget(self.due_btn)

        delete_btn = FlatButton(text='X', kind='danger', size_hint_x=None, width=dp(36))
        delete_btn.bind(on_press=lambda _x: host.delete_task(self))
        self.add_widget(delete_btn)

    def _title_markup(self):
        if self.task.completed:
            return f'[s]{self.task.title}[/s]'
        return self.task.title

    def refresh_visuals(self):
        self.star_btn.text = '★' if self.task.starred else '☆'
        self.star_btn.set_kind('accent' if self.task.starred else 'ghost')
        self.title_label.text = self._title_markup()
        self.title_label.color = MUTED if self.task.completed else TEXT
        self.due_btn.text = self.task.due_date or 'Due'
        self.due_btn.set_kind('primary' if self.task.due_date else 'ghost')
        if self.checkbox.active != bool(self.task.completed):
            self.host._syncing = True
            self.checkbox.active = bool(self.task.completed)
            self.host._syncing = False

    def _on_check(self, _cb, value):
        self.host.toggle_task(self, value)

    def _on_handle_down(self, handle, touch):
        if handle.collide_point(*touch.pos):
            touch.grab(handle)
            self._dragging = True
            self.opacity = 0.28
            handle.background_color = ACCENT
            self.host.begin_task_ghost(self)
            return True
        return False

    def _on_handle_move(self, handle, touch):
        if touch.grab_current is not handle:
            return False
        self.host.move_task_ghost(touch.pos)
        self.host.drag_row_toward(self, touch.y)
        return True

    def _on_handle_up(self, handle, touch):
        if touch.grab_current is not handle:
            return False
        touch.ungrab(handle)
        self._dragging = False
        self.opacity = 1
        handle.set_kind('ghost')
        self.host.end_task_ghost()
        self.host.persist_row_order()
        return True


class TaskListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.folder_id = None
        self._ghost = None
        self._syncing = False
        self.build_ui()

    def set_context(self, folder_id):
        self.folder_id = folder_id

    def build_ui(self):
        main_layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        top_bar.add_widget(FlatButton(text='← Back', kind='neutral', size_hint_x=0.5, on_press=self.go_back))
        top_bar.add_widget(FlatButton(text='+ New Task', kind='primary', size_hint_x=0.5, on_press=self.create_task))
        main_layout.add_widget(top_bar)

        self.title_label = Label(
            text='Tasks',
            size_hint_y=None,
            height=dp(36),
            font_size='22sp',
            bold=True,
            color=TEXT,
            halign='left',
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        main_layout.add_widget(self.title_label)

        hint = Label(
            text='★ priority  ·  ≡ drag to reorder  ·  Due to set a date',
            size_hint_y=None,
            height=dp(22),
            color=MUTED,
            font_size='13sp',
        )
        main_layout.add_widget(hint)

        scroll = ScrollView(bar_width=dp(3), bar_color=ACCENT, scroll_type=['bars', 'content'])
        self.task_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[0, dp(2)])
        self.task_grid.bind(minimum_height=self.task_grid.setter('height'))
        scroll.add_widget(self.task_grid)
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)

    def on_pre_enter(self):
        self.refresh_tasks()

    def on_enter(self):
        pass

    def _scope_kwargs(self):
        return {
            'folder_id': self.folder_id,
            'include_completed': True,
            'unfiled_only': self.folder_id is None,
        }

    def refresh_tasks(self):
        app = App.get_running_app()
        self.task_grid.clear_widgets()

        if self.folder_id is None:
            self.title_label.text = 'Tasks · Home'
        else:
            folder = app.folder_manager.get_folder(self.folder_id)
            name = folder.name if folder else 'Folder'
            self.title_label.text = f'Tasks · {name}'

        tasks = app.task_manager.get_all_tasks(**self._scope_kwargs())
        for task in tasks:
            self.task_grid.add_widget(TaskRow(task, self))

        if not tasks:
            self.task_grid.add_widget(
                Label(text='No tasks yet. Create one!', size_hint_y=None, height=dp(48), color=MUTED)
            )

    def begin_task_ghost(self, row):
        self.end_task_ghost()
        self._ghost = DragGhost(row.task.title, (row.width, row.height))
        self._ghost.attach(row.center)

    def move_task_ghost(self, pos):
        if self._ghost is not None:
            self._ghost.follow(pos)

    def end_task_ghost(self):
        if self._ghost is not None:
            self._ghost.detach()
            self._ghost = None

    def drag_row_toward(self, row, y):
        children = self.task_grid.children
        if row not in children:
            return
        for other in list(children):
            if other is row or not isinstance(other, TaskRow):
                continue
            if other.y <= y <= other.top:
                other.opacity = 0.45
                i = children.index(row)
                j = children.index(other)
                children[i], children[j] = children[j], children[i]
                self.task_grid._trigger_layout()
                for child in children:
                    if isinstance(child, TaskRow) and child is not row:
                        child.opacity = 1
                row.opacity = 0.7
                break

    def persist_row_order(self):
        rows = [c for c in reversed(self.task_grid.children) if isinstance(c, TaskRow)]
        App.get_running_app().task_manager.reorder_tasks([row.task.id for row in rows])

    def _as_row(self, task_or_row):
        if isinstance(task_or_row, TaskRow):
            return task_or_row
        for child in self.task_grid.children:
            if isinstance(child, TaskRow) and child.task.id == getattr(task_or_row, 'id', None):
                return child
        return None

    def toggle_task(self, task_or_row, completed):
        if self._syncing:
            return
        row = self._as_row(task_or_row)
        task = row.task if row is not None else task_or_row
        task.completed = bool(completed)
        App.get_running_app().task_manager.update_task(task.id, completed=completed)
        if row is not None:
            self._syncing = True
            row.refresh_visuals()
            self._syncing = False

    def star_task(self, task_or_row):
        row = self._as_row(task_or_row)
        task = row.task if row is not None else task_or_row
        App.get_running_app().task_manager.toggle_star(task.id)
        task.starred = not task.starred
        if row is not None:
            row.refresh_visuals()
            if task.starred:
                self._move_row_to_top(row)

    def _move_row_to_top(self, row):
        rows = [c for c in reversed(self.task_grid.children) if isinstance(c, TaskRow)]
        others = [c for c in self.task_grid.children if not isinstance(c, TaskRow)]
        if row in rows:
            rows.remove(row)
            rows.insert(0, row)
        self.task_grid.clear_widgets()
        for item in rows:
            self.task_grid.add_widget(item)
        for item in others:
            self.task_grid.add_widget(item)

    def edit_due_date(self, task_or_row):
        row = self._as_row(task_or_row)
        task = row.task if row is not None else task_or_row

        def _save(value):
            App.get_running_app().task_manager.update_task(task.id, due_date=value or None)
            task.due_date = value or None
            if row is not None:
                row.refresh_visuals()

        pick_date(task.due_date, _save)

    def delete_task(self, task_or_row):
        row = self._as_row(task_or_row)
        task = row.task if row is not None else task_or_row
        App.get_running_app().task_manager.delete_task(task.id)
        if row is not None and row.parent is self.task_grid:
            self.task_grid.remove_widget(row)
        if not any(isinstance(c, TaskRow) for c in self.task_grid.children):
            self.task_grid.add_widget(
                Label(text='No tasks yet. Create one!', size_hint_y=None, height=dp(48), color=MUTED)
            )

    def create_task(self, instance):
        App.get_running_app().task_manager.create_task('New Task', folder_id=self.folder_id)
        self.refresh_tasks()

    def go_back(self, instance):
        switch_screen(self.manager, 'main', 'right')
