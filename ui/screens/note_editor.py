"""
Note Editor Screen - Edit notes with rich text formatting
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ui.theme import MUTED, SURFACE, TEXT, FlatButton, FlatInput, switch_screen
from ui.widgets.dialogs import prompt_text
from ui.widgets.folder_picker import pick_folder
from ui.widgets.rich_text_editor import RichTextEditor


class NoteEditorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_note = None
        self._save_flash = None
        self.build_ui()

    def build_ui(self):
        main_layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        top_bar.add_widget(FlatButton(text='← Back', kind='neutral', size_hint_x=0.25, on_press=self.go_back))
        self.save_btn = FlatButton(text='Save', kind='primary', size_hint_x=0.25, on_press=self.save_note)
        top_bar.add_widget(self.save_btn)
        top_bar.add_widget(FlatButton(text='Move…', kind='neutral', size_hint_x=0.25, on_press=self.move_note))
        top_bar.add_widget(
            FlatButton(text='Delete', kind='danger', size_hint_x=0.25, on_press=self.delete_note)
        )
        main_layout.add_widget(top_bar)

        self.title_input = FlatInput(
            hint_text='Note Title',
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size='20sp',
        )
        main_layout.add_widget(self.title_input)

        tag_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        tag_row.add_widget(FlatButton(text='+ Tag', kind='ghost', size_hint_x=None, width=dp(72), on_press=self.add_tag))
        self.tag_scroll = ScrollView(do_scroll_y=False, bar_width=0)
        self.tag_box = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=dp(6))
        self.tag_box.bind(minimum_width=self.tag_box.setter('width'))
        self.tag_scroll.add_widget(self.tag_box)
        tag_row.add_widget(self.tag_scroll)
        main_layout.add_widget(tag_row)

        self.editor = RichTextEditor()
        main_layout.add_widget(self.editor)

        attach_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        attach_row.add_widget(
            FlatButton(text='Attach', kind='ghost', size_hint_x=None, width=dp(88), on_press=self.pick_attachment)
        )
        self.attach_label = Label(text='', color=MUTED, font_size='13sp', halign='left', valign='middle')
        self.attach_label.bind(size=self.attach_label.setter('text_size'))
        attach_row.add_widget(self.attach_label)
        main_layout.add_widget(attach_row)

        self.add_widget(main_layout)

    def load_note(self, note):
        self.current_note = note
        self.title_input.text = note.title
        self.editor.set_text(note.content or '')
        self.save_btn.text = 'Save'
        self.save_btn.set_kind('primary')
        self.refresh_tags()
        self.refresh_attachments()

    def refresh_tags(self):
        self.tag_box.clear_widgets()
        if self.current_note is None:
            return
        app = App.get_running_app()
        for tag in app.tag_manager.get_note_tags(self.current_note.id):
            btn = FlatButton(
                text=f'#{tag.name}  ×',
                kind='ghost',
                size_hint_x=None,
                width=dp(max(88, 14 * len(tag.name) + 48)),
            )
            btn.bind(on_press=lambda _x, t=tag: self.remove_tag(t))
            self.tag_box.add_widget(btn)

    def refresh_attachments(self):
        if self.current_note is None:
            self.attach_label.text = ''
            return
        items = App.get_running_app().attachment_manager.list_for_note(self.current_note.id)
        if not items:
            self.attach_label.text = 'No files attached'
            return
        names = ', '.join(item.filename for item in items)
        self.attach_label.text = names

    def add_tag(self, _instance=None):
        if self.current_note is None:
            return

        def _save(name):
            if name:
                App.get_running_app().tag_manager.add_tag_to_note(self.current_note.id, name)
                self.refresh_tags()

        prompt_text('Add tag', '', _save, hint='work, recipes, #ideas')

    def remove_tag(self, tag):
        if self.current_note is None:
            return
        App.get_running_app().tag_manager.remove_tag_from_note(self.current_note.id, tag.id)
        self.refresh_tags()

    def pick_attachment(self, _instance=None):
        if self.current_note is None:
            return
        layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
        chooser = FileChooserListView(path='.', filters=['*'])
        layout.add_widget(chooser)
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = FlatButton(text='Cancel', kind='ghost')
        attach = FlatButton(text='Attach selected', kind='primary')
        buttons.add_widget(cancel)
        buttons.add_widget(attach)
        layout.add_widget(buttons)
        popup = Popup(
            title='Attach a file',
            content=layout,
            size_hint=(0.92, 0.8),
            title_color=TEXT,
            background='',
            background_color=SURFACE,
        )

        def _close(_x=None):
            popup.dismiss()

        def _attach(_x=None):
            if chooser.selection:
                App.get_running_app().attachment_manager.attach_file(
                    self.current_note.id, chooser.selection[0]
                )
                self.refresh_attachments()
            popup.dismiss()

        cancel.bind(on_press=_close)
        attach.bind(on_press=_attach)
        popup.open()

    def save_note(self, instance):
        if self.current_note is None:
            return

        app = App.get_running_app()
        title = self.title_input.text.strip() or 'Untitled Note'
        content = self.editor.get_text()
        app.note_manager.update_note(
            self.current_note.id,
            title=title,
            content=content,
        )
        self.current_note.title = title
        self.current_note.content = content
        self._flash_saved()

    def _flash_saved(self):
        if self._save_flash is not None:
            self._save_flash.cancel()
        self.save_btn.text = 'Saved'
        self.save_btn.set_kind('success')

        def _reset(_dt):
            self.save_btn.text = 'Save'
            self.save_btn.set_kind('primary')
            self._save_flash = None

        self._save_flash = Clock.schedule_once(_reset, 0.7)

    def move_note(self, _instance=None):
        if self.current_note is None:
            return

        def _move(folder_id):
            app = App.get_running_app()
            app.note_manager.move_note(self.current_note.id, folder_id)
            self.current_note.folder_id = folder_id

        pick_folder('Move note to…', self.current_note.folder_id, _move)

    def delete_note(self, instance):
        if self.current_note is None:
            return
        app = App.get_running_app()
        app.attachment_manager.delete_for_note(self.current_note.id)
        app.note_manager.delete_note(self.current_note.id)
        self.current_note = None
        switch_screen(self.manager, 'main', 'right')

    def go_back(self, instance):
        if self.current_note:
            self.save_note(instance)
        switch_screen(self.manager, 'main', 'right')

    def on_leave(self):
        self.current_note = None
        self.title_input.text = ''
        self.editor.clear()
        self.tag_box.clear_widgets()
        self.attach_label.text = ''
