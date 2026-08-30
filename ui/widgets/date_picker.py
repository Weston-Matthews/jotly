"""Month-view calendar popup for task due dates."""

import calendar
from datetime import date, datetime

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ui.theme import ACCENT, MUTED, PRIMARY, SUCCESS, SURFACE, TEXT, FlatButton


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


class DatePickerPopup(Popup):
    def __init__(self, initial=None, on_pick=None, **kwargs):
        self.on_pick = on_pick
        self.selected = _parse_iso(initial) or date.today()
        self.view_year = self.selected.year
        self.view_month = self.selected.month

        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))
        nav = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.prev_btn = FlatButton(text='‹', kind='ghost', size_hint_x=None, width=dp(44))
        self.next_btn = FlatButton(text='›', kind='ghost', size_hint_x=None, width=dp(44))
        self.month_label = Label(halign='center', color=TEXT, bold=True)
        self.prev_btn.bind(on_press=lambda *_: self._shift(-1))
        self.next_btn.bind(on_press=lambda *_: self._shift(1))
        nav.add_widget(self.prev_btn)
        nav.add_widget(self.month_label)
        nav.add_widget(self.next_btn)
        root.add_widget(nav)

        self.grid = GridLayout(cols=7, spacing=dp(3))
        root.add_widget(self.grid)

        actions = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        clear_btn = FlatButton(text='Clear', kind='ghost')
        today_btn = FlatButton(text='Today', kind='primary')
        cancel_btn = FlatButton(text='Cancel', kind='ghost')
        clear_btn.bind(on_press=self._clear)
        today_btn.bind(on_press=self._today)
        cancel_btn.bind(on_press=lambda *_: self.dismiss())
        actions.add_widget(clear_btn)
        actions.add_widget(today_btn)
        actions.add_widget(cancel_btn)
        root.add_widget(actions)

        kwargs.setdefault('title', 'Due date')
        kwargs.setdefault('size_hint', (0.92, 0.72))
        kwargs.setdefault('separator_color', (*ACCENT[:3], 0.6))
        kwargs.setdefault('title_color', TEXT)
        kwargs.setdefault('background', '')
        kwargs.setdefault('background_color', SURFACE)
        super().__init__(content=root, **kwargs)
        self._render()

    def _shift(self, delta):
        month = self.view_month + delta
        year = self.view_year
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        self.view_month = month
        self.view_year = year
        self._render()

    def _render(self):
        self.month_label.text = date(self.view_year, self.view_month, 1).strftime('%B %Y')
        self.grid.clear_widgets()
        for name in ('Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'):
            self.grid.add_widget(Label(text=name, size_hint_y=None, height=dp(24), color=MUTED))

        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(
            self.view_year, self.view_month
        )
        today = date.today()
        for week in weeks:
            for day in week:
                if day == 0:
                    self.grid.add_widget(Label(text=''))
                    continue
                current = date(self.view_year, self.view_month, day)
                btn = FlatButton(text=str(day), kind='neutral')
                if current == self.selected:
                    btn.set_kind('primary')
                    btn.background_color = PRIMARY
                elif current == today:
                    btn.set_kind('success')
                    btn.background_color = SUCCESS
                btn.bind(on_press=lambda _x, d=current: self._choose(d))
                self.grid.add_widget(btn)

    def _choose(self, picked):
        self.selected = picked
        if self.on_pick:
            self.on_pick(picked.isoformat())
        self.dismiss()

    def _clear(self, *_args):
        if self.on_pick:
            self.on_pick(None)
        self.dismiss()

    def _today(self, *_args):
        self._choose(date.today())


def pick_date(initial, on_pick):
    popup = DatePickerPopup(initial=initial, on_pick=on_pick)
    popup.open()
    return popup
