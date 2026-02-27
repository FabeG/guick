from __future__ import annotations

import contextlib
import datetime
import enum
import importlib.util
import io
import json
import math
import os
import re
import sys
import time
from wx import aui
import webbrowser
from collections import defaultdict
from pathlib import Path
from threading import Thread
from typing import (
    List,
    Optional,
    Union,
)

import click
import tomlkit
import wx
import wx.adv
import wx.html
import wx.lib.scrolledpanel as scrolled
from click.core import (
    Argument,
    Context,
    Option,
)
from tomlkit.toml_document import TOMLDocument

# Check if typer is installed
_typer_spec = importlib.util.find_spec("typer")

if _typer_spec is not None:
    try:
        from typer.core import TyperCommand, TyperGroup
        TYPER_TYPES = (TyperCommand, TyperGroup)
    except ImportError:
        TYPER_TYPES = ()
else:
    TYPER_TYPES = ()

try:
    # Click 8.3+
    from click._utils import UNSET
except ImportError:
    # Click <8.3
    UNSET = None

# Regex pattern to match ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[((?:\d+;)*\d+)m")


# Windows Terminal Colors
# Mapping ANSI color codes to HTML colors
# From https://devblogs.microsoft.com/commandline/updating-the-windows-console-colors/
class TermColors(enum.Enum):
    BLACK = (12, 12, 12)
    RED = (197, 15, 31)
    GREEN = (19, 161, 14)
    YELLOW = (193, 156, 0)
    BLUE = (0, 55, 218)
    MAGENTA = (136, 23, 152)
    CYAN = (58, 150, 221)
    WHITE = (204, 204, 204)
    BRIGHT_BLACK = (118, 118, 118)
    BRIGHT_RED = (231, 72, 86)
    BRIGHT_GREEN = (22, 198, 12)
    BRIGHT_YELLOW = (249, 241, 165)
    BRIGHT_BLUE = (59, 120, 255)
    BRIGHT_MAGENTA = (180, 0, 158)
    BRIGHT_CYAN = (97, 214, 214)
    BRIGHT_WHITE = (242, 242, 242)


class AnsiEscapeCodes(enum.IntEnum):
    ResetFormat = 0
    BoldText = 1
    ItalicText = 3
    UnderLinedText = 4
    StrikeThrough = 9
    TextColorStart = 30
    TextColorEnd = 37
    Text256Color = 38
    TextBrightColorStart = 90
    TextBrightColorEnd = 97
    BackgroundColorStart = 40
    BackgroundColorEnd = 47
    Background256Color = 48
    BackgroundBrightColorStart = 100
    BackgroundBrightColorEnd = 107


ANSI_COLORS = {
    0: TermColors["BLACK"],
    1: TermColors["RED"],
    2: TermColors["GREEN"],
    3: TermColors["YELLOW"],
    4: TermColors["BLUE"],
    5: TermColors["MAGENTA"],
    6: TermColors["CYAN"],
    7: TermColors["WHITE"],
    8: TermColors["BRIGHT_BLACK"],
    9: TermColors["BRIGHT_RED"],
    10: TermColors["BRIGHT_GREEN"],
    11: TermColors["BRIGHT_YELLOW"],
    12: TermColors["BRIGHT_BLUE"],
    13: TermColors["BRIGHT_MAGENTA"],
    14: TermColors["BRIGHT_CYAN"],
    15: TermColors["BRIGHT_WHITE"],
}





class ANSITextCtrl(wx.TextCtrl):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(
            parent,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_READONLY,
            name="LogPanel",
        )
        self.gauge_value = 0
        self.gauge_is_visible = False
        # Default foreground and background colors
        self.default_fg = TermColors["WHITE"]
        self.default_bg = TermColors["BLACK"]

    def append_ansi_text(self, message):
        # Find all ANSI color code segments
        segments = []
        last_end = 0
        current_fg = self.default_fg
        current_bg = self.default_bg
        underline = False
        strikethrough = False
        italic = False
        bold_fg = False
        bold_bg = False
        # Split the message by ANSI codes
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='replace')
        for match in ANSI_ESCAPE_PATTERN.finditer(message):
            # Add text before the ANSI code
            if match.start() > last_end:
                segments.append(
                    (
                        message[last_end : match.start()],
                        current_fg,
                        current_bg,
                        underline,
                        strikethrough,
                        italic,
                        bold_fg,
                        bold_bg,
                    )
                )

            # Extract and interpret ANSI code parameters
            params_str = match.group(1)
            params = iter([int(p) for p in params_str.split(";") if p])
            for param in params:
                # Process ANSI parameters
                if param == AnsiEscapeCodes.ResetFormat:
                    current_fg = self.default_fg
                    current_bg = self.default_bg
                    underline = False
                    italic = False
                    bold_fg = False
                    bold_bg = False
                    strikethrough = False
                elif param == AnsiEscapeCodes.UnderLinedText:
                    underline = True
                elif param == AnsiEscapeCodes.StrikeThrough:
                    strikethrough = True
                elif param == AnsiEscapeCodes.ItalicText:
                    italic = True
                elif param == AnsiEscapeCodes.BoldText:
                    bold_fg = True
                elif (
                    AnsiEscapeCodes.BackgroundColorStart
                    <= param
                    <= AnsiEscapeCodes.BackgroundColorEnd
                ):
                    current_bg = ANSI_COLORS[
                        param - AnsiEscapeCodes.BackgroundColorStart
                    ]
                elif (
                    AnsiEscapeCodes.TextColorStart
                    <= param
                    <= AnsiEscapeCodes.TextColorEnd
                ):
                    current_fg = ANSI_COLORS[param - AnsiEscapeCodes.TextColorStart]
                elif (
                    AnsiEscapeCodes.BackgroundBrightColorStart
                    <= param
                    <= AnsiEscapeCodes.BackgroundBrightColorEnd
                ):
                    current_bg = ANSI_COLORS[
                        param - AnsiEscapeCodes.BackgroundBrightColorStart
                    ]
                    bold_bg = True
                elif (
                    AnsiEscapeCodes.TextBrightColorStart
                    <= param
                    <= AnsiEscapeCodes.TextBrightColorEnd
                ):
                    current_fg = ANSI_COLORS[
                        param - AnsiEscapeCodes.TextBrightColorStart
                    ]
                    bold_fg = True
                # 256 colors or RGB
                elif param in {AnsiEscapeCodes.Text256Color, AnsiEscapeCodes.Background256Color}:
                    second_param = next(params, None)
                    # 256 colors
                    if second_param == 5:
                        color_code = next(params, None)
                        # Standard colors
                        if color_code < 16:
                            color = ANSI_COLORS[color_code]
                        # 6 x 6 x 6 color cube
                        elif 16 <= color_code <= 231:
                            color_code -= 16
                            r = color_code // 36
                            g = (color_code % 36) // 6
                            b = color_code % 6

                            def level(n):
                                return 0 if n == 0 else 55 + n * 40

                            color = (level(r), level(g), level(b))

                        else:
                            # Grayscale ramp
                            gray = 8 + (color_code - 232) * 10
                            color = (gray, gray, gray)
                    # rgb values
                    elif second_param == 2:
                        red = next(params, None)
                        green = next(params, None)
                        blue = next(params, None)
                        color = (red, green, blue)
                    if param == AnsiEscapeCodes.Text256Color:
                        current_fg = color
                    else:
                        current_bg = color


            last_end = match.end()

        # Add remaining text
        if last_end < len(message):
            segments.append(
                (
                    message[last_end:],
                    current_fg,
                    current_bg,
                    underline,
                    strikethrough,
                    italic,
                    bold_fg,
                    bold_bg,
                )
            )

        # Apply text and styles
        for text, fg, bg, ul, st, it, bold_fg, bold_bg in segments:
            if text:
                # Create a font that matches the default one but with underline if needed
                font = self.GetFont()
                if ul:
                    font.SetUnderlined(True)
                else:
                    font.SetUnderlined(False)
                if it:
                    font.MakeItalic()
                if st:
                    font.SetStrikethrough(True)
                # Create text attribute with the font
                if bold_fg:
                    font = font.Bold()
                    if isinstance(fg, TermColors):
                        color_fg = TermColors["BRIGHT_" + fg.name].value if "BRIGHT" not in fg.name else TermColors[fg.name].value
                    else:
                        color_fg = fg
                else:
                    if isinstance(fg, TermColors):
                        color_fg = TermColors[fg.name].value
                    else:
                        color_fg = fg
                if bold_bg:
                    if isinstance(fg, TermColors):
                        color_bg = TermColors["BRIGHT_" + bg.name].value if "BRIGHT" not in bg.name else TermColors[bg.name].value
                    else:
                        color_bg = bg
                else:
                    if isinstance(bg, TermColors):
                        color_bg = TermColors[bg.name].value
                    else:
                        color_bg = bg

                style = wx.TextAttr(
                    wx.Colour(*color_fg), wx.Colour(*color_bg), font
                )
                self.SetDefaultStyle(style)
                # Regex to extract the progress bar value from the tqdm output
                regex_tqdm = re.match(r"\r([\d\s]+)%\|.*\|(.*)", text)
                regex_click_progressbar = re.match(r"\r(.*) \[(#*)(-*)\](.*)", text)
                if regex_tqdm:
                    if not self.gauge_is_visible:
                        self.gauge_sizer.ShowItems(True)
                        self.gauge_is_visible = True
                        self.Layout()
                    self.gauge_value = int(regex_tqdm.group(1))
                    self.gauge.SetValue(self.gauge_value)
                    self.gauge_text.SetValue(regex_tqdm.group(2))
                elif regex_click_progressbar:
                    if not self.gauge_is_visible:
                        self.gauge_sizer.ShowItems(True)
                        self.gauge_is_visible = True
                        self.Layout()
                    completed = len(regex_click_progressbar.group(2))
                    total = completed + len(regex_click_progressbar.group(3))
                    if total > 0:
                        self.gauge_value = int((completed / total) * 100)
                    else:
                        self.gauge_value = 0
                    self.gauge.SetValue(self.gauge_value)
                    self.gauge_text.SetValue(
                        regex_click_progressbar.group(1)
                        + " " + regex_click_progressbar.group(4)
                    )
                else:
                    self.AppendText(text)
        # Reset style at the end
        default_font = self.GetFont()
        default_font.SetUnderlined(False)
        self.SetDefaultStyle(
            wx.TextAttr(
                wx.Colour(*self.default_fg.value),
                wx.Colour(*self.default_bg.value),
                default_font,
            )
        )


