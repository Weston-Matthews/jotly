"""
Task Model and Manager
Handles all task-related operations
"""


class Task:
    # Represents a single task
    
    def __init__(self, id=None, title='', description='', completed=False, folder_id=None, created_at=None, updated_at=None, due_date=None):
        self.id = id;
        self.title = title;
        self.description = description;
        self.completed = completed;
        self.folder_id = folder_id;
        self.created_at = created_at;
        self.updated_at = updated_at;
        self.due_date = due_date;
        
    @classmethod
    def from_db_row(cls, row):
        # Create a Task instance from a database row
        return cls(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            completed=row['completed'],
            folder_id=row['folder_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            due_date=row['due_date']
        )
    
    def to_dict(self):
        # Convert task to dictionary
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'folder_id': self.folder_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'due_date': self.due_date
        }

class TaskManager:
    # Manages task operations
    
    def __init__(self, db_manager):
        self.db = db_manager;
    
    def create_task(self, title, description='', folder_id=None, due_date=None):
        # Creates a new task
        timestamp = self.db.get_timestamp();
        
        self.db.execute('''
            INSERT INTO tasks (title, description, completed, folder_id, created_at, updated_at, due_date)
            VALUES (?, ?, 0, ?, ?, ?, ?)
        ''', (title, description, folder_id, timestamp, timestamp, due_date));
        
        self.db.commit();
        return self.db.cursor.lastrowid
    
    def get_task(self, task_id):
        # Get a task by ID
        self.db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,));
        row = self.db.fetchone();
        return Task.from_db_row(row) if row else None
    
    def update_task(self, task_id, title=None, description=None, completed=None, folder_id=None, due_date=None):
        # Update an existing task
        timestamp = self.db.get_timestamp();
        
        # Build dynamic update query
        updates = [];
        params = [];
        
        if title is not None:
            updates.append('title = ?');
            params.append(title);
            
        if description is not None:
            updates.append('description = ?');
            params.append(description);
        
        if completed is not None:
            updates.append('completed = ?');
            params.append(completed);
        
        if folder_id is not None:
            updates.append('folder_id = ?');
            params.append(folder_id);
        
        if due_date is not None:
            updates.append('due_date = ?');
            params.append(due_date);
        
        updates.append('updated_at = ?');
        params.append(timestamp);
        params.append(task_id);
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?";
        self.db.execute(query, params);
        self.db.commit();
    
    def delete_task(self, task_id):
        # Deletes a task
        self.db.execute('DELETE FROM tasks WHERE id = ?', (task_id,));
        self.db.commit();
    
    def toggle_task(self, task_id):
        # Toggle task completed status
        task = self.get_task(task_id);
        if task:
            self.update_task(task_id, completed=not task.completed);
    
    def get_all_tasks(self, folder_id=None, include_completed=True):
        # Get all tasks, optionally filtered by folder and completion status
        if folder_id is not None:
            if include_completed:
                self.db.execute('''
                    SELECT * FROM tasks
                    WHERE folder_id = ?
                    ORDER BY completed ASC, created_at DESC
                ''', (folder_id,));
            else:
                self.db.execute('''
                    SELECT * FROM tasks
                    WHERE folder_id = ? AND completed = 0
                    ORDER BY created_at DESC
                ''', (folder_id,));
        else:
            if include_completed:
                self.db.execute('''
                    SELECT * FROM tasks
                    ORDER BY completed ASC, created_at DESC
                ''');
            else:
                self.db.execute('''
                    SELECT * FROM tasks
                    WHERE completed = 0
                    ORDER BY created_at DESC
                ''')
        
        rows = self.db.fetchall();
        return [Task.from_db_row(row) for row in rows]