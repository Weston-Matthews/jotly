"""Tap-to-pick folder popup: the reliable "Move to…" path (no drag needed)."""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from ui.theme import SURFACE, TEXT, FlatButton


def _walk(folder_manager, parent_id=None, depth=0):
    for folder in folder_manager.get_all_folders(parent_id):
        yield folder, depth
        yield from _walk(folder_manager, folder.id, depth + 1)


def pick_folder(title, current_folder_id, on_pick):
    """Call on_pick(folder_id) with a folder id, or None for Home."""
    app = App.get_running_app()
    layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))
    scroll = ScrollView()
    box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
    box.bind(minimum_height=box.setter('height'))
    scroll.add_widget(box)
    layout.add_widget(scroll)

    popup = Popup(
        title=title,
        content=layout,
        size_hint=(0.88, 0.7),
        title_color=TEXT,
        background='',
        background_color=SURFACE,
    )

    def _choose(folder_id):
        popup.dismiss()
        on_pick(folder_id)

    entries = [(None, '⌂  Home (unfiled)', 0)]
    entries += [(f.id, f'▸  {f.name}', d) for f, d in _walk(app.folder_manager)]
    for folder_id, label, depth in entries:
        here = folder_id == current_folder_id
        btn = FlatButton(
            text=label + ('   ✓' if here else ''),
            kind='primary' if here else 'folder',
            size_hint_y=None,
            height=dp(44),
            halign='left',
            valign='middle',
        )
        btn.padding = (dp(10) + dp(18) * depth, 0)
        btn.bind(on_release=lambda _b, fid=folder_id: _choose(fid))
        box.add_widget(btn)

    cancel = FlatButton(text='Cancel', kind='ghost', size_hint_y=None, height=dp(44))
    cancel.bind(on_release=lambda *_: popup.dismiss())
    layout.add_widget(cancel)
    popup.open()
    return popup
