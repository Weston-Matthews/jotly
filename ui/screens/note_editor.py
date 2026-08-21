"""
Note Editor Screen - Edit notes with rich text formatting
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.app import App
from ui.widgets.rich_text_editor import RichTextEditor


class NoteEditorScreen(Screen):
    # Screen for editing notes
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_note = None;
        self.build_ui();
    
    def build_ui(self):
        # Build the editor UI
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10);
        
        # Top bar with back and save buttons
        top_bar = BoxLayout(size_hint_y=None, height=50, spacing=10);
        
        back_btn = Button(
            text='← Back',
            size_hint_x=0.3,
            on_press=self.go_back
        );
        top_bar.add_widget(back_btn);
        
        save_btn = Button(
            text='Save',
            size_hint_x=0.3,
            on_press=self.save_note
        );
        top_bar.add_widget(save_btn);
        
        delete_btn = Button(
            text='Delete',
            size_hint_x=0.4,
            on_press=self.delete_note,
            background_color=(1, 0.3, 0.3, 1)
        );
        top_bar.add_widget(delete_btn);
        
        main_layout.add_widget(top_bar);
        
        # Title input
        self.title_input = TextInput(
            hint_text='Note Title',
            multiline=False,
            size_hint_y=None,
            height=50,
            font_size=20
        );
        main_layout.add_widget(self.title_input);
        
        # Rich text editor
        self.editor = RichTextEditor();
        main_layout.add_widget(self.editor);
        
        self.add_widget(main_layout);
    
    def load_note(self, note):
        # Load a note into the editor
        self.current_note = note;
        self.title_input.text = note.title;
        self.editor.set_text(note.content or '');
    
    def save_note(self, instance):
        # Save the current note
        if self.current_note is None:
            return
        
        app = App.get_running_app();
        
        title = self.title_input.text.strip();
        content = self.editor.get_text();
        
        if not title:
            title = 'Untitled Note';
        
        app.note_manager.update_note(
            self.current_note.id,
            title=title,
            content=content
        );
        
        # Show feedback (you could add a popup here)
        print(f"Note '{title} saved!");
        
    def delete_note(self, instance):
        # Delete the current note
        if self.current_note is None:
            return
        
        app = App.get_running_app();
        app.note_manager.delete_note(self.current_note.id);
        
        # Go back to the main screen
        self.go_back(instance);
    
    def go_back(self, instance):
        # Return to main screen
        # Auto-sae before leaving
        if self.current_note:
            self.save_note(instance);
        
        self.manager.current = 'main';
        
        # Refresh main screen
        main_screen = self.manager.get_screen('main');
        main_screen.refresh_content();
    
    def on_leave(self):
        # Called when leaving the screen
        # Clear editor
        self.current_note = None;
        self.title_input.text = '';
        self.editor.clear();