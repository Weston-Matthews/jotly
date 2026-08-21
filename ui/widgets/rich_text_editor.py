"""
Rich Text Editor Widget
Supports basic formatting: bold, italic, underline, bullet lists
Uses BBCode markup for storage (tags visible during editing)
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import StringProperty


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
        
        # Create toolbar
        self.toolbar = BoxLayout(size_hint_y=None, height=50, spacing=5, padding=5)
        
        # Bold button
        self.bold_btn = Button(text='[b]B[/b]', markup=True, size_hint_x=None, width=50)
        self.bold_btn.bind(on_press=self.insert_bold)
        self.toolbar.add_widget(self.bold_btn)
        
        # Italic button
        self.italic_btn = Button(text='[i]I[/i]', markup=True, size_hint_x=None, width=50)
        self.italic_btn.bind(on_press=self.insert_italic)
        self.toolbar.add_widget(self.italic_btn)
        
        # Underline button
        self.underline_btn = Button(text='[u]U[/u]', markup=True, size_hint_x=None, width=50)
        self.underline_btn.bind(on_press=self.insert_underline)
        self.toolbar.add_widget(self.underline_btn)
        
        # Bullet list button
        self.bullet_btn = Button(text='• List', size_hint_x=None, width=80)
        self.bullet_btn.bind(on_press=self.insert_bullet)
        self.toolbar.add_widget(self.bullet_btn)
        
        # Clear formatting button
        self.clear_btn = Button(text='Clear Format', size_hint_x=None, width=120)
        self.clear_btn.bind(on_press=self.clear_formatting)
        self.toolbar.add_widget(self.clear_btn)
        
        # Spacer
        from kivy.uix.label import Label
        self.toolbar.add_widget(Label())
        
        self.add_widget(self.toolbar)
        
        # Text input area
        self.text_input = TextInput(
            multiline=True,
            font_size=16,
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1)
        )
        self.text_input.bind(text=self.on_text_change)
        
        self.add_widget(self.text_input)
    
    def on_text_change(self, instance, value):
        """Update text_content property when text changes"""
        self.text_content = value
    
    def insert_bold(self, instance):
        """Wrap selected text in bold tags or insert tags at cursor"""
        self._wrap_selection('[b]', '[/b]')
    
    def insert_italic(self, instance):
        """Wrap selected text in italic tags or insert tags at cursor"""
        self._wrap_selection('[i]', '[/i]')
    
    def insert_underline(self, instance):
        """Wrap selected text in underline tags or insert tags at cursor"""
        self._wrap_selection('[u]', '[/u]')
    
    def insert_bullet(self, instance):
        """Insert a bullet point at cursor position"""
        cursor_pos = self.text_input.cursor_index()
        text = self.text_input.text
        
        # Insert bullet at cursor
        bullet = '• '
        self.text_input.text = text[:cursor_pos] + bullet + text[cursor_pos:]
        
        # Move cursor after bullet
        self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_pos + len(bullet))
    
    def _wrap_selection(self, start_tag, end_tag):
        """Wrap selected text with formatting tags"""
        # Get selection
        if self.text_input.selection_text:
            # There is selected text
            selected = self.text_input.selection_text
            formatted = f'{start_tag}{selected}{end_tag}'
            
            # Replace selection with formatted text
            start = self.text_input.selection_from
            end = self.text_input.selection_to
            
            if start > end:
                start, end = end, start
            
            text = self.text_input.text
            self.text_input.text = text[:start] + formatted + text[end:]
            
            # Set cursor after the inserted text
            new_pos = start + len(formatted)
            self.text_input.cursor = self.text_input.get_cursor_from_index(new_pos)
        else:
            # No selection, just insert the tags at cursor
            cursor_pos = self.text_input.cursor_index()
            text = self.text_input.text
            insert_text = f'{start_tag}{end_tag}'
            self.text_input.text = text[:cursor_pos] + insert_text + text[cursor_pos:]
            
            # Move cursor between the tags
            new_pos = cursor_pos + len(start_tag)
            self.text_input.cursor = self.text_input.get_cursor_from_index(new_pos)
    
    def clear_formatting(self, instance):
        """Remove all BBCode formatting from selected text or entire document"""
        import re
        
        if self.text_input.selection_text:
            # Clear formatting from selection only
            selected = self.text_input.selection_text
            cleaned = re.sub(r'\[/?[biu]\]', '', selected)
            
            start = self.text_input.selection_from
            end = self.text_input.selection_to
            
            if start > end:
                start, end = end, start
            
            text = self.text_input.text
            self.text_input.text = text[:start] + cleaned + text[end:]
        else:
            # Clear all formatting from entire text
            text = self.text_input.text
            cleaned = re.sub(r'\[/?[biu]\]', '', text)
            self.text_input.text = cleaned
    
    def set_text(self, text):
        """Set the text content (with markup)"""
        self.text_input.text = text if text else ''
    
    def get_text(self):
        """Get the text content (with markup)"""
        return self.text_input.text
    
    def clear(self):
        """Clear the editor"""
        self.text_input.text = ''