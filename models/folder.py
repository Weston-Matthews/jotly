"""
Folder Model and Manager
Handles all folder/notebook-related operations
"""


class Folder:
    # Represents a folder/notebook
    
    def __init__(self, id=None, name='', parent_id=None, created_at=None, updated_at=None):
        self.id = id;
        self.name = name;
        self.parent_id = parent_id;
        self.created_at = created_at;
        self.updated_at = updated_at;
    
    @classmethod
    def from_db_row(cls, row):
        # Create a folder instance from a database row
        return cls(
            id=row['id'],
            name=row['name'],
            parent_id=row['parent_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def to_dict(self):
        # Convert folder to dictionary
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class FolderManager:
    #Manages folder operations
    
    def __init__(self, db_manager):
        self.db = db_manager;
    
    def create_folder(self, name, parent_id=None):
        # Create a new folder
        timestamp = self.db.get_timestamp();
        
        self.db.execute('''
            INSERT INTO folders (name, parent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (name, parent_id, timestamp, timestamp));
        
        self.db.commit();
        return self.db.cursor.lastrowid
    
    def get_folder(self, folder_id):
        # Get a folder by id
        self.db.execute('SELECT * FROM folders WHERE id = ?', (folder_id,));
        row = self.db.fetchone();
        return Folder.from_db_row(row) if row else None
    
    def update_folder(self, folder_id, name=None, parent_id=None):
        # Update an existing folder
        timestamp = self.db.get_timestamp();
        
        updates = [];
        params = [];
        
        if name is not None:
            updates.append('name = ?');
            params.append(name);
        
        if parent_id is not None:
            updates.append('parent_id = ?');
            params.append(parent_id);
        
        updates.append('updates_at = ?');
        params.append(timestamp);
        params.append(folder_id);
        
        query = f"UPDATE folders SET {', '.join(updates)} WHERE id = ?";
        self.db.execute(query, params);
        self.db.commit();
    
    def delete_folder(self, folder_id):
        # Delete a folder (notes/tasks inside will have their folder_id set to NULL
        self.db.execute('DELETE FROM folders WHERE id = ?', (folder_id,));
        self.db.commit();
    
    def get_all_folders(self, parent_id=None):
        # Get all folders, optionally filtering by parent
        if parent_id is not None:
            self.db.execute('''
                SELECT * FROM folders
                WHERE parent_id = ?
                ORDER BY name ASC
            ''', (parent_id,));
        else:
            # Get root folders (no parent)
            self.db.execute('''
                SELECT * FROM folders
                WHERE parent_id is NULL
                ORDER by name ASC
            ''');
        
        rows = self.db.fetchall();
        return [Folder.from_db_row(row) for row in rows]
    
    def get_folder_path(self, folder_id):
        # Get the full path of a folder (for breadcrumb navigation
        path = [];
        current_id = folder_id;
        
        while current_id is not None:
            folder = self.get_folder(current_id);
            if folder:
                path.insert(0, folder);
                current_id = folder.parent_id;
            else:
                break;
        
        return path;