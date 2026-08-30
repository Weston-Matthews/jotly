"""
Rich Text Editor Widget
Supports basic formatting: bold, italic, underline, bullet lists
Uses BBCode markup for storage (tags visible during editing)
"""

import re

from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from ui.theme import MUTED, FlatButton, FlatInput


class RichTextEditor(BoxLayout):
    """
    A rich text editor widget with formatting toolbar
    Stores content as BBCode markup
    Note: BBCode tags are visible during editing (e.g., [b]bold text[/b])
    """

    text_content = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(6)

        self.toolbar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))

        self.bold_btn = FlatButton(text='[b]B[/b]', kind='ghost', markup=True, size_hint_x=None, width=dp(44))
        self.bold_btn.bind(on_press=self.insert_bold)
        self.toolbar.add_widget(self.bold_btn)

        self.italic_btn = FlatButton(text='[i]I[/i]', kind='ghost', markup=True, size_hint_x=None, width=dp(44))
        self.italic_btn.bind(on_press=self.insert_italic)
        self.toolbar.add_widget(self.italic_btn)

        self.underline_btn = FlatButton(text='[u]U[/u]', kind='ghost', markup=True, size_hint_x=None, width=dp(44))
        self.underline_btn.bind(on_press=self.insert_underline)
        self.toolbar.add_widget(self.underline_btn)

        self.bullet_btn = FlatButton(text='• List', kind='ghost', size_hint_x=None, width=dp(72))
        self.bullet_btn.bind(on_press=self.insert_bullet)
        self.toolbar.add_widget(self.bullet_btn)

        self.number_btn = FlatButton(text='1.', kind='ghost', size_hint_x=None, width=dp(44))
        self.number_btn.bind(on_press=self.insert_numbered)
        self.toolbar.add_widget(self.number_btn)

        self.check_btn = FlatButton(text='☐', kind='ghost', size_hint_x=None, width=dp(44))
        self.check_btn.bind(on_press=self.insert_check)
        self.toolbar.add_widget(self.check_btn)

        self.clear_btn = FlatButton(text='Clear', kind='ghost', size_hint_x=None, width=dp(64))
        self.clear_btn.bind(on_press=self.clear_formatting)
        self.toolbar.add_widget(self.clear_btn)

        self.toolbar.add_widget(Label(color=MUTED))
        self.add_widget(self.toolbar)

        self.text_input = FlatInput(multiline=True, font_size='16sp')
        self.text_input.bind(text=self.on_text_change)
        self.add_widget(self.text_input)

    def on_text_change(self, instance, value):
        self.text_content = value

    def insert_bold(self, instance):
        self._wrap_selection('[b]', '[/b]')

    def insert_italic(self, instance):
        self._wrap_selection('[i]', '[/i]')

    def insert_underline(self, instance):
        self._wrap_selection('[u]', '[/u]')

    def insert_bullet(self, instance):
        self._prefix_current_line('• ')

    def insert_numbered(self, instance):
        text = self.text_input.text
        cursor = self.text_input.cursor_index()
        line_start = text.rfind('\n', 0, cursor) + 1
        before = text[:line_start]
        count = 1
        for raw in before.splitlines()[::-1]:
            stripped = raw.strip()
            if re.match(r'^\d+\.\s', stripped):
                count = int(stripped.split('.', 1)[0]) + 1
                break
            if stripped.startswith('• ') or stripped.startswith('☐ ') or stripped.startswith('☑ '):
                break
            if stripped:
                break
        self._prefix_current_line(f'{count}. ')

    def insert_check(self, instance):
        text = self.text_input.text
        cursor = self.text_input.cursor_index()
        line_start = text.rfind('\n', 0, cursor) + 1
        line_end = text.find('\n', cursor)
        if line_end < 0:
            line_end = len(text)
        line = text[line_start:line_end]
        if line.startswith('☐ '):
            replacement = '☑ ' + line[2:]
            self.text_input.text = text[:line_start] + replacement + text[line_end:]
        elif line.startswith('☑ '):
            replacement = '☐ ' + line[2:]
            self.text_input.text = text[:line_start] + replacement + text[line_end:]
        else:
            self._prefix_current_line('☐ ')

    def _prefix_current_line(self, prefix):
        text = self.text_input.text
        cursor = self.text_input.cursor_index()
        line_start = text.rfind('\n', 0, cursor) + 1
        line_end = text.find('\n', cursor)
        if line_end < 0:
            line_end = len(text)
        line = text[line_start:line_end]
        if line.startswith(prefix):
            return
        for old in ('• ', '☐ ', '☑ '):
            if line.startswith(old):
                line = line[len(old):]
                break
        numbered = re.match(r'^\d+\.\s+', line)
        if numbered:
            line = line[numbered.end():]
        updated = prefix + line
        self.text_input.text = text[:line_start] + updated + text[line_end:]
        self.text_input.cursor = self.text_input.get_cursor_from_index(line_start + len(prefix))

    def _wrap_selection(self, start_tag, end_tag):
        if self.text_input.selection_text:
            selected = self.text_input.selection_text
            formatted = f'{start_tag}{selected}{end_tag}'
            start = self.text_input.selection_from
            end = self.text_input.selection_to
            if start > end:
                start, end = end, start
            text = self.text_input.text
            self.text_input.text = text[:start] + formatted + text[end:]
            new_pos = start + len(formatted)
            self.text_input.cursor = self.text_input.get_cursor_from_index(new_pos)
        else:
            cursor_pos = self.text_input.cursor_index()
            text = self.text_input.text
            insert_text = f'{start_tag}{end_tag}'
            self.text_input.text = text[:cursor_pos] + insert_text + text[cursor_pos:]
            new_pos = cursor_pos + len(start_tag)
            self.text_input.cursor = self.text_input.get_cursor_from_index(new_pos)

    def clear_formatting(self, instance):
        if self.text_input.selection_text:
            selected = self.text_input.selection_text
            cleaned = re.sub(r'\[/?[biu]\]', '', selected)
            start = self.text_input.selection_from
            end = self.text_input.selection_to
            if start > end:
                start, end = end, start
            text = self.text_input.text
            self.text_input.text = text[:start] + cleaned + text[end:]
        else:
            self.text_input.text = re.sub(r'\[/?[biu]\]', '', self.text_input.text)

    def set_text(self, text):
        self.text_input.text = text if text else ''

    def get_text(self):
        return self.text_input.text

    def clear(self):
        self.text_input.text = ''
