"""
Note Model and Manager
Handles all note-related operations
"""

class Note:
    # Represents a single note
    
    def __init__(self, id=None, title='', content='', folder_id=None, created_at=None, updated_at=None):
        self.id = id;
        self.title = title;
        self.content = content; # Rich text stored as BBCode markup
        self.folder_id = folder_id;
        self.created_at = created_at;
        self.updated_at = updated_at;
    
    @classmethod
    def from_db_row(cls, row):
        # Create a Note instance from a database row
        return cls(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            folder_id=row['folder_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def to_dict(self):
        # Convert note to dictionary
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'folder_id': self.folder_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    

class NoteManager:
    # Manages note operations
    
    def __init__(self, db_manager):
        self.db = db_manager;
    
    def create_note(self, title, content='', folder_id=None):
        # Create a new note
        timestamp = self.db.get_timestamp();
        
        self.db.execute('''
            INSERT INTO notes (title, content, folder_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, folder_id, timestamp, timestamp));
        
        note_id = self.db.cursor.lastrowid;
        
        # Update FTS index
        self.db.execute('''
            INSERT INTO notes_fts (rowid, title, content)
            VALUES (?, ?, ?)
        ''', (note_id, title, content));
        
        self.db.commit();
        return note_id
    
    def get_note(self, note_id):
        # Get a note by ID
        self.db.execute('SELECT * FROM notes WHERE id = ?', (note_id,));
        row = self.db.fetchone();
        return Note.from_db_row(row) if row else None
    
    def update_note(self, note_id, title=None, content=None, folder_id=None):
        # Update an existing note
        timestamp = self.db.get_timestamp();
        
        # Build dynamic update query
        updates = [];
        params = [];
        
        if title is not None:
            updates.append('title = ?');
            params.append(title);
        
        if content is not None:
            updates.append('content = ?');
            params.append(content);
        
        if folder_id is not None:
            updates.append('folder_id = ?');
            params.append(folder_id);
        
        updates.append('updated_at = ?');
        params.append(timestamp);
        params.append(note_id);
        
        query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?";
        self.db.execute(query, params);
        
        # Update FTS index if title or content changed
        if title is not None or content is not None:
            fts_updates = [];
            fts_params = [];
            
            if title is not None:
                fts_updates.append('title = ?');
                fts_params.append(title);
            
            if content is not None:
                fts_updates.append('content = ?');
                fts_params.append(content);
            
            fts_params.append(note_id);
            fts_query = f"UPDATE notes_fts SET {', '.join(fts_updates)} WHERE rowid = ?";
            self.db.execute(fts_query, fts_params);
        
        self.db.commit();
    
    def delete_note(self, note_id):
        # Delete a note
        self.db.execute('DELETE FROM notes WHERE id = ?', (note_id,));
        self.db.execute('DELETE FROM notes_fts WHERE rowid = ?', (note_id,));
        self.db.commit();
    
    def get_all_notes(self, folder_id=None):
        # Get all notes, optionally filtered by folder
        if folder_id is not None:
            self.db.execute('''
                SELECT * FROM notes
                WHERE folder_id = ?
                ORDER BY updated_at DESC
            ''', (folder_id,));
        else:
            self.db.execute('''
                SELECT * FROM notes
                ORDER BY updated_at DESC
            ''');
        
        rows = self.db.fetchall();
        return [Note.from_db_row(row) for row in rows]
    
    def search_notes(self, query):
        # Search notes using full-text search
        self.db.execute('''
            SELECT notes.* FROM notes
            JOIN notes_fts ON notes.id = notes_fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY rank
        ''', (query,));
        
        rows = self.db.fetchall();
        return [Note.from_db_row(row) for row in rows]