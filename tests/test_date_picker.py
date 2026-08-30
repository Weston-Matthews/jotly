from datetime import date

from ui.widgets.date_picker import _parse_iso


def test_parse_iso_accepts_date_and_rejects_junk():
    assert _parse_iso('2026-09-01') == date(2026, 9, 1)
    assert _parse_iso('2026-09-01T12:00:00') == date(2026, 9, 1)
    assert _parse_iso('') is None
    assert _parse_iso(None) is None
    assert _parse_iso('not-a-date') is None
