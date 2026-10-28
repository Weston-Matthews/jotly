"""Shared look-and-feel plus snappy screen switches."""

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.screenmanager import SlideTransition
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase
import os

# Bundle a font that includes arrows and basic symbols so glyphs render on every platform.
# Path is relative to the project root (works for desktop and when packaged).
_FONT_PATH = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts', 'DejaVuSans.ttf')
_FONT_PATH = os.path.normpath(_FONT_PATH)
if os.path.exists(_FONT_PATH):
    LabelBase.register(name='DejaVu', fn_regular=_FONT_PATH)
    DEFAULT_FONT = 'DejaVu'
else:
    DEFAULT_FONT = 'Roboto'  # Kivy default fallback

# Warm dark slate — reads as a notes app, not stock Kivy grey.
BG = (0.09, 0.10, 0.12, 1)
SURFACE = (0.16, 0.18, 0.22, 1)
SURFACE_ALT = (0.20, 0.22, 0.27, 1)
ROW_FOLDER = (0.17, 0.24, 0.34, 1)
ROW_NOTE = (0.18, 0.20, 0.25, 1)
ROW_TASK = (0.16, 0.22, 0.20, 1)
TEXT = (0.95, 0.95, 0.97, 1)
MUTED = (0.62, 0.64, 0.70, 1)
ACCENT = (0.95, 0.72, 0.22, 1)
PRIMARY = (0.27, 0.55, 0.92, 1)
PRIMARY_DOWN = (0.20, 0.42, 0.74, 1)
SUCCESS = (0.28, 0.72, 0.42, 1)
DANGER = (0.84, 0.30, 0.30, 1)
DANGER_DOWN = (0.68, 0.20, 0.20, 1)
HOLD = (0.22, 0.52, 0.95, 1)
DROP = (0.28, 0.72, 0.38, 1)
DRAG = (0.98, 0.82, 0.22, 1)
IDLE = SURFACE
HINT = (0.85, 0.82, 0.58, 1)

TRANSITION_DURATION = 0.12

KIND_COLORS = {
    'neutral': SURFACE_ALT,
    'folder': ROW_FOLDER,
    'note': ROW_NOTE,
    'task': ROW_TASK,
    'primary': PRIMARY,
    'accent': ACCENT,
    'success': SUCCESS,
    'danger': DANGER,
    'ghost': (0.22, 0.24, 0.28, 0.95),
}

KIND_DOWN = {
    'neutral': (0.12, 0.14, 0.17, 1),
    'folder': (0.13, 0.19, 0.28, 1),
    'note': (0.13, 0.15, 0.19, 1),
    'task': (0.12, 0.18, 0.16, 1),
    'primary': PRIMARY_DOWN,
    'accent': (0.78, 0.56, 0.12, 1),
    'success': (0.20, 0.56, 0.32, 1),
    'danger': DANGER_DOWN,
    'ghost': (0.16, 0.18, 0.22, 1),
}


def apply_window():
    if Window is not None:
        Window.clearcolor = BG


def switch_screen(manager, name, direction='left'):
    """Swap screens with a short slide so navigation feels instant."""
    if manager.current == name:
        return
    transition = manager.transition
    if isinstance(transition, SlideTransition):
        transition.duration = TRANSITION_DURATION
        transition.direction = direction
    manager.current = name


class FlatButton(Button):
    """Solid-color button with an immediate press darken (no atlas lag)."""

    def __init__(self, kind='neutral', **kwargs):
        self.kind = kind
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('color', TEXT)
        kwargs.setdefault('font_size', '15sp')
        kwargs.setdefault('font_name', DEFAULT_FONT)
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        super().__init__(**kwargs)
        self._base_color = KIND_COLORS.get(kind, SURFACE_ALT)
        self.background_color = self._base_color
        self.bind(state=self._on_state, size=self._fit_text)

    def set_kind(self, kind):
        self.kind = kind
        self._base_color = KIND_COLORS.get(kind, SURFACE_ALT)
        if self.state != 'down':
            self.background_color = self._base_color

    def _on_state(self, _instance, value):
        if value == 'down':
            self.background_color = KIND_DOWN.get(self.kind, KIND_DOWN['neutral'])
        else:
            self.background_color = self._base_color

    def _fit_text(self, *_args):
        if self.halign == 'left':
            self.text_size = (self.width - dp(16), self.height)
            self.padding = (dp(10), 0)


class FlatInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_active', '')
        kwargs.setdefault('background_color', SURFACE_ALT)
        kwargs.setdefault('foreground_color', TEXT)
        kwargs.setdefault('hint_text_color', MUTED)
        kwargs.setdefault('cursor_color', ACCENT)
        kwargs.setdefault('selection_color', (0.27, 0.55, 0.92, 0.35))
        kwargs.setdefault('padding', [dp(12), dp(12), dp(12), dp(12)])
        kwargs.setdefault('font_size', '16sp')
        kwargs.setdefault('font_name', DEFAULT_FONT)
        super().__init__(**kwargs)
        if not self.multiline:
            # A fixed height minus fixed 12dp padding leaves exactly one line of
            # room at 1.0 font scale; at Android font scale > 1 the line no longer
            # fits and TextInput toggles scroll_y on every keystroke ("bounce").
            self._min_height = self.height if self.size_hint_y is None else None
            self.bind(
                height=self._fit_single_line,
                line_height=self._fit_single_line,
                font_size=self._fit_single_line,
            )
            self._fit_single_line()

    def _fit_single_line(self, *_args):
        line_h = self.line_height
        if self._min_height is not None:
            wanted = max(self._min_height, line_h + dp(16))
            if abs(self.height - wanted) > 0.5:
                self.height = wanted  # re-enters via the height binding
                return
        pad_y = max(dp(2), (self.height - line_h) / 2.0)
        left, _top, right, _bottom = self.padding
        self.padding = [left, pad_y, right, pad_y]
        self.scroll_y = 0
