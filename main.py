"""
Jotly - Simple Android note-taking and task management app
Main application entry point
"""

import os

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from database.db_manager import DatabaseManager
from models.attachment import AttachmentManager
from models.backup import BackupManager
from models.capture import CaptureService
from models.folder import FolderManager
from models.note import NoteManager
from models.tag import TagManager
from models.task import TaskManager
from ui.screens.main_screen import MainScreen
from ui.screens.note_editor import NoteEditorScreen
from ui.screens.task_list import TaskListScreen
from ui.theme import TRANSITION_DURATION, apply_window


class JotlyApp(App):
    """Main application class."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_manager = None
        self.note_manager = None
        self.task_manager = None
        self.folder_manager = None
        self.tag_manager = None
        self.attachment_manager = None
        self.capture = None
        self.backup = None
        self.pending_share = None

    def build(self):
        apply_window()
        os.makedirs(self.user_data_dir, exist_ok=True)
        db_path = os.path.join(self.user_data_dir, 'jotly.db')
        self.db_manager = DatabaseManager(db_path)

        self.note_manager = NoteManager(self.db_manager)
        self.task_manager = TaskManager(self.db_manager)
        self.folder_manager = FolderManager(self.db_manager)
        self.tag_manager = TagManager(self.db_manager)
        attach_dir = os.path.join(self.user_data_dir, 'attachments')
        self.attachment_manager = AttachmentManager(self.db_manager, attach_dir)
        self.capture = CaptureService(
            self.note_manager, self.tag_manager, self.attachment_manager
        )
        self.backup = BackupManager(
            self.db_manager,
            self.folder_manager,
            self.note_manager,
            self.task_manager,
            self.tag_manager,
            self.attachment_manager,
        )
        self.pending_share = _read_android_share()

        sm = ScreenManager(transition=SlideTransition(duration=TRANSITION_DURATION))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(NoteEditorScreen(name='note_editor'))
        sm.add_widget(TaskListScreen(name='task_list'))
        return sm

    def on_stop(self):
        if self.db_manager:
            self.db_manager.close()


def _read_android_share():
    """If Android launched Jotly via SEND, return the shared text or path."""
    try:
        from jnius import autoclass
    except Exception:
        return None
    try:
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        intent = activity.getIntent()
        action = intent.getAction()
        if not action or 'SEND' not in str(action):
            return None
        extras = intent.getExtras()
        if extras is None:
            return None
        text = extras.get('android.intent.extra.TEXT')
        subject = extras.get('android.intent.extra.SUBJECT')
        return {
            'text': str(text) if text else '',
            'subject': str(subject) if subject else '',
        }
    except Exception:
        return None


if __name__ == '__main__':
    JotlyApp().run()
