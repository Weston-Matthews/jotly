"""Inbox-style capture: drop text, a URL, or a file into a new note."""

import os
import re
from urllib.parse import urlparse


_URL_RE = re.compile(r'^https?://\S+$', re.IGNORECASE)


class CaptureService:
    def __init__(self, note_manager, tag_manager, attachment_manager):
        self.notes = note_manager
        self.tags = tag_manager
        self.attachments = attachment_manager

    @staticmethod
    def looks_like_url(text):
        return bool(text and _URL_RE.match(text.strip()))

    @staticmethod
    def title_from_url(url):
        parsed = urlparse(url.strip())
        host = parsed.netloc or 'Link'
        path = (parsed.path or '').strip('/')
        if path:
            leaf = path.split('/')[-1].replace('-', ' ').replace('_', ' ')
            return f'{leaf} · {host}'[:80]
        return host

    def capture_text(self, text, folder_id=None, title=None, tag_names=None):
        body = (text or '').strip()
        if not body:
            return None
        if self.looks_like_url(body):
            return self.capture_url(body, folder_id=folder_id, tag_names=tag_names)
        note_title = (title or body.splitlines()[0][:80]).strip() or 'Quick note'
        note_id = self.notes.create_note(note_title, body, folder_id)
        if tag_names:
            self.tags.set_note_tags(note_id, tag_names)
        return note_id

    def capture_url(self, url, folder_id=None, title=None, tag_names=None):
        clean = (url or '').strip()
        if not clean:
            return None
        note_title = title or self.title_from_url(clean)
        body = clean if clean.startswith('http') else f'https://{clean}'
        extra_tags = list(tag_names or [])
        extra_tags.append('clip')
        note_id = self.notes.create_note(note_title, body, folder_id)
        self.tags.set_note_tags(note_id, extra_tags)
        return note_id

    def capture_file(self, src_path, folder_id=None, title=None, extra_text='', tag_names=None):
        if not src_path or not os.path.isfile(src_path):
            return None
        filename = os.path.basename(src_path)
        note_title = title or filename
        body = extra_text.strip() if extra_text else f'Attached {filename}'
        note_id = self.notes.create_note(note_title, body, folder_id)
        self.attachments.attach_file(note_id, src_path, filename)
        names = list(tag_names or [])
        names.append('inbox')
        self.tags.set_note_tags(note_id, names)
        return note_id
