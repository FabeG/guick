import contextlib
import datetime
import io
import math
import os
import re
import sys
import time
import typing as t
import webbrowser
from enum import Enum, IntEnum
from pathlib import Path
from threading import Thread

import click
import platformdirs
import tomlkit
import wx
import wx.html
import wx.lib.scrolledpanel as scrolled
from wx.lib.newevent import NewEvent

from click._utils import UNSET


# Regex pattern to match ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[((?:\d+;)*\d+)m')


# Windows Terminal Colors
# Mapping ANSI color codes to HTML colors
# From https://devblogs.microsoft.com/commandline/updating-the-windows-console-colors/
class TermColors(Enum):
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


class AnsiEscapeCodes(IntEnum):
    ResetFormat = 0
    BoldText = 1
    UnderLinedText = 4
    TextColorStart = 30
    TextColorEnd = 37
    TextBrightColorStart = 90
    TextBrightColorEnd = 97
    BackgroundColorStart = 40
    BackgroundColorEnd = 47
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
}





class ANSITextCtrl(wx.TextCtrl):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_READONLY)
        self.parent = parent
        self.gauge = parent.gauge
        self.gauge_sizer = parent.gauge_sizer
        self.gauge_text = parent.gauge_text
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
        bold_fg = False
        bold_bg = False
        # Split the message by ANSI codes
        for match in ANSI_ESCAPE_PATTERN.finditer(message):
            # Add text before the ANSI code
            if match.start() > last_end:
                segments.append((message[last_end:match.start()], current_fg, current_bg, underline, bold_fg, bold_bg))

            # Extract and interpret ANSI code parameters
            params_str = match.group(1)
            params = [int(p) for p in params_str.split(';') if p]
            for param in params:
                # Process ANSI parameters
                if param == AnsiEscapeCodes.ResetFormat:
                    current_fg = self.default_fg
                    current_bg = self.default_bg
                    underline = False
                    bold_fg = False
                    bold_bg = False
                elif param == AnsiEscapeCodes.UnderLinedText:
                    underline = True
                elif param == AnsiEscapeCodes.BoldText:
                    bold_fg = True
                elif AnsiEscapeCodes.BackgroundColorStart <= param <= AnsiEscapeCodes.BackgroundColorEnd:
                    current_bg = ANSI_COLORS[param - AnsiEscapeCodes.BackgroundColorStart]
                elif AnsiEscapeCodes.TextColorStart <= param <= AnsiEscapeCodes.TextColorEnd:
                    current_fg = ANSI_COLORS[param - AnsiEscapeCodes.TextColorStart]
                elif AnsiEscapeCodes.BackgroundBrightColorStart <= param <= AnsiEscapeCodes.BackgroundBrightColorEnd:
                    current_bg = ANSI_COLORS[param - AnsiEscapeCodes.BackgroundBrightColorStart]
                    bold_bg = True
                elif AnsiEscapeCodes.TextBrightColorStart <= param <= AnsiEscapeCodes.TextBrightColorEnd:
                    current_fg = ANSI_COLORS[param - AnsiEscapeCodes.TextBrightColorStart]
                    bold_fg = True

            last_end = match.end()

        # Add remaining text
        if last_end < len(message):
            segments.append((message[last_end:], current_fg, current_bg, underline, bold_fg, bold_bg))

        # Apply text and styles
        for text, fg, bg, ul, bold_fg, bold_bg in segments:
            if text:
                # Create a font that matches the default one but with underline if needed
                font = self.GetFont()
                if ul:
                    font.SetUnderlined(True)
                else:
                    font.SetUnderlined(False)
                # Create text attribute with the font
                if bold_fg:
                    color_fg = TermColors["BRIGHT_" + fg.name]
                else:
                    color_fg = TermColors[fg.name]
                if bold_bg:
                    color_bg = TermColors["BRIGHT_" + bg.name]
                else:
                    color_bg = TermColors[bg.name]

                style = wx.TextAttr(wx.Colour(*color_fg.value), wx.Colour(*color_bg.value), font)
                self.SetDefaultStyle(style)
                # Regex to extract the progress bar value from the tqdm output
                regex_tqdm = re.match(r"\r([\d\s]+)%\|.*\|(.*)", text)
                if regex_tqdm:
                    if not self.gauge_is_visible:
                        self.gauge_sizer.ShowItems(True)
                        self.gauge_is_visible = True
                        self.parent.Layout()
                    self.gauge_value = int(regex_tqdm.group(1))
                    self.gauge.SetValue(self.gauge_value)
                    self.gauge_text.SetValue(regex_tqdm.group(2))
                else:
                    self.AppendText(text)
        # Reset style at the end
        default_font = self.GetFont()
        default_font.SetUnderlined(False)
        self.SetDefaultStyle(wx.TextAttr(wx.Colour(*self.default_fg.value), wx.Colour(*self.default_bg.value), default_font))


