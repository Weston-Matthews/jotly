# NoteApp Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │              │  │              │  │              │         │
│  │ Main Screen  │  │ Note Editor  │  │  Task List   │         │
│  │              │  │              │  │              │         │
│  │ - Folders    │  │ - Title      │  │ - Checkboxes │         │
│  │ - Notes      │  │ - Rich Text  │  │ - Delete     │         │
│  │ - Tasks      │  │ - Formatting │  │ - Complete   │         │
│  │ - Search     │  │ - Save/Back  │  │ - Add Task   │         │
│  │              │  │              │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           │                                     │
│                  ┌────────▼────────┐                            │
│                  │                 │                            │
│                  │ Screen Manager  │                            │
│                  │  (Navigation)   │                            │
│                  │                 │                            │
│                  └────────┬────────┘                            │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      BUSINESS LOGIC                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │              │  │              │  │              │         │
│  │NoteManager   │  │TaskManager   │  │FolderManager │         │
│  │              │  │              │  │              │         │
│  │- create()    │  │- create()    │  │- create()    │         │
│  │- update()    │  │- update()    │  │- update()    │         │
│  │- delete()    │  │- delete()    │  │- delete()    │         │
│  │- search()    │  │- toggle()    │  │- get_path()  │         │
│  │- get_all()   │  │- get_all()   │  │- get_all()   │         │
│  │              │  │              │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                       DATA LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                   ┌─────────────────┐                           │
│                   │                 │                           │
│                   │  DatabaseManager│                           │
│                   │                 │                           │
│                   │ - execute()     │                           │
│                   │ - commit()      │                           │
│                   │ - fetchall()    │                           │
│                   │ - get_timestamp │                           │
│                   │                 │                           │
│                   └────────┬────────┘                           │
│                            │                                    │
│                   ┌────────▼────────┐                           │
│                   │                 │                           │
│                   │  SQLite Database│                           │
│                   │  (noteapp.db)   │                           │
│                   │                 │                           │
│                   │  Tables:        │                           │
│                   │  - notes        │                           │
│                   │  - tasks        │                           │
│                   │  - folders      │                           │
│                   │  - notes_fts    │                           │
│                   │                 │                           │
│                   └─────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘


DATA FLOW EXAMPLE - Creating a Note:
═══════════════════════════════════════

1. User taps "+ Note" button
   └─> MainScreen.create_new_note()

2. MainScreen calls manager
   └─> NoteManager.create_note(title, content, folder_id)

3. Manager interacts with database
   └─> DatabaseManager.execute(INSERT INTO notes...)
   └─> DatabaseManager.execute(INSERT INTO notes_fts...)
   └─> DatabaseManager.commit()

4. Manager returns note_id
   └─> MainScreen.open_note(note)

5. Screen navigation
   └─> ScreenManager switches to NoteEditorScreen

6. Editor loads note
   └─> NoteEditorScreen.load_note(note)
   └─> RichTextEditor displays content


KEY DESIGN PRINCIPLES:
═════════════════════

✓ Separation of Concerns
  - UI doesn't know about SQL
  - Managers don't know about UI widgets
  - Database handles only storage

✓ Single Responsibility
  - Each manager handles one entity type
  - Each screen handles one view
  - DatabaseManager only manages connections

✓ Data Encapsulation
  - All DB access through managers
  - Models represent data cleanly
  - No direct SQL in UI code

✓ Performance First
  - SQLite indexes on key columns
  - FTS5 for instant search
  - Minimal UI redraws
  - Local storage (no network lag)