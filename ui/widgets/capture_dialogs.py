"""Clip, attach, export, and import dialogs for the main screen."""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup

from ui.theme import SURFACE, TEXT, FlatButton
from ui.widgets.dialogs import prompt_text


def clip_inbox(host):
    """Prompt for text or a URL and open the resulting note."""

    def _save(text):
        if not text:
            return
        app = App.get_running_app()
        note_id = app.capture.capture_text(text, folder_id=host.current_folder)
        if note_id:
            host.refresh_content()
            host.open_note(app.note_manager.get_note(note_id))

    prompt_text('Clip text or a URL', '', _save, hint='Paste a link or a thought')


def clip_file(host):
    """File chooser that creates a new note with the selected file attached."""
    layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
    chooser = FileChooserListView(path='.')
    layout.add_widget(chooser)
    buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
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
                chooser.selection[0], folder_id=host.current_folder
            )
            popup.dismiss()
            if note_id:
                host.refresh_content()
                host.open_note(app.note_manager.get_note(note_id))
            return
        popup.dismiss()

    cancel.bind(on_press=_close)
    attach.bind(on_press=_go)
    popup.open()


def export_archive(host):
    """Prompt for a filename and write a zip under the app data directory."""
    app = App.get_running_app()
    dest = app.user_data_dir

    def _save(name):
        filename = name or 'jotly-backup.zip'
        if not filename.endswith('.zip'):
            filename += '.zip'
        path = filename if filename.startswith('/') else f'{dest}/{filename}'
        app.backup.export_archive(path)
        host.drag_hint.text = f'Exported to {path}'

    prompt_text('Export archive', 'jotly-backup.zip', _save, hint='Filename in app storage')


def import_archive(host):
    """Zip chooser that restores an archive and refreshes the list."""
    layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
    chooser = FileChooserListView(path=App.get_running_app().user_data_dir, filters=['*.zip'])
    layout.add_widget(chooser)
    buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
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
            host.drag_hint.text = (
                f"Imported {counts['notes']} notes, {counts['tasks']} tasks"
            )
            host.refresh_content()
        popup.dismiss()

    cancel.bind(on_press=_close)
    load.bind(on_press=_go)
    popup.open()
