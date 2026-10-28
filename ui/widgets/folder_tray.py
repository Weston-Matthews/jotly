"""Hold-to-browse folder tray used while dragging a note."""

from kivy.app import App
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from ui.theme import MUTED, TEXT, FlatButton


class TrayFolderChip(FlatButton):
    def __init__(self, folder_id, name, **kwargs):
        kwargs.setdefault('kind', 'folder')
        super().__init__(**kwargs)
        self.folder_id = folder_id
        self.text = name
        self.size_hint_y = None
        self.height = dp(40)
        self.halign = 'left'


class FolderBrowseTray(BoxLayout):
    """Lists folders for one parent; holding a chip drills into it."""

    def __init__(self, host, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        super().__init__(orientation='vertical', spacing=dp(4), padding=dp(6), **kwargs)
        self.host = host
        self.current_parent_id = None
        self.height = 0
        self.opacity = 0
        self.disabled = True
        self._bg = None

        header = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(4))
        self.back_btn = FlatButton(text='‹', kind='ghost', size_hint_x=None, width=dp(36))
        self.back_btn.bind(on_press=lambda *_: self.go_back())
        self.title = Label(text='Move to…', halign='left', valign='middle', color=TEXT)
        self.title.bind(size=self.title.setter('text_size'))
        header.add_widget(self.back_btn)
        header.add_widget(self.title)
        self.add_widget(header)

        scroll = ScrollView()
        self.chip_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(3))
        self.chip_box.bind(minimum_height=self.chip_box.setter('height'))
        scroll.add_widget(self.chip_box)
        self.add_widget(scroll)

        self.chips = []

    def show(self, parent_id):
        self.current_parent_id = parent_id
        self.height = dp(168)
        self.opacity = 1
        self.disabled = False
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.12, 0.16, 0.22, 0.95)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self._sync_bg, size=self._sync_bg)
        self._fill(parent_id)

    def _sync_bg(self, *_args):
        if self._bg is not None:
            self._bg.pos = self.pos
            self._bg.size = self.size

    def hide(self):
        self.opacity = 0
        self.height = 0
        self.disabled = True
        self.chips = []
        self.chip_box.clear_widgets()
        self.canvas.before.clear()
        self._bg = None

    def is_open(self):
        return self.opacity > 0.5

    # While collapsed (height 0) the header still lays out on top of the
    # bottom bar, and disabled widgets swallow touches that collide with
    # them. Ignore all touches unless the tray is actually open.
    def on_touch_down(self, touch):
        if not self.is_open():
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.is_open():
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if not self.is_open():
            return False
        return super().on_touch_up(touch)

    def go_back(self):
        if self.current_parent_id is None:
            return
        folder = App.get_running_app().folder_manager.get_folder(self.current_parent_id)
        parent = folder.parent_id if folder else None
        self.show(parent)

    def _fill(self, parent_id):
        app = App.get_running_app()
        self.chip_box.clear_widgets()
        self.chips = []

        if parent_id is None:
            self.title.text = 'Move to · Home'
        else:
            folder = app.folder_manager.get_folder(parent_id)
            self.title.text = f'Move to · {folder.name if folder else "Folder"}'

        home_chip = TrayFolderChip(None, '⌂  Unfiled / Home')
        self.chip_box.add_widget(home_chip)
        self.chips.append(home_chip)

        folders = app.folder_manager.get_all_folders(parent_id)
        if not folders and parent_id is not None:
            here = TrayFolderChip(parent_id, '▸  Drop here (no subfolders)')
            self.chip_box.add_widget(here)
            self.chips.append(here)
            return

        for folder in folders:
            children = app.folder_manager.get_all_folders(folder.id)
            suffix = '  ›' if children else ''
            chip = TrayFolderChip(folder.id, f'▸  {folder.name}{suffix}')
            self.chip_box.add_widget(chip)
            self.chips.append(chip)

    def chip_under(self, pos):
        """pos is in window coordinates."""
        if not self.is_open():
            return None
        for chip in self.chips:
            if chip.collide_point(*chip.to_widget(*pos)):
                return chip
        return None
