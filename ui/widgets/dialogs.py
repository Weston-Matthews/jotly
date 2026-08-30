"""Simple text prompt popups used for rename and due dates."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

from ui.theme import SURFACE, TEXT, FlatButton, FlatInput


def prompt_text(title, initial, on_confirm, hint=''):
    layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
    field = FlatInput(text=initial or '', multiline=False, hint_text=hint)
    layout.add_widget(field)

    buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    cancel = FlatButton(text='Cancel', kind='ghost')
    save = FlatButton(text='Save', kind='primary')
    buttons.add_widget(cancel)
    buttons.add_widget(save)
    layout.add_widget(buttons)

    popup = Popup(
        title=title,
        content=layout,
        size_hint=(0.85, 0.35),
        separator_color=(0.95, 0.72, 0.22, 0.6),
        title_color=TEXT,
        background='',
        background_color=SURFACE,
    )

    def _close(_instance=None):
        popup.dismiss()

    def _save(_instance=None):
        on_confirm(field.text.strip())
        popup.dismiss()

    cancel.bind(on_press=_close)
    save.bind(on_press=_save)
    field.bind(on_text_validate=_save)
    popup.open()
    field.focus = True
    return popup
