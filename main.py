"""
Jotly - Simple Android Note-Taking and Task Managment App
Main application entry point
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from database.db_manager import DatabaseManager
from models.note import NoteManager
from models.task import TaskManager
from models.folder import FolderManager

# Import screens
from ui.screens.main_screen import MainScreen
from ui.screens.note_editor import NoteEditorScreen
from ui.screens.task_list import TaskListScreen

class JotlyApp(App):
    # Main application class
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs);
        self.db_manager = None;
        self.note_manager = None;
        self.task_manager = None;
        self.folder_manager = None;
    
    def build(self):
        # Build and return the root widget
        # Initialize database
        self.db_manager = DatabaseManager();
        
        # Initialize managers
        self.note_manager = NoteManager(self.db_manager);
        self.task_manager = TaskManager(self.db_manager);
        self.folder_manager = FolderManager(self.db_manager);
        
        # Create screen manager
        sm = ScreenManager();
        sm.add_widget(MainScreen(name='main'));
        sm.add_widget(NoteEditorScreen(name='note_editor'));
        sm.add_widget(TaskListScreen(name='task_list'));
        
        return sm
    
    def on_stop(self):
        # Clean up when app is closed
        if self.db_manager:
            self.db_manager.close()
    
if __name__ == '__main__':
    JotlyApp().run()