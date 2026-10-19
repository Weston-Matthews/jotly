"""Drag-and-drop note filing: ghost, hold-to-browse, and drop handling."""

from kivy.app import App
from kivy.clock import Clock

from ui.theme import DROP, HOLD
from ui.widgets.drag_ghost import DragGhost

HOLD_SECONDS = 0.7


class NoteDragController:
    """Owns drag state and hit-testing for the main screen.

    The host (MainScreen) supplies the widgets and data the controller
    paints and moves against:
      folder_drop_targets, home_drop_target, folder_tray, drag_hint,
      current_folder
    """

    def __init__(self, host):
        self.host = host
        self._hold_event = None
        self._hold_target = None
        self._highlighted = []
        self._hover_widget = None
        self._ghost = None

    def begin_note_drag(self, note_btn):
        self.host.drag_hint.text = (
            'Drop on a folder  ·  hold ← Up to browse  ·  release elsewhere to cancel'
        )
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
        for btn in self.host.folder_drop_targets:
            if idle:
                btn.set_kind('folder')
            else:
                btn.background_color = (0.28, 0.36, 0.48, 1)
        if self.host.home_drop_target:
            if idle:
                self.host.home_drop_target.set_kind('neutral')
            else:
                self.host.home_drop_target.background_color = (0.28, 0.36, 0.48, 1)

    def _clear_highlights(self):
        self._hover_widget = None
        for widget in self._highlighted:
            if hasattr(widget, 'set_kind'):
                widget.set_kind(getattr(widget, 'kind', 'neutral'))
            else:
                widget.background_color = (1, 1, 1, 1)
        self._highlighted = []
        self._paint_targets(idle=True)
        for chip in getattr(self.host.folder_tray, 'chips', []):
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

    @staticmethod
    def _touch_hits(widget, touch):
        return widget.collide_point(*widget.to_widget(*touch.pos))

    def on_note_drag(self, touch):
        target_key = None
        open_parent = None

        chip = (
            self.host.folder_tray.chip_under(touch)
            if self.host.folder_tray.is_open()
            else None
        )
        hover = None
        hover_color = DROP
        hint = 'Release to cancel'

        if chip is not None:
            target_key = ('chip', chip.folder_id)
            open_parent = chip.folder_id
            hover = chip
            hint = f'Drop to move into {chip.text.replace("📁", "").replace("⌂", "").strip()}'
        elif self.host.home_drop_target and self._touch_hits(self.host.home_drop_target, touch):
            target_key = ('up', None)
            hover = self.host.home_drop_target
            hover_color = HOLD
            hint = 'Hold to browse folders  ·  drop now to move to parent / Home'
            if self.host.current_folder is None:
                open_parent = None
            else:
                folder = App.get_running_app().folder_manager.get_folder(self.host.current_folder)
                open_parent = folder.parent_id if folder else None
        else:
            for folder_btn in self.host.folder_drop_targets:
                if self._touch_hits(folder_btn, touch):
                    hover = folder_btn
                    hint = f'Drop to move into {folder_btn.folder.name}'
                    break

        if hover is not self._hover_widget:
            self._clear_highlights()
            self._paint_targets(idle=False)
            if hover is not None:
                self._highlight(hover, hover_color)
        self.host.drag_hint.text = hint

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
            self.host.folder_tray.show(parent_id)
        elif kind == 'chip':
            children = App.get_running_app().folder_manager.get_all_folders(folder_id)
            if folder_id is None:
                self.host.folder_tray.show(None)
            elif children:
                self.host.folder_tray.show(folder_id)

    def drop_note(self, note, touch):
        app = App.get_running_app()
        self._cancel_hold()
        self._clear_highlights()
        self.host.drag_hint.text = ''

        chip = (
            self.host.folder_tray.chip_under(touch)
            if self.host.folder_tray.is_open()
            else None
        )
        if chip is not None:
            app.note_manager.move_note(note.id, chip.folder_id)
            self.host.folder_tray.hide()
            return

        for folder_btn in self.host.folder_drop_targets:
            if self._touch_hits(folder_btn, touch):
                app.note_manager.move_note(note.id, folder_btn.folder.id)
                self.host.folder_tray.hide()
                return

        if self.host.home_drop_target and self._touch_hits(self.host.home_drop_target, touch):
            target = None
            if self.host.current_folder is not None:
                folder = app.folder_manager.get_folder(self.host.current_folder)
                target = folder.parent_id if folder else None
            app.note_manager.move_note(note.id, target)

        self.host.folder_tray.hide()