def blend(c1, c2, factor):
    return wx.Colour(
        int(c1.Red() + (c2.Red() - c1.Red()) * factor),
        int(c1.Green() + (c2.Green() - c1.Green()) * factor),
        int(c1.Blue() + (c2.Blue() - c1.Blue()) * factor),
    )


class SearchPanel(wx.Panel):
    def __init__(self, parent, target_text_ctrl):
        """
        A reusable panel that searches inside the provided target_text_ctrl.
        """
        super().__init__(parent)
        self.target_ctrl = target_text_ctrl
        self.current_search_pos = 0
        self.last_match_start = -1
        self.last_match_end = -1
        self.saved_bg_color = wx.NullColour
        self.saved_fg_color = wx.NullColour

        # Search Control
        self.search_ctrl = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search_ctrl.ShowCancelButton(True)
        self.search_ctrl.SetDescriptiveText("Type and press Enter...")

        # Next Button
        self.btn_next = wx.Button(self, label="Next", size=(60, -1))

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.search_ctrl, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.sizer.Add(self.btn_next, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.SetSizer(self.sizer)

        # Define some bindings (Close / Enter or Next)
        self.search_ctrl.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.on_close)
        self.search_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_find_next)
        self.search_ctrl.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.on_find_next)
        self.btn_next.Bind(wx.EVT_BUTTON, self.on_find_next)

        # Start Hidden
        self.Hide()

    def show_search(self):
        """Public method to trigger the search bar to appear."""
        if not self.IsShown():
            self.Show()
            # Force parent to re-layout so this panel doesn't overlap/float weirdly
            self.GetParent().Layout()

        self.search_ctrl.SetFocus()
        self.search_ctrl.SelectAll()

    def on_close(self, event=None):
        """Hide the search bar and return focus to text."""
        self.Hide()
        self.GetParent().Layout()
        self.target_ctrl.SetFocus()

    def clear_highlight(self):
        """Clear previous highlight, keeping the original style."""
        if self.last_match_start != -1:
            # Restore background previous style
            restore_bg = self.saved_bg_color
            if not restore_bg.IsOk():
                restore_bg = self.target_ctrl.GetBackgroundColour()
            # Restore foreground previous style
            restore_fg = self.saved_fg_color
            if not restore_fg.IsOk():
                restore_fg = self.target_ctrl.GetForegroundColour()
            # Restore the previous style for the previous match
            default_style = wx.TextAttr(restore_fg, restore_bg)
            self.target_ctrl.SetStyle(self.last_match_start, self.last_match_end, default_style)
            self.target_ctrl.Refresh()
            self.last_match_start = -1
            self.last_match_end = -1

    def python_to_wx_index(self, full_text, python_index):
        """
        Converts a Python string index (0-based code points) to a
        wxPython/Windows control index (UTF-16 code units).
        """
        # Take the text UP TO the point we are interested in
        substring = full_text[:python_index]

        # Encode as UTF-16LE (Windows native).
        # Divide by 2 because UTF-16 is 2 bytes per character.
        return len(substring.encode('utf-16le')) // 2

    def on_find_next(self, event):
        """Search logic."""
        query = self.search_ctrl.GetValue()
        if not query:
            return

        self.clear_highlight()

        last_pos = self.target_ctrl.GetLastPosition()
        content = self.target_ctrl.GetRange(0, last_pos)

        # Case-insensitive search
        idx = content.lower().find(query.lower(), self.current_search_pos)

        # Wrap around
        if idx == -1:
            idx = content.lower().find(query.lower(), 0)
            if idx == -1:
                return

        # Calculate Python Start/End
        py_start = idx
        py_end = idx + len(query)

        # Convert to wx/Windows Indices
        # We calculate the UTF-16 position for the start and the end.
        wx_start = self.python_to_wx_index(content, py_start)

        # Note: We calculate end based on the substring length in UTF-16
        # This handles cases where the SEARCH QUERY ITSELF contains an emoji.
        match_text = content[py_start:py_end]
        match_len_utf16 = len(match_text.encode('utf-16le')) // 2
        wx_end = wx_start + match_len_utf16
        existing_attr = wx.TextAttr()
        self.target_ctrl.GetStyle(wx_start, existing_attr)

        # Save the background and forexground colors
        # If the text has no specific bg set, this might be Null, which we handle in clear_highlight.
        self.saved_bg_color = existing_attr.GetBackgroundColour()
        self.saved_fg_color = existing_attr.GetTextColour()
        if not self.saved_bg_color.IsOk():
            self.saved_bg_color = self.target_ctrl.GetBackgroundColour()
        if not self.saved_fg_color.IsOk():
            self.saved_fg_color = self.target_ctrl.GetForegroundColour()

        # Highlight found text
        highlight_style = wx.TextAttr(wx.BLACK, wx.Colour(255, 255, 0))
        self.target_ctrl.SetStyle(wx_start, wx_end, highlight_style)
        self.target_ctrl.ShowPosition(wx_start)

        # Store State
        self.last_match_start = wx_start
        self.last_match_end = wx_end

        # Keep searching from the python index
        self.current_search_pos = py_end

        # Keep focus on search bar
        self.search_ctrl.SetFocus()


