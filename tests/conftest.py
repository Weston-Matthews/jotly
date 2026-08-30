"""Shared fixtures for manager-level tests. No Kivy required."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from models.folder import FolderManager
from models.note import NoteManager
from models.tag import TagManager
from models.task import TaskManager


@pytest.fixture
def db():
    manager = DatabaseManager(':memory:')
    yield manager
    manager.close()


@pytest.fixture
def notes(db):
    return NoteManager(db)


@pytest.fixture
def tasks(db):
    return TaskManager(db)


@pytest.fixture
def folders(db):
    return FolderManager(db)


@pytest.fixture
def tags(db):
    return TagManager(db)
