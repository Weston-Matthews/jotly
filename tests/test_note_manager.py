def test_create_and_get_note(notes):
    note_id = notes.create_note('Groceries', 'milk and eggs')
    note = notes.get_note(note_id)
    assert note is not None
    assert note.title == 'Groceries'
    assert note.content == 'milk and eggs'
    assert note.folder_id is None
    assert note.created_at
    assert note.updated_at


def test_get_missing_note_returns_none(notes):
    assert notes.get_note(999) is None


def test_update_note_changes_fields(notes):
    note_id = notes.create_note('Draft', 'old body')
    notes.update_note(note_id, title='Final', content='new body')
    note = notes.get_note(note_id)
    assert note.title == 'Final'
    assert note.content == 'new body'


def test_update_note_noop_when_no_fields(notes):
    note_id = notes.create_note('Same', 'body')
    before = notes.get_note(note_id)
    notes.update_note(note_id)
    after = notes.get_note(note_id)
    assert after.title == before.title
    assert after.updated_at == before.updated_at


def test_delete_note(notes):
    note_id = notes.create_note('Trash me', 'gone')
    notes.delete_note(note_id)
    assert notes.get_note(note_id) is None


def test_get_all_notes_orders_by_updated_at(notes):
    first = notes.create_note('Older', 'a')
    second = notes.create_note('Newer', 'b')
    notes.update_note(first, content='touched')
    titles = [n.title for n in notes.get_all_notes()]
    assert titles[0] == 'Older'
    assert set(titles) == {'Older', 'Newer'}
    assert second in {n.id for n in notes.get_all_notes()}


def test_get_all_notes_filters_by_folder(notes, folders):
    work = folders.create_folder('Work')
    notes.create_note('In work', 'x', folder_id=work)
    notes.create_note('Unfiled', 'y')
    in_work = notes.get_all_notes(folder_id=work)
    assert [n.title for n in in_work] == ['In work']
    assert [n.title for n in notes.get_all_notes()] == ['Unfiled']


def test_search_matches_title_and_content(notes):
    notes.create_note('Meeting notes', 'agenda for Monday')
    notes.create_note('Unrelated', 'shopping list')
    by_title = notes.search_notes('Meeting')
    by_body = notes.search_notes('Monday')
    assert [n.title for n in by_title] == ['Meeting notes']
    assert [n.title for n in by_body] == ['Meeting notes']


def test_search_updates_when_note_changes(notes):
    note_id = notes.create_note('Alpha', 'penguins in the snow')
    assert notes.search_notes('penguins')
    notes.update_note(note_id, title='Beta', content='only walruses now')
    assert notes.search_notes('penguins') == []
    assert [n.title for n in notes.search_notes('walruses')] == ['Beta']
    assert notes.search_notes('Alpha') == []


def test_search_drops_deleted_notes(notes):
    note_id = notes.create_note('Temp', 'zebra stripes')
    assert notes.search_notes('zebra')
    notes.delete_note(note_id)
    assert notes.search_notes('zebra') == []


def test_search_empty_query_returns_no_rows(notes):
    notes.create_note('Anything', 'text')
    assert notes.search_notes('') == []
    assert notes.search_notes('   ') == []
    assert notes.search_notes(None) == []


def test_search_hyphenated_query_is_not_fts_syntax(notes):
    notes.create_note('Safe', 'ordinary body')
    assert notes.search_notes('zzzz-no-match') == []
    notes.create_note('Follow-up', 'call the client')
    assert [n.title for n in notes.search_notes('Follow-up')] == ['Follow-up']