class LogPanel(wx.Panel):
    """A panel containing a shared log in a StaticBox."""

    def __init__(self, parent: Guick):
        super().__init__(parent)
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

        box_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create the progessbar in case of tqdm
        self.gauge = wx.Gauge(self, -1, 100, size=(-1, 5))
        font = get_best_monospace_font()
        self.gauge_text = wx.TextCtrl(
            self, -1, "", size=(400, -1), style=wx.TE_READONLY | wx.NO_BORDER
        )
        self.gauge_text.SetFont(
            wx.Font(
                8,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=font,
            )
        )
        self.gauge_sizer = wx.BoxSizer(wx.VERTICAL)
        self.gauge_sizer.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 2)
        self.gauge_sizer.Add(self.gauge_text, 1, wx.EXPAND | wx.ALL, 2)
        # Create the log
        self.log_ctrl = ANSITextCtrl(self)
        self.log_ctrl.SetFont(
            wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=font,
            )
        )
        self.log_ctrl.SetBackgroundColour(wx.Colour(*TermColors.BLACK.value))
        self.search_panel = SearchPanel(self, target_text_ctrl=self.log_ctrl)

        box_sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 2)
        box_sizer.Add(self.gauge_sizer, 0, wx.EXPAND | wx.ALL, 2)
        box_sizer.Add(self.search_panel, 0, wx.EXPAND | wx.ALL, 0)
        self.gauge_sizer.Show(self.gauge_text, False)
        self.gauge_sizer.Show(self.gauge, False)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(box_sizer, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizerAndFit(main_sizer)
        # box_sizer.SetSizeHints(self)
        self.Layout()


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, obj: wx.TextCtrl):
        wx.FileDropTarget.__init__(self)
        self.obj = obj

    def OnDropFiles(self, x, y, filenames):
        self.obj.SetValue("")
        self.obj.WriteText(filenames[0])
        return True


class AboutDialog(wx.Dialog):
    def __init__(self, parent, title, head, text_content, font_size=8, name="AboutDialog"):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, name=name)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Setup the TextCtrl to act like a Label
        # TE_READONLY: Prevents editing
        # TE_MULTILINE: Allows multiple lines
        # TE_AUTO_URL: The magic flag that detects and highlights URLs
        # TE_RICH: Required on Windows for URL detection to work reliably
        # BORDER_NONE: Removes the input box border so it looks flat
        style = (
            wx.TE_MULTILINE
            | wx.TE_READONLY
            | wx.TE_AUTO_URL
            | wx.TE_RICH2
            | wx.BORDER_NONE
        )

        self.text_ctrl = wx.TextCtrl(self, style=style)
        self.text_ctrl.SetValue(text_content)

        # Match the background color
        # This makes the text box blend in with the dialog background
        bg_color = self.GetBackgroundColour()
        self.text_ctrl.SetBackgroundColour(bg_color)

        # Set Monospace Font (Must be done BEFORE calculating size)
        f_size = int(font_size)
        mono_font = get_best_monospace_font()
        font_info = wx.FontInfo(f_size).FaceName(mono_font)
        mono_font = wx.Font(font_info)
        self.text_ctrl.SetFont(mono_font)

        # Manual Sizing
        # TextCtrl generally doesn't "Fit" as tightly as StaticText,
        # so we calculate the exact pixels needed.
        lines = text_content.split('\n')
        longest_line = max(lines, key=len) if lines else ""

        # Get width/height of the text using the current font
        w_text, h_text = self.text_ctrl.GetTextExtent(longest_line)

        # Calculate totals
        # We add small buffers (+20 width, +10 height) to ensure no scrollbars appear
        line_height = self.text_ctrl.GetTextExtent("Ty")[1]  # Height of a standard char
        total_height = (line_height * len(lines)) + 15
        total_width = w_text + 30

        self.text_ctrl.SetMinSize((total_width, total_height))

        # Bind the URL Click Event
        self.text_ctrl.Bind(wx.EVT_TEXT_URL, self.OnLinkClicked)

        # Add to sizer
        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 20)

        # Standard Buttons
        btn_sizer = self.CreateStdDialogButtonSizer(wx.OK)
        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM, 10)

        self.SetSizer(sizer)
        self.Layout()
        self.Fit()
        self.CenterOnParent()

    def OnLinkClicked(self, event):
        if event.MouseEvent.LeftUp():
            url = self.text_ctrl.GetRange(event.GetURLStart(), event.GetURLEnd())
            webbrowser.open(url)
        event.Skip()


def get_best_monospace_font() -> str:
    font_enum = wx.FontEnumerator()
    font_enum.EnumerateFacenames()
    available_fonts = font_enum.GetFacenames()

    # Preferred monospace fonts (order matters)
    monospace_fonts = [
        "Consolas",
        "Courier New",
        "Lucida Console",
        "MS Gothic",
        "NSimSun",
    ]

    # Pick the first available monospace font
    chosen_font = next(
        (f for f in monospace_fonts if f in available_fonts), "Courier New"
    )
    return chosen_font


class RedirectText:
    def __init__(self, my_text_ctrl: ANSITextCtrl) -> None:
        self.out = my_text_ctrl

    def write(self, string: str) -> None:
        wx.CallAfter(self.out.append_ansi_text, string)

    def flush(self):
        pass

    def isatty(self):
        # Pretend it's a TTY (so that we can use colorized output)
        return True

    def __getattr__(self, attr):
        return getattr(self.out, attr)


