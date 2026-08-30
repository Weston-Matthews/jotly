"""
Task Model and Manager
Handles all task-related operations
"""

UNSET = object()


class Task:
    def __init__(
        self,
        id=None,
        title='',
        description='',
        completed=False,
        folder_id=None,
        created_at=None,
        updated_at=None,
        due_date=None,
        starred=False,
        sort_order=0,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.completed = bool(completed)
        self.folder_id = folder_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.due_date = due_date
        self.starred = bool(starred)
        self.sort_order = sort_order if sort_order is not None else 0

    @classmethod
    def from_db_row(cls, row):
        keys = row.keys()
        return cls(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            completed=row['completed'],
            folder_id=row['folder_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            due_date=row['due_date'],
            starred=row['starred'] if 'starred' in keys else 0,
            sort_order=row['sort_order'] if 'sort_order' in keys else 0,
        )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'folder_id': self.folder_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'due_date': self.due_date,
            'starred': self.starred,
            'sort_order': self.sort_order,
        }


class TaskManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def _next_sort_order(self, folder_id):
        if folder_id is None:
            self.db.execute(
                'SELECT COALESCE(MAX(sort_order), -1) + 1 FROM tasks WHERE folder_id IS NULL'
            )
        else:
            self.db.execute(
                'SELECT COALESCE(MAX(sort_order), -1) + 1 FROM tasks WHERE folder_id = ?',
                (folder_id,),
            )
        row = self.db.fetchone()
        return row[0] if row else 0

    def create_task(self, title, description='', folder_id=None, due_date=None, starred=False):
        timestamp = self.db.get_timestamp()
        sort_order = self._next_sort_order(folder_id)
        self.db.execute(
            '''
            INSERT INTO tasks (
                title, description, completed, folder_id,
                created_at, updated_at, due_date, starred, sort_order
            )
            VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?)
            ''',
            (
                title,
                description,
                folder_id,
                timestamp,
                timestamp,
                due_date,
                1 if starred else 0,
                sort_order,
            ),
        )
        self.db.commit()
        return self.db.cursor.lastrowid

    def get_task(self, task_id):
        self.db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = self.db.fetchone()
        return Task.from_db_row(row) if row else None

    def update_task(
        self,
        task_id,
        title=UNSET,
        description=UNSET,
        completed=UNSET,
        folder_id=UNSET,
        due_date=UNSET,
        starred=UNSET,
        sort_order=UNSET,
    ):
        timestamp = self.db.get_timestamp()
        updates = []
        params = []

        if title is not UNSET:
            updates.append('title = ?')
            params.append(title)
        if description is not UNSET:
            updates.append('description = ?')
            params.append(description)
        if completed is not UNSET:
            updates.append('completed = ?')
            params.append(1 if completed else 0)
        if folder_id is not UNSET:
            updates.append('folder_id = ?')
            params.append(folder_id)
        if due_date is not UNSET:
            updates.append('due_date = ?')
            params.append(due_date or None)
        if starred is not UNSET:
            updates.append('starred = ?')
            params.append(1 if starred else 0)
        if sort_order is not UNSET:
            updates.append('sort_order = ?')
            params.append(sort_order)

        if not updates:
            return

        updates.append('updated_at = ?')
        params.append(timestamp)
        params.append(task_id)
        self.db.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        self.db.commit()

    def delete_task(self, task_id):
        self.db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.db.commit()

    def toggle_task(self, task_id):
        task = self.get_task(task_id)
        if task:
            self.update_task(task_id, completed=not task.completed)

    def toggle_star(self, task_id):
        task = self.get_task(task_id)
        if task:
            self.update_task(task_id, starred=not task.starred)

    def reorder_tasks(self, task_ids):
        """Persist a new manual order. Starred items still float to the top on read."""
        for index, task_id in enumerate(task_ids):
            self.db.execute(
                'UPDATE tasks SET sort_order = ?, updated_at = ? WHERE id = ?',
                (index, self.db.get_timestamp(), task_id),
            )
        self.db.commit()

    def get_all_tasks(self, folder_id=None, include_completed=True, unfiled_only=False):
        clauses = []
        params = []
        if folder_id is not None:
            clauses.append('folder_id = ?')
            params.append(folder_id)
        elif unfiled_only:
            clauses.append('folder_id IS NULL')
        if not include_completed:
            clauses.append('completed = 0')
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        order = (
            'starred DESC, sort_order ASC, completed ASC, '
            'CASE WHEN due_date IS NULL OR due_date = \'\' THEN 1 ELSE 0 END, '
            'due_date ASC, created_at DESC'
        )
        self.db.execute(f'SELECT * FROM tasks {where} ORDER BY {order}', params)
        rows = self.db.fetchall()
        return [Task.from_db_row(row) for row in rows]
