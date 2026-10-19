# main_screen.py Extraction Spec

Status: implemented and pushed (commit e31c93a)  
Source: `ui/screens/main_screen.py` (was ~640 lines; now ~320)  
Goal: thin the screen into a coordinator + focused widgets so later work (due-date banner, richer lists) is safer.

## Why extract

`MainScreen` currently owns:

- Full layout construction
- Drag-and-drop note filing (touch, ghost, hold timer, drop targets, folder tray)
- List building (folders, notes, tasks, empty state, search results)
- Capture (clip text/URL, attach file)
- Backup (export / import popups)
- Navigation and breadcrumbs
- Android share consumption

The drag machinery and the row builders are the largest, most self-contained pieces. Extracting them leaves a screen that mostly wires buttons and calls `refresh_content()`.

## Current inventory

### Classes defined in the file

| Class | Role | Key state / methods |
|---|---|---|
| `DropFolderButton` | Folder row that can receive a dragged note | `folder`, `is_drop_target` |
| `DraggableNoteButton` | Note row: tap to open, drag to move | `note`, `host`, `_dragging`, `_origin`; `on_touch_down/move/up` |
| `MainScreen` | Screen coordinator | See methods below |

### MainScreen instance state

| Attribute | Purpose |
|---|---|
| `current_folder` | `None` = Home; otherwise folder id |
| `folder_drop_targets` | List of `DropFolderButton` currently on screen |
| `home_drop_target` | The “← Up / Home” button |
| `_hold_event` | `Clock` event for long-press tray open |
| `_hold_target` | `('up', None)` or `('chip', folder_id)` |
| `_highlighted` | Widgets currently painted as hover |
| `_hover_widget` | Current hover target |
| `_ghost` | Active `DragGhost` or `None` |
| `_search_ev` | Debounce clock for live search |
| `search_input` | Top search field |
| `breadcrumb` | Path label |
| `drag_hint` | Status line under breadcrumb |
| `content_grid` | Vertical list of rows |
| `up_btn` / `home_drop_target` | Bottom navigation button |
| `folder_tray` | `FolderBrowseTray` instance |

### Methods (by concern)

**Layout & lifecycle**

- `build_ui()` — constructs top title/date, search bar, util bar (Clip/Attach/Export/Import), breadcrumb, drag hint, scroll + content grid, bottom bar (Up / Tasks / + Folder), folder tray
- `on_pre_enter()` — `refresh_content()` + `_consume_share()`
- `on_enter()` — no-op
- `_consume_share()` — reads `app.pending_share`, calls `capture.capture_text`, opens the new note

**List building & display**

- `refresh_content()` — clears grid; adds folder rows, note rows, open task rows, empty state; updates breadcrumb
- `update_breadcrumb()` — “Home · …” or path from `folder_manager.get_folder_path`
- `_note_label(note)` — title + up to 4 tags + `NoteManager.preview_text`
- `_note_row(note, draggable=True)` — builds note button (draggable or plain) + Rename button

**Search**

- `_on_search_text` — 120 ms debounce (0 ms when empty)
- `search_notes` — FTS via `note_manager.search_notes`; replaces grid with non-draggable note rows

**Drag & drop (the bulk)**

- `begin_note_drag(note_btn)` — hint, paint targets, create `DragGhost`
- `move_note_ghost(pos)` / `end_note_ghost()`
- `on_note_drag(touch)` — hit-test chips / Up button / folder buttons; update hover + hint; start/cancel hold timer
- `_open_hold_target(key, parent_id)` — opens tray on long-press of Up or chip
- `drop_note(note, touch)` — move to chip, folder button, or parent/Home; hide tray
- Helpers: `_touch_hits`, `_paint_targets`, `_clear_highlights`, `_highlight`, `_cancel_hold`

**Navigation & CRUD**

- `open_folder` / `go_up` — change `current_folder`, refresh
- `open_note` — load into `note_editor`, slide left
- `open_task` / `open_task_list` — set context on `task_list`, slide left
- `create_new_note` — creates “Untitled Note”, opens editor
- `create_new_task` — creates “New Task”, refreshes
- `create_new_folder` — prompt, creates under current folder
- `rename_folder` / `rename_note` — `prompt_text` + manager update + refresh

**Capture & backup**

- `clip_inbox` — prompt → `capture.capture_text` → open note
- `clip_file` — file chooser popup → `capture.capture_file` → open note
- `export_archive` — prompt for filename → `backup.export_archive` (into `user_data_dir`)
- `import_archive` — zip chooser → `backup.import_archive` → refresh + status

### External connections

| Dependency | How used |
|---|---|
| `App.get_running_app()` | Managers: `note_manager`, `task_manager`, `folder_manager`, `tag_manager`, `capture`, `backup`; `pending_share`; `user_data_dir` |
| `FolderBrowseTray` | Hold-to-browse; `show` / `hide` / `is_open` / `chip_under` / `chips` |
| `DragGhost` | Floating label during drag |
| `prompt_text` (dialogs) | Rename, new folder, clip, export filename |
| `NoteManager.preview_text` | Note row subtitle |
| `switch_screen` (theme) | Screen transitions |
| Theme constants / widgets | `FlatButton`, `FlatInput`, colors |
| ScreenManager | `get_screen('note_editor')`, `get_screen('task_list')` |