class NavButton(wx.Panel):
    """Custom navigation button for sidebar"""

    def __init__(self, parent, label, icon=None, deprecated=False, help=None):
        super().__init__(parent)
        self.selected = False
        self.static_text = None
        self.label = label
        self.deprecated = deprecated
        self.help = help

        # Use system colors
        self.normal_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.hover_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT)
        self.selected_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        self.selected_text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        self.normal_text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT)
        self.deprecated_colour = blend(self.normal_text_color, self.normal_color, 0.5)
        self.selected_deprecated_colour = blend(self.selected_text_color, self.selected_color, 0.5)

        self.SetForegroundColour(self.normal_text_color)
        self.SetBackgroundColour(self.normal_color)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Icon (using text as placeholder)
        if icon:
            icon_text = wx.StaticText(self, label=icon)
            font = icon_text.GetFont()
            font.PointSize += 2
            icon_text.SetFont(font)
            sizer.Add(icon_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15)

        # Label
        self.static_text = wx.StaticText(self, label=label)
        if help:
            self.static_text.SetToolTip(help)
        if deprecated:
            # Write them in italic
            font = self.static_text.GetFont()
            font.SetStyle(wx.FONTSTYLE_ITALIC)
            self.static_text.SetFont(font)
        sizer.Add(self.static_text, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        self.SetSizer(sizer)

        # Bind events for hover and click
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_hover)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)

        for child in self.GetChildren():
            child.Bind(wx.EVT_LEFT_DOWN, self.on_click)

    def on_hover(self, event):
        if not self.selected:
            self.SetBackgroundColour(self.hover_color)
            self.Refresh()

    def on_leave(self, event):
        if not self.selected:
            self.SetBackgroundColour(self.normal_color)
            self.Refresh()

    def on_click(self, event):
        event = wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.GetId())
        wx.PostEvent(self.GetEventHandler(), event)

    def set_selected(self, selected):
        self.selected = selected
        if selected:
            selected_color = self.selected_deprecated_colour if self.deprecated else self.selected_text_color
            self.SetBackgroundColour(self.selected_color)
            for child in self.GetChildren():
                if isinstance(child, wx.StaticText):
                    child.SetForegroundColour(selected_color)
        else:
            normal_color = self.deprecated_colour if self.deprecated else self.normal_text_color
            self.SetBackgroundColour(self.normal_color)
            for child in self.GetChildren():
                if isinstance(child, wx.StaticText):
                    child.SetForegroundColour(normal_color)
        self.Refresh()


class NormalEntry:
    longest_param_name = ""

    @classmethod
    def init_class(cls, param_name: str) -> None:
        cls.longest_param_name = param_name

    def __init__(self, **kwargs) -> None:
        self.param = kwargs["param"]
        self.parent = kwargs["parent"]
        self.entry = None
        self.text_error = None
        self.default_text = kwargs.get("default_text")
        self.hint = kwargs.get("hint")
        self.min_size = (200, -1)
        self.build_label()
        self.build_entry()
        self.build_button()
        self.build_error()

    def build_label(self) -> None:
        self.static_text = wx.StaticText(
            self.parent, -1, NormalEntry.longest_param_name + " *"
        )
        size = self.static_text.GetSize()
        self.static_text.SetMinSize(size)
        required = " *" if self.param.required else ""
        self.static_text.SetLabel(self.param.name + required)

        # Deprecated parameters
        if self.param.deprecated:
            # Make deprecated parameters faded
            bg = self.static_text.GetBackgroundColour()
            normal_colour = self.static_text.GetForegroundColour()
            deprecated_colour = blend(normal_colour, bg, 0.5)
            self.static_text.SetForegroundColour(deprecated_colour)

            # Write them in italic
            font = self.static_text.GetFont()
            font.SetStyle(wx.FONTSTYLE_ITALIC)
            self.static_text.SetFont(font)

        if hasattr(self.param, "help"):
            self.static_text.SetToolTip(self.param.help)

    def build_entry(self) -> None:
        # Password
        if hasattr(self.param, "hide_input") and self.param.hide_input:
            self.entry = wx.TextCtrl(self.parent, -1, style=wx.TE_PASSWORD)
        # Normal case
        else:
            self.entry = wx.TextCtrl(self.parent, -1)
            if self.hint:
                self.entry.SetHint(self.hint)
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(self.default_text)

    def build_button(self) -> None:
        pass

    def build_error(self) -> None:
        self.text_error = wx.StaticText(self.parent, -1, "")
        font = wx.Font(wx.FontInfo(8))
        self.text_error.SetMinSize(self.min_size)
        self.text_error.SetFont(font)
        self.text_error.SetForegroundColour((255, 0, 0))


class ChoiceEntry(NormalEntry):
    def build_entry(self) -> None:
        choices = [
            choice.name if isinstance(choice, enum.Enum) else str(choice)
            for choice in self.param.type.choices
        ]
        self.entry = wx.ComboBox(self.parent, -1, choices=choices)
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(self.default_text)
        if self.hint:
            self.entry.SetHint(self.hint)


class BoolEntry(NormalEntry):
    def build_entry(self) -> None:
        self.entry = wx.CheckBox(self.parent, -1)
        if not isinstance(self.default_text, bool):
            value = self.default_text == "True"
        else:
            value = self.default_text
        self.entry.SetValue(value)
        self.entry.Bind(wx.EVT_SET_FOCUS, self.on_focus)

    def on_focus(self, event):
        # Redirect focus away (to avoid the focus rect to be put on the empty labal)
        self.parent.SetFocus()


class SliderEntry(NormalEntry):
    def build_entry(self) -> None:
        initial_value = (
            int(self.default_text) if self.default_text else self.param.type.min
        )
        self.entry = wx.Slider(
            self.parent,
            value=initial_value,
            minValue=self.param.type.min,
            maxValue=self.param.type.max,
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS,
        )
        self.entry.SetMinSize(self.min_size)

        self.entry.SetTickFreq(
            int(
                math.pow(
                    10,
                    math.ceil(
                        math.log10(self.param.type.max - self.param.type.min) - 1
                    ),
                )
            )
        )


class PathEntry(NormalEntry):
    def __init__(self, **kwargs) -> None:
        self.callback = kwargs.get("callback")
        super().__init__(**kwargs)
        self.file_drop_target = MyFileDropTarget(self.entry)
        self.entry.SetDropTarget(self.file_drop_target)

    def build_button(self) -> None:
        self.button = wx.Button(self.parent, -1, "Browse")
        self.button.Bind(wx.EVT_BUTTON, self.callback)


class DateTimeEntry(NormalEntry):
    def __init__(self, **kwargs) -> None:
        self.button = None
        self.param = kwargs.get("param")
        print(dir(self.param))
        print(self.param.type.formats)
        self.callback = kwargs.get("callback")
        super().__init__(**kwargs)

    def build_entry(self) -> None:
        super().build_entry()
        # Set the 31 december 2025 13:00 as hint using the param format
        with contextlib.suppress(ValueError):
            self.entry.SetHint(datetime.datetime(2025, 12, 31, 13, 30, 50, 79233).strftime(self.param.type.formats[0]))

    def build_button(self) -> None:
        self.button = wx.Button(self.parent, -1, "Select")
        self.button.Bind(wx.EVT_BUTTON, self.callback)