class LogPanel(wx.Panel):
    """A panel containing a shared log in a StaticBox."""
    def __init__(self, parent):
        super().__init__(parent)

        sb = wx.StaticBox(self, label="Log")
        font = wx.Font(wx.FontInfo(10).Bold())
        sb.SetFont(font)
        box_sizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        # Create the progessbar in case of tqdm
        self.gauge = wx.Gauge(self, -1, 100, size=(-1, 5))
        font = get_best_monospace_font()
        self.gauge_text = wx.TextCtrl(self, -1, "", size=(400, -1), style=wx.TE_READONLY | wx.NO_BORDER)
        self.gauge_text.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=font))
        self.gauge_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.gauge_sizer.Add(self.gauge, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        self.gauge_sizer.Add(self.gauge_text, 0, wx.EXPAND | wx.ALL, 2)
        # Create the log
        self.log_ctrl = ANSITextCtrl(self)
        self.log_ctrl.SetMinSize((100, 200))
        self.log_ctrl.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=font))
        self.log_ctrl.SetBackgroundColour(wx.Colour(*TermColors.BLACK.value))

        box_sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 2)
        box_sizer.Add(self.gauge_sizer, 0, wx.EXPAND | wx.ALL, 2)
        self.gauge_sizer.Show(self.gauge_text, False)
        self.gauge_sizer.Show(self.gauge, False)
        self.SetSizer(box_sizer)
        box_sizer.SetSizeHints(self)
        self.Layout()


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, obj):
        wx.FileDropTarget.__init__(self)
        self.obj = obj

    def OnDropFiles(self, x, y, filenames):
        self.obj.SetValue("")
        self.obj.WriteText(filenames[0])
        return True


class AboutDialog(wx.Frame):
    def __init__(self, parent, title, head, description, font=None):
        super().__init__(parent, title=title)

        # Create a panel to hold the text control and button
        panel = wx.Panel(self)

        # Create a sizer for the panel to manage layout
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Create the TextCtrl (HTML content)
        self.html = wx.TextCtrl(panel, size=(600, 200), style=wx.TE_AUTO_URL | wx.TE_MULTILINE | wx.TE_READONLY)

        if font == "monospace":
            font = get_best_monospace_font()
            self.html.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=font))
        self.html.WriteText(head)
        self.html.WriteText("\n\n")
        self.html.WriteText(description)
        # Ensure the text starts at the beginning
        self.html.SetInsertionPoint(0)

        # Add TextCtrl to sizer
        sizer.Add(self.html, 1, wx.EXPAND | wx.ALL, 10)

        # Create the Close Button
        close_button = wx.Button(panel, label="Close")
        sizer.Add(close_button, 0, wx.CENTER | wx.TOP | wx.BOTTOM, 10)

        # Bind the button to close the dialog
        close_button.Bind(wx.EVT_BUTTON, self.OnClose)
        self.html.Bind(wx.EVT_TEXT_URL, self.OnLinkClicked)

        # Set the sizer for the panel
        panel.SetSizerAndFit(sizer)

        # Set the size of the frame to fit the panel
        self.Fit()

        # Show the frame
        self.Show()

    def OnLinkClicked(self, event):
        if event.MouseEvent.LeftUp():
            url = self.html.GetRange(event.GetURLStart(), event.GetURLEnd())
            webbrowser.open(url)
        event.Skip()

    def OnClose(self, event):
        # Close the window when the button is clicked
        self.Close()


