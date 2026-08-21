"""
Main Screen - Shows list of folders, notes, and tasks
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.app import App
from datetime import date


class MainScreen(Screen):
    # Main screen showing folders and items
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_folder = None;
        self.build_ui();
    
    def build_ui(self):
        # Build the main UI
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title and Today's Date
        top_title = BoxLayout(orientation='vertical', height=5, spacing=1);
        
        app_title = Label(
                text='Jotly',
                font_size='30sp',
                size_hint=(.7, 1),
                halign='center',
                valign='center'
            );
        top_title.add_widget(app_title);
        
        today = date.today();
        today_str = today.strftime('%A, %B %d, %Y');
        app_title_date = Label(
                text=today_str,
                size_hint=(.3, 1),
                halign='center',
                valign='center'
            );
        
        top_title.add_widget(app_title_date);
        main_layout.add_widget(top_title);
        
        # Top bar with search and new buttons
        top_bar = BoxLayout(size_hint_y=None, height=50, spacing=10);
        
        self.search_input = TextInput(
            hint_text='search notes...',
            multiline=False,
            size_hint_x=0.6
        );
        self.search_input.bind(on_text_validate=self.search_notes);
        top_bar.add_widget(self.search_input);
        
        new_note_btn = Button(
            text='+ Note',
            size_hint_x=0.2,
            on_press=self.create_new_note
        );
        top_bar.add_widget(new_note_btn);
        
        new_task_btn = Button(
            text='+ Task',
            size_hint_x=0.2,
            on_press=self.create_new_task
        );
        top_bar.add_widget(new_task_btn);
        
        main_layout.add_widget(top_bar);
        
        # Breadcrumb navigation
        self.breadcrumb = Label(
            text='All Items',
            size_hint_y=None,
            height=30,
            halign='left'
        );
        self.breadcrumb.bind(size=self.breadcrumb.setter('text_size'));
        main_layout.add_widget(self.breadcrumb);
        
        # Scrollable content area
        scroll = ScrollView();
        self.content_grid = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None,
            padding=5
        );
        self.content_grid.bind(minimum_height=self.content_grid.setter('height'));
        
        scroll.add_widget(self.content_grid);
        main_layout.add_widget(scroll);
        
        # Bottom bar with folder button
        bottom_bar = BoxLayout(size_hint_y=None, height=50, spacing=10);
        
        new_folder_btn = Button(
            text='+ Folder',
            on_press=self.create_new_folder
        );
        bottom_bar.add_widget(new_folder_btn);
        
        main_layout.add_widget(bottom_bar);
        
        self.add_widget(main_layout);
    
    def on_enter(self):
        # Called when screen is entered
        self.refresh_content();
    
    def refresh_content(self):
        # Refresh the content grid with folders and items
        app = App.get_running_app();
        self.content_grid.clear_widgets();
        
        # Get folders
        folders = app.folder_manager.get_all_folders(self.current_folder);
        
        for folder in folders:
            folder_btn = Button(
                text=f'📁 {folder.name}',
                size_hint_y=None,
                height=50,
                halign='left',
                valign='middle'
            );
            folder_btn.bind(size=folder_btn.setter('text_size'));
            folder_btn.bind(on_press=lambda x, f=folder: self.open_folder(f));
            self.content_grid.add_widget(folder_btn);
        
        # Get notes
        notes = app.note_manager.get_all_notes(self.current_folder);
        
        for note in notes:
            note_btn = Button(
                text=f'📝 {note.title}',
                size_hint_y=None,
                height=50,
                halign='left',
                valign='middle'
            );
            note_btn.bind(size=note_btn.setter('text_size'));
            note_btn.bind(on_press=lambda x, n=note: self.open_note(n));
            self.content_grid.add_widget(note_btn);
        
        # Get tasks
        tasks = app.task_manager.get_all_tasks(self.current_folder, include_completed=False);
        
        for task in tasks:
            task_btn = Button(
                text=f'☐ {task.title}',
                size_hint_y=None,
                height=50,
                halign='left',
                valign='middle'
            );
            task_btn.bind(size=task_btn.setter('text_size'));
            task_btn.bind(on_press=lambda x, t=task: self.open_task(t));
            self.content_grid.add_widget(task_btn);
        
        # Update breadcrumb
        self.update_breadcrumb();
    
    def update_breadcrumb(self):
        # Update breadcrumb navigation
        if self.current_folder is None:
            self.breadcrumb.text = 'All Items';
        else:
            app = App.get_running_app();
            path = app.folder_manager.get_folder_path(self.current_folder);
            path_text = ' > '.join([f.name for f in path]);
            self.breadcrumb.text = path_text;
    
    def open_folder(self, folder):
        # Open a folder
        self.current_folder = folder.id;
        self.refresh_content();
    
    def open_note(self, note):
        # Open note editor
        app = App.get_running_app();
        editor_screen = self.manager.get_screen('note_editor');
        editor_screen.load_note(note);
        self.manager.current = 'note_editor';
    
    def open_task(self, task):
        # Open task list
        self.manager.current = 'task_list';
    
    def create_new_note(self, instance):
        # Create a new note
        app = App.get_running_app();
        note_id = app.note_manager.create_note('Untitled Note', '', self.current_folder);
        note = app.note_manager.get_note(note_id);
        self.open_note(note);
    
    def create_new_task(self, instance):
        # Create a new task
        app = App.get_running_app();
        app.task_manager.create_task('New Task', '', self.current_folder);
        self.refresh_content();
    
    def create_new_folder(self, instance):
        # Create a new folder
        app = App.get_running_app();
        app.folder_manager.create_folder('New Folder', self.current_folder);
        self.refresh_content();
    
    def search_notes(self, instance):
        # Search for notes
        query = self.search_input.text.strip();
        if not query:
            self.refresh_content();
            return
        
        app = App.get_running_app();
        self.content_grid.clear_widgets();
        
        # Search notes
        notes = app.note_manager.search_notes(query);
        
        for note in notes:
            note_btn = Button(
                text=f'📝 {note.title}',
                size_hint_y=None,
                height=50,
                halign='left',
                valign='middle'
            );
            note_btn.bind(size=note_btn.setter('text_size'));
            note_btn.bind(on_press=lambda x, n=note: self.open_note(n));
            self.content_grid.add_widget(note_btn);
            
        if not notes:
            no_results = Label(
                text='No results found',
                size_hint_y=None,
                height=50
            );
            self.content_grid.add_widget(no_results);