class ParameterSection:
    def __init__(
        self,
        config: TOMLDocument,
        command_name: str,
        panel: CommandPanel,
        label: str,
        params: List[Union[Argument, Option]],
        main_boxsizer: wx.BoxSizer,
    ) -> None:
        self.params = params
        self.controls = {}  # param_name -> wx control
        self.boxsizer = None
        self.gbs = None
        self.panel = panel
        self.command_name = command_name
        self.config = config
        self.entry = {}
        self.text_error = {}
        self.static_text = {}

        if not params:
            return  # nothing to render

        # # StaticBox with bold font
        sb = wx.StaticBox(panel, label=label)
        sb.SetFont(wx.Font(wx.FontInfo(10).Bold()))

        # BoxSizer wrapping the StaticBox
        self.boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        main_boxsizer.Add(
            self.boxsizer, flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=5
        )

        # GridBagSizer for parameter controls
        self.gbs = wx.GridBagSizer(vgap=1, hgap=5)
        self.boxsizer.Add(self.gbs, 1, flag=wx.EXPAND | wx.ALL, border=5)

        # Build UI for each parameter
        self._populate()
        self.gbs.AddGrowableCol(1)

    def _populate(self) -> None:
        idx_param = -1
        for param in self.params:
            if (
                not param.is_eager
                # If using typer, these parameters are automatically added
                and param.name not in {"install_completion", "show_completion"}
                and (
                    (hasattr(param, "hidden") and not param.hidden)
                    or (not hasattr(param, "hidden"))
                )
            ):
                idx_param += 1
                try:
                    # If previous run, prefill this field with the one saved in
                    # history.toml
                    config_value = self.config[self.command_name][param.name]
                    prefilled_value = str(config_value) if config_value not in {UNSET, None} else ""
                except (TypeError, KeyError):
                    prefilled_value = None

                # If the parameter has an envvar, prefill with its value
                if param.envvar and param.value_from_envvar(param.envvar):
                    default_value = param.value_from_envvar(param.envvar)
                elif callable(param.default):
                    default_value = param.default()
                # If it is an Enum - Choice parameter
                elif isinstance(param.default, enum.Enum) and isinstance(
                    param.type, click.Choice
                ):
                    default_value = param.default.value
                # Otherwise, prefill with the default value if any
                else:
                    default_value = param.default

                hint_value = str(default_value) if default_value not in {UNSET, None} else ""
                # File
                if isinstance(param.type, click.File) or (
                    isinstance(param.type, click.Path) and param.type.file_okay
                ):
                    widgets = PathEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        hint=hint_value,
                        callback=lambda evt, param=param: self.file_open(
                            evt, param,
                        ),
                    )
                    # self.button[param.name] = widgets.button

                # Directory
                elif isinstance(param.type, click.Path) and param.type.dir_okay:
                    widgets = PathEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        hint=hint_value,
                        callback=lambda evt, param=param.name: self.dir_open(
                            evt, param
                        ),
                    )
                    # self.button[param.name] = widgets.button

                # Choice
                elif isinstance(param.type, click.Choice):
                    widgets = ChoiceEntry(
                        parent=self.panel, param=param, default_text=prefilled_value, hint=hint_value
                    )

                # bool
                elif isinstance(param.type, click.types.BoolParamType):
                    widgets = BoolEntry(
                        parent=self.panel, param=param, default_text=prefilled_value, hint=hint_value
                    )

                # IntRange: Slider only if min and max defined
                elif (
                    isinstance(param.type, click.types.IntRange)
                    and hasattr(param.type, "min")
                    and hasattr(param.type, "max")
                    and param.type.min is not None
                    and param.type.max is not None
                ):
                    widgets = SliderEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        hint=hint_value,
                        min_value=param.type.min,
                        max_value=param.type.max,
                    )

                # Date
                elif isinstance(param.type, click.types.DateTime):
                    widgets = DateTimeEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        hint=hint_value,
                        callback=lambda evt, param=param: self.date_time_picker(
                            evt, param,
                        ),
                    )
                else:
                    widgets = NormalEntry(
                        parent=self.panel, param=param, default_text=prefilled_value, hint=hint_value
                    )
                self.entry[param.name] = widgets.entry
                self.text_error[param.name] = widgets.text_error
                self.static_text[param.name] = widgets.static_text
                self.gbs.Add(widgets.static_text, (2 * idx_param, 0))
                self.gbs.Add(widgets.entry, flag=wx.EXPAND, pos=(2 * idx_param, 1))
                if hasattr(widgets, "button"):
                    self.gbs.Add(widgets.button, (2 * idx_param, 2))
                self.gbs.Add(
                    widgets.text_error, flag=wx.EXPAND, pos=(2 * idx_param + 1, 1)
                )
        # line = wx.StaticLine(p, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        # gbs.Add(line, (i+1, 0), (i+1, 3), wx.EXPAND|wx.RIGHT|wx.TOP, 5)

        # self.gbs.AddGrowableCol(1)
        # self.boxsizer.Add(self.gbs, 1, wx.EXPAND | wx.ALL, 10)
        # self.boxsizer.SetSizeHints(self.panel)

        # return self.panel

    def date_time_picker(self, event, param):
        # Identify required input types
        show_date = any(
            [
                bool(re.search(r"%[YymdUuVWjABbax]", format_str))
                for format_str in param.type.formats
            ]
        )
        show_time = any(
            [
                bool(re.search(r"%[HIpMSfzZX]", format_str))
                for format_str in param.type.formats
            ]
        )
        if show_time and not show_date:
            mode = "time"
        elif show_date and not show_time:
            mode = "date"
        else:
            mode = "datetime"
        mouse_pos = wx.GetMousePosition()
        if mode == "date":
            title = "Select Date"
        elif mode == "time":
            title = "Select Time"
        elif mode == "datetime":
            title = "Select Date & Time"
        dlg = wx.Dialog(self.panel, title=title, name="DatePicker")
        dlg.Move(mouse_pos)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Initialize the datetime picker with the time currently in the entry, if any
        datetime_obj = None
        current_text_entry = self.entry[param.name].GetValue()
        try:
            # Parse the string to a datetime object
            datetime_obj = datetime.datetime.strptime(current_text_entry, param.type.formats[0])

        except ValueError as exc:
            if "unconverted data remains" in str(exc):
                # If the string is too long, slice it to the length of a dummy formatted string
                # This keeps "12:50" and drops ":40"
                dummy_len = len(datetime.datetime.now().strftime(param.type.formats[0]))
                datetime_obj = datetime.datetime.strptime(current_text_entry[:dummy_len], param.type.formats[0])

        hbox = wx.BoxSizer(wx.VERTICAL)

        if mode in {"date", "datetime"}:
            self.date_picker = wx.adv.CalendarCtrl(dlg)
            if datetime_obj:
                # Set the date using wx.DateTime
                wx_date = wx.DateTime()
                wx_date.Set(datetime_obj.day, datetime_obj.month - 1, datetime_obj.year)
                self.date_picker.SetDate(wx_date)
            hbox.Add(self.date_picker, flag=wx.ALL | wx.CENTER, border=5)

        if mode in {"time", "datetime"}:
            self.time_picker = wx.adv.TimePickerCtrl(dlg)
            if datetime_obj:
                # Set the time using wx.DateTime
                wx_time = wx.DateTime()
                wx_time.SetHMS(datetime_obj.hour, datetime_obj.minute, datetime_obj.second)
                self.time_picker.SetValue(wx_time)
            hbox.Add(self.time_picker, flag=wx.ALL | wx.EXPAND, border=5)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(dlg, wx.ID_OK, label="OK")
        cancel_btn = wx.Button(dlg, wx.ID_CANCEL, label="Cancel")
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        vbox.Add(hbox, flag=wx.ALL | wx.CENTER, border=5)
        vbox.Add(btn_sizer, flag=wx.ALL | wx.CENTER, border=5)

        dlg.SetSizerAndFit(vbox)
        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            if mode == "date":
                self.entry[param.name].SetValue(
                    self.date_picker.GetDate().Format(param.type.formats[0])
                )
            elif mode == "time":
                self.entry[param.name].SetValue(
                    self.time_picker.GetValue().Format(param.type.formats[0])
                )
            else:
                # In case we have multiple formats, pick the most complete one (with more format specifiers)
                most_complete_format = max(
                    param.type.formats, key=lambda s: s.count("%")
                )
                self.entry[param.name].SetValue(
                    datetime.datetime.fromisoformat(
                        self.date_picker.GetDate().FormatISODate()
                        + " "
                        + self.time_picker.GetValue().FormatISOTime()
                    ).strftime(most_complete_format)
                )

    def dir_open(self, event, param):
        dlg = wx.DirDialog(
            self.panel,
            message="Choose Directory",
            defaultPath=os.getcwd(),
            style=wx.RESIZE_BORDER,
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            self.entry[param.name].SetValue(path)

    def file_open(self, event, param):
        # Should we let the user select multiple files?
        multiple = (hasattr(param, "multiple") and param.multiple) or (
            param.nargs != 1
        )
        # Read mode ?
        if (hasattr(param.type, "readable") and param.type.readable) or (
            hasattr(param.type, "mode") and "r" in param.type.mode
        ):
            mode = "read"
        # Write mode (overwrite readable if both are True)
        if (hasattr(param.type, "writable") and param.type.writable) or (
            hasattr(param.type, "mode") and "w" in param.type.mode
        ):
            mode = "write"
        # If help text is something like:
        # Excel file (.xlsx, .csv)
        # Text file (.txt or .log)
        # Extract the file type and the extensions, so that the file
        # dialog can filter the files
        wildcards = "All files|*.*"
        if hasattr(param, "help") and param.help:
            wildcard_raw = re.search(
                r"(\w+) file[s]? \(([a-zA-Z ,\.]*)\)", param.help
            )
            if wildcard_raw:
                file_type, extensions_raw = wildcard_raw.groups()
                extensions = re.findall(
                    r"\.(\w+(?:\.\w+)?)", extensions_raw
                )
                extensions_text = ";".join(
                    [f"*.{ext}" for ext in extensions]
                )
                wildcards = f"{file_type} files|{extensions_text}"
        path = self.entry[param.name].GetValue()
        message = "Choose a file"
        last_folder = Path(path).parent if path != "" else os.getcwd()
        if mode == "read":
            style = wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST
            if multiple:
                style |= wx.FD_MULTIPLE
                message = "Choose files"
        else:
            style = wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT
        dlg = wx.FileDialog(
            self.panel,
            message=message,
            defaultDir=str(last_folder),
            defaultFile="",
            wildcard=wildcards,
            style=style,
        )

        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            if multiple:
                path = json.dumps(dlg.GetPaths())
            else:
                path = dlg.GetPath()
            dlg.Destroy()
            self.entry[param.name].SetValue(path)


class CommandPanel(scrolled.ScrolledPanel):
    def __init__(
        self, parent: Guick, ctx: Context, name: str, config: TOMLDocument
    ) -> None:
        super().__init__(parent)
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        self.entries = {}
        self.text_errors = {}
        self.static_texts = {}
        self.ctx = ctx
        self.command_name = name
        self.config = config
        self.sections = {}
        self.SetupScrolling(scroll_x=False, scroll_y=True)

        # Get the command
        try:
            # If it is a group, get the subcommand
            command = ctx.command.commands.get(name)
        except AttributeError:
            # Otherwise, get the main command
            command = ctx.command

        # Set the longest parameter name for alignment
        with contextlib.suppress(ValueError):
            longest_param_name = max([param.name for param in command.params], key=len)
            NormalEntry.init_class(longest_param_name)

        main_boxsizer = wx.BoxSizer(wx.VERTICAL)
        panels = defaultdict(list)
        user_defined_panels = []
        for param in command.params:
            if (
                (not param.is_eager)
                and (
                    (hasattr(param, "hidden") and not param.hidden)
                    or (not hasattr(param, "hidden"))
                )
                and param.name not in {"install_completion", "show_completion"}
            ):
                if hasattr(param, "rich_help_panel") and (
                    panel_name := param.rich_help_panel
                ):
                    panels[panel_name].append(param)
                    if panel_name not in user_defined_panels:
                        user_defined_panels.append(panel_name)
                elif param.required:
                    panels["Required Parameters"].append(param)
                else:
                    panels["Optional Parameters"].append(param)
        list_panels = [
            "Required Parameters",
            *user_defined_panels,
            "Optional Parameters",
        ]

        for panel in list_panels:
            if panels[panel]:
                self.sections[panel] = ParameterSection(
                    self.config, command.name, self, panel, panels[panel], main_boxsizer
                )
                self.entries.update(self.sections[panel].entry)
                self.text_errors.update(self.sections[panel].text_error)
                self.static_texts.update(self.sections[panel].static_text)

        self.SetSizer(main_boxsizer)
        self.Layout()
        self.best_size = main_boxsizer.GetMinSize()

    def on_exit(self, event):
        self.Close()


class Guick(wx.Frame):
    def __init__(self, ctx: Context, size: wx.Size = None) -> None:
        wx.Frame.__init__(self, None, -1, ctx.command.name)
        self.ctx = ctx
        self.cmd_panels = {}

        # Create the menu bar
        self.create_help_menu()

        # Set history file name
        history_folder = (
            Path(click.get_app_dir("guick", roaming=False)) / "history" / ctx.info_name
        )
        history_folder.mkdir(parents=True, exist_ok=True)
        self.history_file = history_folder / "history.toml"

        # Load the history file if it exists
        self.config = tomlkit.document()
        try:
            with open(self.history_file, encoding="utf-8") as fp:
                self.config = tomlkit.load(fp)
        except FileNotFoundError:
            pass

        self.Bind(wx.EVT_CLOSE, self.on_exit)

        # Define key bindings for the SearchCtrl
        # Ctrl-F to open the SearchCtrl
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord("F"), 101)])
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(
            wx.EVT_MENU, lambda evt: self.log_panel.search_panel.show_search(), id=101
        )
        # ESC Key to close the SearchCtrl
        self.Bind(wx.EVT_CHAR_HOOK, self.on_global_char_hook)

        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        # If it is a group, create a right sidebar showing the commands
        if isinstance(ctx.command, click.Group):
            # Create the panels for each command
            self.create_parameters_panels()
            self._mgr.AddPane(
                self.nav_panel,
                aui.AuiPaneInfo()
                .Name("NavPanel")
                .Left()
                .MinSize((self.nav_size.width, -1))
                # .MinSize((250, -1))
                .Floatable(False)
                .Movable(False)
                .PaneBorder(False)
                .CaptionVisible(False)
                .Layer(1),
            )
            panel_width = -1
            panel_height = self.nav_size.height
            for panel_name in self.ctx.command.commands.keys():
                self._mgr.AddPane(
                    self.cmd_panels[panel_name],
                    aui.AuiPaneInfo()
                    .Name(panel_name)
                    .CenterPane()
                    .PaneBorder(False)
                    .Hide(),
                )
                if self.cmd_panels[panel_name].best_size.width > panel_width:
                    panel_width = self.cmd_panels[panel_name].best_size.width
                if self.cmd_panels[panel_name].best_size.height > panel_height:
                    panel_height = self.cmd_panels[panel_name].best_size.height
            self.show_panel(list(self.ctx.command.commands.keys())[0])

        # Otherwise, create a single panel
        else:
            self.nav_size = 0
            panel = CommandPanel(self, ctx, "", self.config)
            self.cmd_panels[ctx.command.name] = panel

            self._mgr.AddPane(
                panel,
                aui.AuiPaneInfo().Name("Command").CenterPane().PaneBorder(False),
            )
            panel_width = panel.best_size.width
            panel_height = panel.best_size.height

        # Create the OK/Cancel buttons
        button_panel, button_height = self.create_ok_cancel_buttons()

        self._mgr.AddPane(
            button_panel,
            aui.AuiPaneInfo()
            .MaximizeButton(False)
            .Resizable(False)
            .Bottom()
            .CloseButton(False)
            .Floatable(False)
            .Movable(False)
            .PaneBorder(False)
            .CaptionVisible(False)
            .MinSize(wx.Size(-1, button_height))
            .PaneBorder(False)
            .Layer(0),
        )

        # # Create the log
        log_panel_height = 200
        self.log_panel = LogPanel(self)
        self._mgr.AddPane(
            self.log_panel,
            aui.AuiPaneInfo()
            .Name("log")
            .Caption("Log")
            .Bottom()
            .CloseButton(False)
            .MaximizeButton(True)
            .MinimizeButton(True)
            .Resizable(True)
            .MinSize(wx.Size(-1, log_panel_height))
            .PaneBorder(False)
            .Layer(1),
        )

        # Customize the caption for Log panel
        art = self._mgr.GetArtProvider()
        art.SetColour(
            aui.AUI_DOCKART_INACTIVE_CAPTION_COLOUR,
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE),
        )
        art.SetColour(
            aui.AUI_DOCKART_INACTIVE_CAPTION_GRADIENT_COLOUR,
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE),
        )
        art.SetColour(aui.AUI_DOCKART_INACTIVE_CAPTION_TEXT_COLOUR, wx.BLACK)
        # Font caption in bold
        font = art.GetFont(aui.AUI_DOCKART_CAPTION_FONT)
        font.MakeBold()
        font.SetPointSize(font.GetPointSize() + 2)
        art.SetFont(aui.AUI_DOCKART_CAPTION_FONT, font)

        # Transparent hint while docking
        self._mgr.SetFlags(self._mgr.GetFlags() | aui.AUI_MGR_TRANSPARENT_HINT)

        sys.stdout = RedirectText(self.log_panel.log_ctrl)

        # Height: form height + button height + log height + buffer for AUI sashes/captions
        caption_size = art.GetMetric(aui.AUI_DOCKART_CAPTION_SIZE)
        sash_size = art.GetMetric(aui.AUI_DOCKART_SASH_SIZE)

        total_width = self.nav_size.width + panel_width + 30
        total_height = (
            panel_height + button_height + log_panel_height + caption_size + sash_size
        )

        screen_size = wx.GetClientDisplayRect()
        current_frame_size = self.GetSize()
        current_client_size = self.GetClientSize()

        decoration_height = current_frame_size.height - current_client_size.height

        max_client_height = screen_size.height - decoration_height

        safe_height = min(total_height, max_client_height)

        self.SetClientSize(wx.Size(total_width, safe_height))
        self.CenterOnScreen()
        self._mgr.Update()
        wx.CallAfter(self._unlock_log_sash)

        # If a larger size is specified, apply it
        if size:
            current_size = self.GetClientSize()
            new_width = (
                max(size[0], current_size.width)
                if size[0] != -1
                else current_size.width
            )
            new_height = (
                max(size[1], current_size.height)
                if size[1] != -1
                else current_size.height
            )
            self.SetClientSize((new_width, new_height))

        # self.CreateStatusBar()
        # self.SetStatusText("")

        self.Centre()

        self.Show()

    def _unlock_log_sash(self):
        # Retrieve the form pane info
        pane = self._mgr.GetPane("log")
        if pane.IsOk():
            # Lower the MinSize to allow the user to shrink it later
            pane.MinSize(wx.Size(-1, -1))
            # Update AUI. Since the frame is already large enough,
            # it won't shrink the pane visually, but it WILL unlock the sash!
            self._mgr.Update()

    def create_parameters_panels(self):
        # Right panel for content
        content_panel = wx.Panel(self)
        content_panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        content_sizer = wx.BoxSizer(wx.VERTICAL)

        for name in self.ctx.command.commands:
            command = self.ctx.command.commands.get(name)
            panel = CommandPanel(content_panel, self.ctx, name, self.config)
            panel.Hide()
            self.cmd_panels[name] = panel
            content_sizer.Add(panel, 1, wx.EXPAND)

        content_panel.SetSizer(content_sizer)
        return content_panel

    def create_ok_cancel_buttons(self) -> wx.Panel:
        # Button panel at the bottom
        button_panel = wx.Panel(self)
        button_panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        button_sizer.AddStretchSpacer()

        ok_btn = wx.Button(button_panel, wx.ID_OK, "OK")
        cancel_btn = wx.Button(button_panel, wx.ID_CANCEL, "Cancel")

        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok_button)
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_close_button)

        button_sizer.Add(ok_btn, 0, wx.ALL, 10)
        button_sizer.Add(cancel_btn, 0, wx.TOP | wx.BOTTOM | wx.RIGHT, 10)

        button_panel.SetSizer(button_sizer)
        return button_panel

    def create_left_sidebar(self):

        # Left sidebar for navigation
        nav_panel = wx.Panel(self)
        nav_panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        nav_panel.SetMinSize((250, -1))

        nav_sizer = wx.BoxSizer(wx.VERTICAL)

        # Add title to sidebar
        title = wx.StaticText(nav_panel, label="Commands")
        font = title.GetFont()
        font.PointSize += 2
        font = font.Bold()
        title.SetFont(font)
        nav_sizer.Add(title, 0, wx.ALL, 5)

        # Navigation buttons
        self.nav_buttons = []
        self.cmd_panels = {}
        for name, command in self.ctx.command.commands.items():
            btn = NavButton(nav_panel, name, deprecated=command.deprecated, help=command.help)
            btn.Bind(
                wx.EVT_BUTTON, lambda e, panel_name=name: self.show_panel(panel_name)
            )
            nav_sizer.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
            self.nav_buttons.append((name, btn))

        nav_panel.SetSizer(nav_sizer)
        return nav_panel

    def show_panel(self, panel_name):
        """Switch to the selected panel"""
        # Hide all panels
        for name, panel in self.cmd_panels.items():
            panel.Hide()

        # Show selected panel
        if panel_name in self.cmd_panels:
            self.cmd_panels[panel_name].Show()

        # Update button selection
        for name, btn in self.nav_buttons:
            btn.set_selected(name == panel_name)

        self._mgr.Update()

    def create_help_menu(self) -> None:
        # Create Help menu
        menubar = wx.MenuBar()
        help_menu = wx.Menu()
        help_item = wx.MenuItem(help_menu, -1, "&Help")
        help_menu.Append(help_item)
        self.Bind(wx.EVT_MENU, self.on_help, help_item)

        # If version option defined, add a version menu
        if any(
            param.name == "version" and param.is_eager
            for param in self.ctx.command.params
        ):
            # Get version before redirecting stdout
            self.version = self.get_version()

            version_item = wx.MenuItem(help_menu, -1, "&Version")
            help_menu.Append(version_item)
            self.Bind(wx.EVT_MENU, self.OnVersion, version_item)

        menubar.Append(help_menu, "&Help")
        self.SetMenuBar(menubar)

    def on_exit(self, event):
        # Destroys the main frame which quits the wxPython application
        self.Destroy()
        sys.exit()

    def on_global_char_hook(self, event):
        """Handle ESC key globally to close search."""
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            if self.log_panel.search_panel.IsShown():
                self.log_panel.search_panel.on_close()
            else:
                event.Skip()
        else:
            event.Skip()

    def on_help(self, event):
        head = self.ctx.command.name

        if isinstance(self.ctx.command, (TyperCommandGui, TyperGroupGui)):
            import unittest.mock as mock
            from contextlib import redirect_stdout

            f = io.StringIO()
            with mock.patch("os.get_terminal_size", return_value=os.terminal_size((100, 20))):
                with redirect_stdout(f):
                    help_text = self.ctx.command.get_help(self.ctx)

                description = f.getvalue()

        else:
            formatter = click.HelpFormatter()
            self.ctx.command.format_help(self.ctx, formatter)
            description = self.ctx.command.get_help(self.ctx)
        dlg = AboutDialog(self, "Help", head, description, name="HelpDialog")
        dlg.ShowModal()
        dlg.Destroy()

    def get_version(self):
        for param in self.ctx.command.params:
            if param.name == "version":
                with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                    try:
                        param.callback(self.ctx, param, True)
                    except Exception:
                        pass
                    output = buf.getvalue()
                    break
        return output

    def OnVersion(self, event):
        head = self.ctx.command.name

        dlg = AboutDialog(self, "About", head, self.version, name="VersionDialog")
        dlg.ShowModal()
        dlg.Destroy()

    def on_close_button(self, event):
        sys.exit()

    def on_ok_button(self, event) -> None:
        sel_cmd_name, sel_cmd_panel = [
            (name, cmd_panel)
            for name, cmd_panel in self.cmd_panels.items()
            if cmd_panel.IsShown()
        ][0]

        # Get the selected command
        try:
            selected_command = self.ctx.command.commands.get(sel_cmd_name)
        except AttributeError:
            selected_command = self.ctx.command

        # If the command section does not exist in the history file, create it
        if sel_cmd_name and sel_cmd_name not in self.config:
            script_history = tomlkit.table()
            self.config.add(sel_cmd_name, script_history)

        opts = {}
        errors = {}
        for key, entry in sel_cmd_panel.entries.items():
            value = entry.GetValue()
            if value in {"", UNSET, None}:
                opts[key] = entry.GetHint()
                if opts[key] == "":
                    # Empty value: different behaviour depending on Click or Typer
                    if isinstance(selected_command, TYPER_TYPES):
                        opts[key] = None
                    elif isinstance(selected_command, click.Command):
                        opts[key] = UNSET
            else:
                param = [p for p in selected_command.params if p.name == key][0]
                if param.nargs not in (None, 1) or (hasattr(param, "multiple") and param.multiple):
                    # Try to parse as JSON to handle lists
                    try:
                        opts[key] = json.loads(value)
                    except json.JSONDecodeError:
                        errors[param.name] = "Unexpected error in the list, probably a syntax error?"
                        opts[key] = ""
                else:
                    opts[key] = entry.GetValue()
        args = []

        # Parse parameters and save errors if any
        self.ctx.params = {}
        for param in selected_command.params:
            # Remove default to avoid having user empty fields being set to default
            # values without knowing it
            if not (hasattr(param, "hidden") and param.hidden):
                param.default = UNSET
            if param.name in errors:
                continue
            try:
                _, args = param.handle_parse_result(self.ctx, opts, args)
            except click.exceptions.BadParameter as exc:
                errors[exc.param.name] = exc
            except Exception as exc:
                # Don't overwrite existing errors
                if param.name not in errors:
                    errors[param.name] = "Unexpected error, probably a syntax error?"

        # Display errors if any
        for param in selected_command.params:
            if (hasattr(param, "hidden") and not param.hidden) or (
                not hasattr(param, "hidden")
            ):
                if errors.get(param.name):
                    sel_cmd_panel.text_errors[param.name].SetLabel(
                        "‼️ " + str(errors[param.name])
                    )
                    sel_cmd_panel.text_errors[param.name].SetToolTip(
                        str(errors[param.name])
                    )
                else:
                    with contextlib.suppress(KeyError):
                        sel_cmd_panel.text_errors[param.name].SetLabel("")

        # If there are errors, we stop here
        if errors:
            return

        # Save the parameters to the history file
        for param in selected_command.params:
            # Save each parameter except hidden ones and password fields
            if not (hasattr(param, "hide_input") and param.hide_input):
                with contextlib.suppress(KeyError, tomlkit.exceptions.ConvertError):
                    self.config[sel_cmd_name][param.name] = opts[param.name]
        with open(self.history_file, mode="w", encoding="utf-8") as fp:
            tomlkit.dump(self.config, fp)

        # Invoke the command in a separate thread to avoid blocking the GUI
        self.ctx.args = args
        self.thread = Thread(
            target=selected_command.invoke, args=(self.ctx,), daemon=True
        )
        self.thread.start()


class CommonGui:
    def __init__(self, *args, size=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.size = size

    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        # If args defined on the command line, use the CLI
        if args:
            args = super().parse_args(ctx, args)
            return args

        app = wx.App()
        frame = Guick(ctx, size=self.size)
        frame.Show()
        app.MainLoop()


class GroupGui(CommonGui, click.Group):
    pass



class CommandGui(CommonGui, click.Command):
    pass


with contextlib.suppress(NameError):
    class TyperCommandGui(CommonGui, TyperCommand):
        pass

    class TyperGroupGui(CommonGui, TyperGroup):
        pass