def get_best_monospace_font():
    font_enum = wx.FontEnumerator()
    font_enum.EnumerateFacenames()
    available_fonts = font_enum.GetFacenames()

    # Preferred monospace fonts (order matters)
    monospace_fonts = ["Consolas", "Courier New", "Lucida Console", "MS Gothic", "NSimSun"]

    # Pick the first available monospace font
    chosen_font = next((f for f in monospace_fonts if f in available_fonts), "Courier New")
    return chosen_font


class RedirectText:
    def __init__(self, my_text_ctrl):
        self.out = my_text_ctrl

    def write(self, string):
        wx.CallAfter(self.out.append_ansi_text, string)

    def flush(self):
        pass


class NormalEntry:
    longest_param_name = ""

    @classmethod
    def init_class(cls, param_name):
        cls.longest_param_name = param_name

    def __init__(self, **kwargs):
        self.param = kwargs["param"]
        self.parent = kwargs["parent"]
        self.entry = None
        self.text_error = None
        self.default_text = kwargs.get("default_text")
        self.min_size = (100, -1)
        self.build_label()
        self.build_entry()
        self.build_button()
        self.build_error()

    def build_label(self):
        self.static_text = wx.StaticText(self.parent, -1, NormalEntry.longest_param_name + " *")
        size = self.static_text.GetSize()
        self.static_text.SetMinSize(size)
        required = " *" if self.param.required else ""
        self.static_text.SetLabel(self.param.name + required)
        if hasattr(self.param, "help"):
            self.static_text.SetToolTip(self.param.help)

    def build_entry(self):
        # Password
        if hasattr(self.param, "hide_input") and self.param.hide_input:
            self.entry = wx.TextCtrl(
                self.parent, -1, size=(500, -1), style=wx.TE_RICH | wx.TE_PASSWORD
            )
        # Normal case
        else:
            self.entry = wx.TextCtrl(self.parent, -1, size=(500, -1), style=wx.TE_RICH)
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(self.default_text)

    def build_button(self):
        pass

    def build_error(self):
        self.text_error = wx.StaticText(self.parent, -1, "", size=(500, -1))
        font = wx.Font(wx.FontInfo(8))
        self.text_error.SetMinSize(self.min_size)
        self.text_error.SetFont(font)
        self.text_error.SetForegroundColour((255, 0, 0))


class ChoiceEntry(NormalEntry):
    def build_entry(self):
        self.entry = wx.ComboBox(
            self.parent,
            -1,
            size=(500, -1),
            choices=[
                choice.name
                if isinstance(choice, enum.Enum)
                else str(choice)
                for choice in self.param.type.choices
            ]
        )
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(self.default_text)


class BoolEntry(NormalEntry):
    def build_entry(self):
        self.entry = wx.CheckBox(self.parent, -1)
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(bool(self.default_text))


class SliderEntry(NormalEntry):
    def build_entry(self):
        initial_value = int(self.default_text) if self.default_text else self.param.type.min
        self.entry = wx.Slider(
            self.parent, value=initial_value, minValue=self.param.type.min, maxValue=self.param.type.max,
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS
            )
        self.entry.SetMinSize(self.min_size)

        self.entry.SetTickFreq(int(math.pow(10, math.ceil(math.log10(self.param.type.max - self.param.type.min) - 1))))


class PathEntry(NormalEntry):
    def __init__(self, **kwargs):
        self.callback = kwargs.get("callback")
        super().__init__(**kwargs)
        self.file_drop_target = MyFileDropTarget(self.entry)
        self.entry.SetDropTarget(self.file_drop_target)

    def build_button(self):
        self.button = wx.Button(self.parent, -1, "Browse")
        self.button.Bind(
            wx.EVT_BUTTON, self.callback
        )


class DateTimeEntry(NormalEntry):
    def __init__(self, **kwargs):
        self.button = None
        self.param = kwargs.get("param")
        print(dir(self.param))
        print(self.param.type.formats)
        self.callback = kwargs.get("callback")
        super().__init__(**kwargs)

    def build_button(self):
        self.button = wx.Button(self.parent, -1, "Browse")
        self.button.Bind(
            wx.EVT_BUTTON, self.callback
        )