### Behaviors that must be preserved

1. Tap note → open editor; drag note → ghost + drop targets.
2. Drop on folder row moves note into that folder.
3. Drop on ← Up / Home moves to parent (or Home if already at root).
4. Hold (~0.7 s) on ← Up / Home or on a tray chip with children opens/drills the tray.
5. Drop on a tray chip moves into that folder and closes the tray.
6. Release elsewhere cancels (note stays put, tray hides).
7. Live search (120 ms) replaces the list with non-draggable results; clearing search restores the folder view.
8. Clip / Attach create a note in the current folder and open it.
9. Export writes a zip under app data; import refreshes the list.
10. Android share intent is consumed on first enter and opens the resulting note.
11. Only open (incomplete) tasks appear on the home preview.
12. Breadcrumb and drag hint stay in sync with folder and drag state.

## Extraction plan

### Target shape

```
ui/screens/main_screen.py          # coordinator (~320 lines)
ui/widgets/note_row.py             # DraggableNoteButton + DropFolderButton + row builders
ui/widgets/note_drag_controller.py # drag state, hold timer, hit-testing, drop
ui/widgets/capture_dialogs.py      # clip text, attach file, export, import popups (optional)
```

Keep `FolderBrowseTray` and `DragGhost` where they are.

### Step-by-step

**Step 1 — Extract row widgets (low risk)**

1. Create `ui/widgets/note_row.py`.
2. Move `DropFolderButton` and `DraggableNoteButton` there.
3. Move `_note_label` and `_note_row` logic into a small helper or methods on a thin factory that receives the screen (or a protocol with `open_note`, `rename_note`, `begin_note_drag`, etc.).
4. Update imports in `main_screen.py`.
5. Run existing smoke tests; manually verify tap-to-open and drag still work.

**Step 2 — Extract drag controller (medium risk)**

1. Create `ui/widgets/note_drag_controller.py`.
2. Move drag state (`_ghost`, `_hold_event`, `_hold_target`, `_highlighted`, `_hover_widget`) and methods:
   - `begin_note_drag`, `move_note_ghost`, `end_note_ghost`
   - `on_note_drag`, `_open_hold_target`, `drop_note`
   - `_touch_hits`, `_paint_targets`, `_clear_highlights`, `_highlight`, `_cancel_hold`
3. The controller receives the screen (or a narrow host interface) for:
   - `folder_drop_targets`, `home_drop_target`, `folder_tray`, `drag_hint`
   - `current_folder`
   - `refresh_content` (called after a successful drop)
   - Access to managers via `App.get_running_app()` or injected
4. `DraggableNoteButton` continues to call `host.begin_note_drag` etc.; the screen delegates those to the controller.
5. Verify all drag behaviors listed above (including hold-to-browse and cancel).

**Step 3 — Extract capture/backup dialogs (optional, low risk)**

1. Create `ui/widgets/capture_dialogs.py` (or keep them if the screen stays readable).
2. Move `clip_inbox`, `clip_file`, `export_archive`, `import_archive` into functions that take a callback or the screen’s `current_folder` + refresh/open hooks.
3. Screen buttons just call the dialog functions.

**Step 4 — Clean the coordinator**

1. `build_ui` stays on the screen.
2. `refresh_content`, navigation, CRUD, search, and share consumption stay on the screen.
3. Remove now-unused imports and private helpers.
4. Confirm the file is roughly 320 lines and that every original behavior still works.

**Step 5 — Tests**

- Existing manager tests are unaffected.
- Add or extend a smoke test if one already touches the main screen.
- Manual checklist:
  - Create note / task / folder
  - Drag note onto folder and onto Up
  - Hold Up to open tray, drill, drop
  - Search and clear search
  - Clip text and URL
  - Export + import
  - Rename note and folder

## What stays on MainScreen

- `build_ui` and widget references
- `current_folder`
- `refresh_content` / `update_breadcrumb`
- Search debounce and `search_notes`
- Navigation (`open_*`, `go_up`)
- Create / rename folder, note, task
- Share consumption
- Button wiring

## What moves out

- `DropFolderButton`, `DraggableNoteButton`
- Note row label/row construction
- All drag state and drag methods
- (Optional) capture and backup popup construction

## Risks and notes

- Drag hit-testing uses `to_widget` and `collide_point`. Moving code must not change coordinate handling.
- The hold timer captures `open_parent` in a lambda. Keep the same capture semantics.
- `DraggableNoteButton` currently holds a reference to the screen as `host`. After extraction it can hold the controller (or the screen that delegates).
- Search results use non-draggable rows on purpose — preserve that.
- Do not change public behavior or string labels in this pass; this is a pure structural refactor.
- After extraction, update `ARCHITECTURE.md` one-liner if the layout description mentions the screen size/responsibilities.

## Success criteria

- `main_screen.py` is under ~330 lines and no longer contains drag hit-testing or row construction.
- All behaviors in “must be preserved” still work on desktop.
- Existing tests pass.
- No new dependencies; no change to data layer or other screens.

## Next features this unblocks

- Due-date / overdue banner on the home list (touches `refresh_content` only)
- Future list virtualization or incremental updates
- Cleaner place to add “all notes” or saved-search views
