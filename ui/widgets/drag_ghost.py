"""Floating translucent copy that follows a pointer during a drag."""

from kivy.core.window import Window
from kivy.graphics import Color, Line
from kivy.metrics import dp

from ui.theme import DRAG, FlatButton


class DragGhost(FlatButton):
    def __init__(self, text, size, **kwargs):
        super().__init__(
            text=text,
            kind='accent',
            size_hint=(None, None),
            size=size,
            opacity=0.7,
            **kwargs,
        )
        self.background_color = DRAG
        with self.canvas.after:
            Color(1, 1, 1, 0.35)
            self._halo = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(6)),
                width=1.4,
            )
        self.bind(pos=self._sync_halo, size=self._sync_halo)

    def _sync_halo(self, *_args):
        self._halo.rounded_rectangle = (
            self.x - 2,
            self.y - 2,
            self.width + 4,
            self.height + 4,
            dp(6),
        )

    def follow(self, pos):
        self.center = pos

    def attach(self, pos):
        if self.parent is None:
            Window.add_widget(self)
        self.follow(pos)

    def detach(self):
        if self.parent is not None:
            self.parent.remove_widget(self)