class ParameterSection:
    def __init__(self, config, command_name, panel, label, params, main_boxsizer):
        self.params = params
        self.controls = {}  # param_name -> wx control
        self.boxsizer = None
        self.gbs = None
        self.panel = panel
        self.command_name = command_name
        self.config = config
        self.entry = {}
        self.text_error = {}

        if not params:
            return  # nothing to render

        # StaticBox with bold font
        sb = wx.StaticBox(panel, label=label)
        sb.SetFont(wx.Font(wx.FontInfo(10).Bold()))

        # BoxSizer wrapping the StaticBox
        self.boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        main_boxsizer.Add(
            self.boxsizer,
            flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            border=10
        )

        # GridBagSizer for parameter controls
        self.gbs = wx.GridBagSizer(vgap=1, hgap=5)
        self.boxsizer.Add(self.gbs, flag=wx.EXPAND | wx.ALL, border=5)

        # Build UI for each parameter
        self._populate()
        self.gbs.AddGrowableCol(1)

    def _populate(self):
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
                    prefilled_value = self.config[self.command_name][param.name]
                except (TypeError, KeyError):
                    # If the parameter has an envvar, prefill with its value
                    if param.envvar and param.value_from_envvar(param.envvar):
                        prefilled_value = param.value_from_envvar(param.envvar)
                    # If it is an Enum - Choice parameter
                    elif isinstance(param.default, Enum) and isinstance(param.type, click.Choice):
                        prefilled_value = str(param.default.value) if param.default else ""
                    # Otherwise, prefill with the default value if any
                    else:
                        prefilled_value = str(param.default) if param.default and repr(param.default) != "Sentinel.UNSET" else ""

                # File
                if isinstance(param.type, click.File) or (isinstance(param.type, click.Path) and param.type.file_okay):
                    # Read mode
                    if (hasattr(param.type, "readable") and param.type.readable) or (hasattr(param.type, "mode") and "r" in param.type.mode):
                        mode = "read"
                    # Write mode
                    elif (hasattr(param.type, "writable") and param.type.writable) or (hasattr(param.type, "mode") and "w" in param.type.mode):
                        mode = "write"
                    # If help text is something like:
                    # Excel file (.xlsx, .csv)
                    # Text file (.txt or .log)
                    # Extract the file type and the extensions, so that the file
                    # dialog can filter the files
                    wildcards = "All files|*.*"
                    if hasattr(param, "help") and param.help:
                        wildcard_raw = re.search(r"(\w+) file[s]? \(([a-zA-Z ,\.]*)\)", param.help)
                        if wildcard_raw:
                            file_type, extensions_raw = wildcard_raw.groups()
                            extensions = re.findall(r"\.(\w+(?:\.\w+)?)", extensions_raw)
                            extensions_text = ";".join([f"*.{ext}" for ext in extensions])
                            wildcards = f"{file_type} files|{extensions_text}"
                    widgets = PathEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        callback=lambda evt, panel=self.panel, param=param.name, wildcards=wildcards, mode=mode: self.file_open(evt, panel, param, wildcards, mode),
                    )
                    # self.button[param.name] = widgets.button

                # Directory
                elif (isinstance(param.type, click.Path) and param.type.dir_okay):
                    widgets = PathEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        callback=lambda evt, panel=self.panel, param=param.name: self.dir_open(evt, panel, param),
                    )
                    # self.button[param.name] = widgets.button

                # Choice
                elif isinstance(param.type, click.Choice):
                    widgets = ChoiceEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value
                    )

                # bool
                elif isinstance(param.type, click.types.BoolParamType):
                    widgets = BoolEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value
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
                        min_value=param.type.min,
                        max_value=param.type.max
                    )

                # Date
                elif isinstance(param.type, click.types.DateTime):
                    # Identify required input types
                    show_date = any([bool(re.search(r"%[YymdUuVWjABbax]", format_str)) for format_str in param.type.formats])
                    show_time = any([bool(re.search(r"%[HIpMSfzZX]", format_str)) for format_str in param.type.formats])
                    if show_time and not show_date:
                        mode = "time"
                    elif show_date and not show_time:
                        mode = "date"
                    else:
                        mode = "datetime"
                    print(param.name, mode)
                    widgets = DateTimeEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value,
                        callback=lambda evt, param=param, mode=mode: self.date_time_picker(evt, param, mode),
                        mode=mode,
                    )
                else:
                    widgets = NormalEntry(
                        parent=self.panel,
                        param=param,
                        default_text=prefilled_value
                    )
                self.entry[param.name] = widgets.entry
                self.text_error[param.name] = widgets.text_error
                self.gbs.Add(widgets.static_text, (2 * idx_param, 0))
                self.gbs.Add(widgets.entry, flag=wx.EXPAND, pos=(2 * idx_param, 1))
                if hasattr(widgets, "button"):
                    self.gbs.Add(widgets.button, (2 * idx_param, 2))
                self.gbs.Add(widgets.text_error, flag=wx.EXPAND, pos=(2 * idx_param + 1, 1))
        # line = wx.StaticLine(p, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        # gbs.Add(line, (i+1, 0), (i+1, 3), wx.EXPAND|wx.RIGHT|wx.TOP, 5)

        # self.gbs.AddGrowableCol(1)
        # self.boxsizer.Add(self.gbs, 1, wx.EXPAND | wx.ALL, 10)
        # self.boxsizer.SetSizeHints(self.panel)

        # return self.panel

    def date_time_picker(self, event, param, mode="datetime"):
        mouse_pos = wx.GetMousePosition()
        if mode == "date":
            title = "Select Date"
        elif mode == "time":
            title = "Select Time"
        elif mode == "datetime":
            title = "Select Date & Time"
        dlg = wx.Dialog(self.panel, title=title)
        dlg.Move(mouse_pos)
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        if mode in {"date", "datetime"}:
            self.date_picker = wx.adv.DatePickerCtrl(dlg, style=wx.adv.DP_DROPDOWN)
            hbox.Add(self.date_picker, flag=wx.ALL | wx.CENTER, border=5)
        if mode in {"time", "datetime"}:
            self.time_picker = wx.adv.TimePickerCtrl(dlg)
            hbox.Add(self.time_picker, flag=wx.ALL | wx.CENTER, border=5)

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
            # This returns a Python list of files that were selected.
            dlg.Destroy()
            if mode == "date":
                self.entry[param.name].SetValue(self.date_picker.GetValue().Format(param.type.formats[0]))
            elif mode == "time":
                self.entry[param.name].SetValue(self.time_picker.GetValue().Format(param.type.formats[0]))
            else:
                # In case we have multiple formats, pick the most complete one (with more format specifiers)
                most_complete_format = max(param.type.formats, key=lambda s: s.count('%'))
                self.entry[param.name].SetValue(datetime.datetime.fromisoformat(self.date_picker.GetValue().FormatISODate() + " " + self.time_picker.GetValue().FormatISOTime()).strftime(most_complete_format))

    def dir_open(self, event, panel, param):
        dlg = wx.DirDialog(
            panel, message="Choose Directory",
            defaultPath=os.getcwd(),
            style=wx.RESIZE_BORDER
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            self.entry[param].SetValue(path)

    def file_open(self, event, panel, param, wildcards="All files|*.*", mode="read"):
        path = self.entry[param].GetValue()
        last_folder = Path(path).parent if path != "" else os.getcwd()
        if mode == "read":
            style = wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST
        else:
            style = wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT
        dlg = wx.FileDialog(
            panel,
            message="Choose a file",
            defaultDir=str(last_folder),
            defaultFile="",
            wildcard=wildcards,
            style=style,
        )

        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            path = dlg.GetPath()
            dlg.Destroy()
            self.entry[param].SetValue(path)


class CommandPanel(wx.Panel):
    def __init__(self, parent, ctx, name, history_file):
        super().__init__(parent, -1)
        self.entries = {}
        self.text_errors = {}
        self.history_file = history_file
        self.ctx = ctx
        self.command_name = name

        # Load the history file if it exists
        self.config = tomlkit.document()
        try:
            with open(self.history_file, encoding="utf-8") as fp:
                self.config = tomlkit.load(fp)
        except FileNotFoundError:
            pass

        # Get the command
        try:
            # If it is a group, get the subcommand
            command = ctx.command.commands.get(name)
        except AttributeError:
            # Otherwise, get the main command
            command = ctx.command

        # Set the longest parameter name for alignment
        longest_param_name = max([param.name for param in command.params], key=len)
        NormalEntry.init_class(longest_param_name)

        main_boxsizer = wx.BoxSizer(wx.VERTICAL)
        panels = defaultdict(list)
        user_defined_panels = []
        for param in command.params:
            if hasattr(param, "rich_help_panel") and (panel_name := param.rich_help_panel):
                panels[panel_name].append(param)
                if panel_name not in user_defined_panels:
                    user_defined_panels.append(panel_name)
            elif param.required:
                panels["Required Parameters"].append(param)
            else:
                panels["Optional Parameters"].append(param)
        list_panels = ["Required Parameters", *user_defined_panels, "Optional Parameters"]

        for panel in list_panels:
            if panels[panel]:
                self.sections = ParameterSection(
                    self.config,
                    command.name,
                    self,
                    panel,
                    panels[panel],
                    main_boxsizer
                )
                self.entries.update(self.sections.entry)
                self.text_errors.update(self.sections.text_error)

        # Buttons OK / Close at the bottom
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(self, -1, label="Ok")
        hbox.Add(
            ok_button,
            flag=wx.BOTTOM | wx.RIGHT,
            border=2,
        )
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok_button)

        cancel_button = wx.Button(self, label="Cancel")
        hbox.Add(
            cancel_button,
            flag=wx.BOTTOM | wx.LEFT,
            border=2,
        )
        cancel_button.Bind(wx.EVT_BUTTON, self.on_close_button)
        main_boxsizer.Add(hbox, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.TOP, 10)
        self.SetSizerAndFit(main_boxsizer)

    def on_close_button(self, event):
        sys.exit()

    def on_ok_button(self, event):

        # If the command section does not exist in the history file, create it
        if self.command_name and self.command_name not in self.config:
            script_history = tomlkit.table()
            self.config.add(self.command_name, script_history)

        opts = {
            key: entry.GetValue() if entry.GetValue() != "" else UNSET
            for key, entry in self.entries.items()
        }
        # hidden_opts = {
        #     param.name: param.default for param in self.ctx.command.params if param.hidden
        # }
        # opts = {**opts, **hidden_opts}
        args = []
        errors = {}
        # Get the selected command
        try:
            selected_command = self.ctx.command.commands.get(self.command_name)
        except AttributeError:
            selected_command = self.ctx.command

        # Parse parameters and save errors if any
        self.ctx.params = {}
        for param in selected_command.params:
            print(param)
            try:
                _, args = param.handle_parse_result(self.ctx, opts, args)
            except Exception as exc:
                errors[exc.param.name] = exc

        # Display errors if any
        for param in selected_command.params:
            if (hasattr(param, "hidden") and not param.hidden) or (not hasattr(param, "hidden")):
                if errors.get(param.name):
                    self.text_errors[param.name].SetLabel(str(errors[param.name]))
                    self.text_errors[param.name].SetToolTip(str(errors[param.name]))
                else:
                    with contextlib.suppress(KeyError):
                        self.text_errors[param.name].SetLabel("")

        # If there are errors, we stop here
        if errors:
            return

        # Save the parameters to the history file
        for param in selected_command.params:
            with contextlib.suppress(KeyError):
                self.config[self.command_name][param.name] = self.entries[
                    param.name
                ].GetValue()
        with open(self.history_file, mode="w", encoding="utf-8") as fp:
            tomlkit.dump(self.config, fp)

        if args and not self.ctx.allow_extra_args and not self.ctx.resilient_parsing:
            event.GetEventObject().Enable()
            raise Exception("unexpected argument")

        # Invoke the command in a separate thread to avoid blocking the GUI
        self.ctx.args = args
        self.thread = Thread(target=selected_command.invoke, args=(self.ctx,), daemon=True)
        self.thread.start()


