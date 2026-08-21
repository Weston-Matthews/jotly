"""
Task List Screen - View and manage tasks
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.app import App


class TaskListScreen(Screen):
    # Screen for viewing ana managing tasks
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui();
    
    def build_ui(self):
        # Build the task list UI
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10);
        
        # Top bar
        top_bar = BoxLayout(size_hint_y=None, height=50, spacing=10);
        
        back_btn = Button(
            text='← Back',
            size_hint_x=0.5,
            on_press=self.go_back
        );
        top_bar.add_widget(back_btn)
        
        new_task_btn = Button(
            text='+ New Task',
            size_hint_x=0.5,
            on_press=self.create_task
        );
        top_bar.add_widget(new_task_btn);
        
        main_layout.add_widget(top_bar);
        
        # Title
        title = Label(
            text='Tasks',
            size_hint_y=None,
            height=40,
            font_size=24,
            halign='left'
        );
        title.bind(size=title.setter('text_size'));
        main_layout.add_widget(title);
        
        # Scrollable task list
        scroll = ScrollView();
        self.task_grid = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None,
            padding=5
        );
        self.task_grid.bind(minimum_height=self.task_grid.setter('height'));
        
        scroll.add_widget(self.task_grid);
        main_layout.add_widget(scroll);
        
        self.add_widget(main_layout);
    
    def on_enter(self):
        # Called when screen is entered
        self.refresh_tasks();
    
    def refresh_tasks(self):
        # Refresh the task list
        app = App.get_running_app();
        self.task_grid.clear_widgets();
        
        # Get all tasks
        tasks = app.task_manager.get_all_tasks(include_completed=True);
        
        for task in tasks:
            task_row = BoxLayout(
                size_hint_y=None,
                height=50,
                spacing=10
            );
            
            # Checkbox
            checkbox = CheckBox(
                active=task.completed,
                size_hint_x=None,
                width=50
            );
            checkbox.bind(active=lambda cb, value, t=task: self.toggle_task(t, value));
            task_row.add_widget(checkbox);
            
            # Task title
            task_label = Label(
                text=task.title,
                halign='left',
                valign='middle',
                text_size=(None, None)
            );
            task_label.bind(size=lambda l, v, tl=task_label: setattr(tl, 'text_size', (v[0], None)));
            
            # Strikethrough if completed
            if task.completed:
                task_label.text = f'[s]{task.title}[/s]';
                task_label.markup = True;
            
            task_row.add_widget(task_label);
            
            # Delete button
            delete_btn = Button(
                text='X',
                size_hint_x=None,
                width=50,
                background_color=(1, 0.3, 0.3, 1)
            );
            delete_btn.bind(on_press=lambda x, t=task: self.delete_task(t));
            task_row.add_widget(delete_btn);
            
            self.task_grid.add_widget(task_row);
        
        if not tasks:
            no_tasks = Label(
                text='No tasks yet. Create one!',
                size_hint_y=None,
                height=50
            );
            self.task_grid.add_widget(no_tasks);
        
    def toggle_task(self, task, completed):
        # Toggle task completion status
        app = App.get_running_app();
        app.task_manager.update_task(task.id, completed=completed);
        self.refresh_tasks();
    
    def delete_task(self, task):
        # Delete a task
        app = App.get_running_app();
        app.task_manager.delete_task(task.id);
        self.refresh_tasks();
    
    def create_task(self, instance):
        # Create a new task
        app = App.get_running_app();
        app.task_manager.create_task('New Task');
        self.refresh_tasks();
    
    def go_back(self, instance):
        # Return to the main screen
        self.manager.current = 'main';
        
        # Refresh main screen
        main_screen = self.manager.get_screen('main');
        main_screen.refresh_content();