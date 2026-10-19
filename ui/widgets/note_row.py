"""Note and folder row widgets used by the main screen list."""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout

from models.note import NoteManager
from ui.theme import FlatButton


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


def note_label(note):
    """Title, up to four tags, and a short content preview."""
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


def note_row(note, host, draggable=True):
    """Note button (draggable or plain) plus a Rename button."""
    row = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(6))
    if draggable:
        note_btn = DraggableNoteButton(
            note,
            host,
            text=note_label(note),
            halign='left',
            valign='middle',
        )
    else:
        note_btn = FlatButton(
            text=note_label(note),
            kind='note',
            halign='left',
            valign='middle',
        )
        note_btn.bind(on_press=lambda _x, n=note: host.open_note(n))
    rename_btn = FlatButton(text='Rename', kind='ghost', size_hint_x=None, width=dp(88))
    rename_btn.bind(on_press=lambda _x, n=note: host.rename_note(n))
    row.add_widget(note_btn)
    row.add_widget(rename_btn)
    return row
