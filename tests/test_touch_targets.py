"""Real touch dispatch (not direct method calls) for the main-screen bottom bar.

Run: SDL_VIDEODRIVER=offscreen python -m pytest tests/test_touch_targets.py
"""

import os
import tempfile

os.environ.setdefault('KIVY_NO_ARGS', '1')
os.environ.setdefault('SDL_VIDEODRIVER', 'offscreen')

from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.tests.common import UnitTestTouch
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView

from main import JotlyApp


class TouchApp(JotlyApp):
    _dir = tempfile.mkdtemp(prefix='jotly-touch-')

    @property
    def user_data_dir(self):
        return self._dir


def _button(root, text):
    return next(b for b in root.walk() if isinstance(b, Button) and b.text == text)


def _tap(widget):
    touch = UnitTestTouch(*widget.to_window(*widget.center))
    touch.touch_down()
    touch.touch_up()
    for _ in range(10):
        EventLoop.idle()


def test_bottom_bar_buttons_receive_taps():
    app = TouchApp()
    results = {}

    def step(_dt):
        try:
            from kivy.core.window import Window

            sm = app.root
            main = sm.get_screen('main')
            _tap(_button(main, '+ Folder'))
            results['folder_popup'] = any(isinstance(c, ModalView) for c in Window.children)
            for c in list(Window.children):
                if isinstance(c, ModalView):
                    c.dismiss(animation=False)
            for _ in range(10):
                EventLoop.idle()
            folder_id = app.folder_manager.create_folder('Work')
            main.open_folder(app.folder_manager.get_folder(folder_id))
            _tap(_button(main, '← Up / Home'))
            results['up_went_home'] = main.current_folder is None
        finally:
            app.stop()

    Clock.schedule_once(step, 0.3)
    app.run()
    assert results.get('folder_popup'), '+ Folder tap did not open the prompt'
    assert results.get('up_went_home'), '← Up / Home tap did not leave the folder'