class Guick(wx.Frame):
    def __init__(self, ctx, size=None):
        wx.Frame.__init__(self, None, -1, ctx.command.name)
        self.ctx = ctx
        self.entry = {}
        # self.button = {}
        self.text_error = {}

        # Create Help menu
        menubar = wx.MenuBar()
        help_menu = wx.Menu()
        help_item = wx.MenuItem(help_menu, -1, '&Help')
        help_menu.Append(help_item)
        self.Bind(wx.EVT_MENU, self.on_help, help_item)

        # If version option defined, add a version menu
        version_option = False
        if any(
            param.name == "version" and param.is_eager
            for param in ctx.command.params
        ):
            # Get version before redirecting stdout
            self.version = self.get_version()

            version_item = wx.MenuItem(help_menu, -1, '&Version')
            help_menu.Append(version_item)
            self.Bind(wx.EVT_MENU, self.OnVersion, version_item)

        menubar.Append(help_menu, '&Help')
        self.SetMenuBar(menubar)

        # Set history file name
        history_folder = Path(platformdirs.user_config_dir("history", "guick")) / ctx.info_name
        history_folder.mkdir(parents=True, exist_ok=True)
        self.history_file = history_folder / "history.toml"

        self.panel = wx.Panel(
            self,
            -1,
            style=wx.DEFAULT_FRAME_STYLE | wx.CLIP_CHILDREN | wx.FULL_REPAINT_ON_RESIZE,
        )
        vbox = wx.BoxSizer(wx.VERTICAL)
        # If it is a group, create a notebook for each command
        if isinstance(ctx.command, click.Group):
            self.notebook = wx.Notebook(self.panel, -1)
            parent = self.notebook
            for name in ctx.command.commands:
                command = ctx.command.commands.get(name)
                panel = CommandPanel(parent, ctx, name, self.history_file)
                self.notebook.AddPage(panel, name, 1, 0)
                self.panel.SetBackgroundColour(wx.Colour((240, 240, 240, 255)))
            font = wx.Font(wx.FontInfo(14).Bold())
            self.notebook.SetFont(font)
            vbox.Add(self.notebook, 0, wx.EXPAND | wx.ALL, 10)
        # Otherwise, create a single panel
        else:
            parent = self.panel
            command = ctx.command
            panel = CommandPanel(parent, ctx, "", self.history_file)
            vbox.Add(panel, 0, wx.EXPAND | wx.ALL, 10)

        # # Create the log
        self.log_panel = LogPanel(self.panel)
        vbox.Add(self.log_panel, 1, flag=wx.EXPAND | wx.ALL, border=10)
        sys.stdout = RedirectText(self.log_panel.log_ctrl)
        self.panel.SetSizerAndFit(vbox)
        self.Fit()
        # Set the minimum size to the fitted size
        self.SetMinClientSize(self.GetClientSize())
        
        # If a larger size is specified, apply it
        if size:
            current_size = self.GetClientSize()
            new_width = max(size[0], current_size.width) if size[0] != -1 else current_size.width
            new_height = max(size[1], current_size.height) if size[1] != -1 else current_size.height
            self.SetClientSize((new_width, new_height))
        

        self.CreateStatusBar()
        self.SetStatusText("")

        self.Centre()

        self.Bind(wx.EVT_CLOSE, self.on_exit)

    def on_exit(self, event):
        # Destroys the main frame which quits the wxPython application
        self.Destroy()
        sys.exit()

    def on_help(self, event):
        head = self.ctx.command.name
        short_help = self.ctx.command.short_help
        help_text = self.ctx.command.help
        help_epilog = self.ctx.command.epilog
        description = ""
        if short_help:
            description += f"{short_help}\n\n"
        if help_text:
            description += f"{help_text}\n\n"
        if help_epilog:
            description += f"{help_epilog}"
        dlg = AboutDialog(self, "Help", head, description)

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
        
        dlg = AboutDialog(self, "About", head, self.version, font="monospace")
        dlg.Show()




class GroupGui(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        if args:
            args = super().parse_args(ctx, args)
            return args
        # if not args and self.no_args_is_help and not ctx.resilient_parsing:
        #     raise Exception(ctx)

        app = wx.App()
        frame = Guick(ctx)
        frame.Show()
        app.MainLoop()


class CommandGui(click.Command):
    def __init__(self, *args, size=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = size

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        # If args defined on the command line, use the CLI
        if args:
            args = super().parse_args(ctx, args)
            return args
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise Exception(ctx)

        app = wx.App()
        frame = Guick(ctx, size=self.size)
        frame.Show()
        app.MainLoop()
