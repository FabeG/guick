import contextlib
import math
import functools
import inspect
import io
import os
import re
import sys
import time
import typing as t
import webbrowser
from pathlib import Path
from threading import Thread

import click
import platformdirs
import tomlkit
import wx
import wx.html

import wx.lib.agw.labelbook as LB
import wx.lib.buttons as buttons
import wx.lib.scrolledpanel as scrolled
from wx.lib.newevent import NewEvent


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, obj):
        wx.FileDropTarget.__init__(self)
        self.obj = obj

    def OnDropFiles(self, x, y, filenames):
        self.obj.SetValue("")
        self.obj.WriteText(filenames[0])
        return True

# Regex pattern to match ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[(\d+)m')

# Mapping ANSI color codes to HTML colors
ANSI_COLORS = {
    30: wx.Colour(0, 0, 0),       # Black
    31: wx.Colour(255, 0, 0),     # Red
    32: wx.Colour(13, 161, 14),     # Green
    33: wx.Colour(193, 156, 0),   # Yellow
    34: wx.Colour(0, 55, 218),     # Blue
    35: wx.Colour(136, 23, 152),   # Magenta
    36: wx.Colour(58, 150, 221),   # Cyan
    37: wx.Colour(255, 255, 255),  # White
}
ANSI_BACKGROUND_COLOR = {
    41: wx.Colour(255, 0, 0),     # Red
}


class ANSITextCtrl(wx.TextCtrl):
    def __init__(self, parent, style, size, gauge, gauge_text, *args, **kwargs):
        super().__init__(parent, style=wx.TE_MULTILINE | wx.TE_RICH2, size=size)
        self.gauge = gauge
        self.gauge_text = gauge_text
        self.gauge_value = 0

    def append_ansi_text(self, text):
        """Parses ANSI escape sequences and applies color formatting."""
        parts = ANSI_ESCAPE_PATTERN.split(text)
        # Default white text / black background
        current_attr = wx.TextAttr(wx.Colour(255, 255, 255))
        current_attr.SetBackgroundColour(wx.Colour(0, 0, 0))
        for part in parts:
            if part.isdigit():  # ANSI color code
                code = int(part)
                if code in ANSI_COLORS:
                    current_attr.SetTextColour(ANSI_COLORS[code])
                elif code in ANSI_BACKGROUND_COLOR:
                    current_attr.SetBackgroundColour(ANSI_BACKGROUND_COLOR[code])
                    current_attr.SetTextColour(wx.Colour(255, 255, 255))
            else:  # Normal text
                if "\r" in part:
                    # Regex to extract the progress bar value from the tqdm output
                    regex_tqdm = re.match(r"([\d\s]+)%\|.*\|(.*)", part)
                    if regex_tqdm:
                        self.gauge_value = int(regex_tqdm.group(1))
                        self.gauge.SetValue(self.gauge_value)
                        self.gauge_text.SetValue(regex_tqdm.group(2))
                else:
                    self.SetDefaultStyle(current_attr)
                    self.AppendText(part)


class LogPanel(wx.Panel):
    """A panel containing a shared log in a StaticBox."""
    def __init__(self, parent):
        super().__init__(parent)

        sb = wx.StaticBox(self, label="Log")
        font = wx.Font(wx.FontInfo(10).Bold())
        sb.SetFont(font)
        box_sizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        # Create the log
        self.gauge = wx.Gauge(self, -1, 100, size=(-1, 10))
        font = get_best_monospace_font()
        self.gauge_text = wx.TextCtrl(self, -1, "", size=(400, -1), style=wx.TE_READONLY)
        self.gauge_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=font))
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 5)
        hbox.Add(self.gauge_text, 0, wx.EXPAND | wx.ALL, 5)
        self.log_ctrl = ANSITextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, size=(-1, 200), gauge=self.gauge, gauge_text=self.gauge_text)
        self.log_ctrl.SetMinSize((100, 200))
        self.log_ctrl.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=font))

        box_sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        box_sizer.Add(hbox, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(box_sizer)
        box_sizer.SetSizeHints(self)
        self.Layout()

        self.log_ctrl.SetBackgroundColour(wx.Colour(0, 0, 0))


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
            webbrowser.open(url)  # Open in default browser
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
    def __init__(self, **kwargs):
        self.param = kwargs["param"]
        self.parent = kwargs["parent"]
        self.entry = None
        self.text_error = None
        self.default_text = kwargs.get("default_text")
        self.longest_param_name = kwargs.get("longest_param_name", "")
        self.sizer = kwargs["sizer"]
        self.min_size = (100, -1)
        self.row = kwargs["row"]
        self.build_label()
        self.build_entry()
        self.build_button()
        self.build_error()

    def build_label(self):
        static_text = wx.StaticText(self.parent, -1, self.longest_param_name)
        size = static_text.GetSize()
        static_text.SetMinSize(size)
        static_text.SetLabel(self.param.name)
        static_text.SetToolTip(self.param.help)
        self.sizer.Add(static_text, (self.row, 0))

    def build_entry(self):
        # Password
        if self.param.hide_input:
            self.entry = wx.TextCtrl(
                self.parent, -1, size=(500, -1), style=wx.TE_RICH | wx.TE_PASSWORD
            )
        # Normal case
        else:
            self.entry = wx.TextCtrl(self.parent, -1, size=(500, -1), style=wx.TE_RICH)
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(self.default_text)
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))

    def build_button(self):
        # Create fake button to know the size of the spacer
        button = wx.Button(self.parent, -1, "Browse")
        size = button.GetSize()
        button.Destroy()
        self.sizer.Add(size, (self.row, 2))

    def build_error(self):
        self.text_error = wx.StaticText(self.parent, -1, "", size=(500, -1))
        font = wx.Font(wx.FontInfo(8))
        self.text_error.SetMinSize(self.min_size)
        self.text_error.SetFont(font)
        self.text_error.SetForegroundColour((255, 0, 0))
        self.sizer.Add(self.text_error, flag=wx.EXPAND, pos=(self.row + 1, 1))


class ChoiceEntry(NormalEntry):
    def build_entry(self):
        self.entry = wx.ComboBox(
            self.parent, -1, size=(500, -1), choices=list(self.param.type.choices)
        )
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(self.default_text)
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))


class BoolEntry(NormalEntry):
    def build_entry(self):
        self.entry = wx.CheckBox(self.parent, -1)
        self.entry.SetMinSize(self.min_size)
        if self.default_text:
            self.entry.SetValue(bool(self.default_text))
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))


class SliderEntry(NormalEntry):
    def build_entry(self):
        initial_value = int(self.default_text) if self.default_text else self.param.type.min
        self.entry = wx.Slider(
            self.parent, value=initial_value, minValue=self.param.type.min, maxValue=self.param.type.max,
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS
            )
        self.entry.SetMinSize(self.min_size)

        self.entry.SetTickFreq(int(math.pow(10, math.ceil(math.log10(self.param.type.max - self.param.type.min) - 1))))
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))


class PathEntry(NormalEntry):
    def __init__(self, **kwargs):
        self.button = None
        self.callback = kwargs.get("callback")
        super().__init__(**kwargs)
        self.file_drop_target = MyFileDropTarget(self.entry)
        self.entry.SetDropTarget(self.file_drop_target)

    def build_button(self):
        self.button = wx.Button(self.parent, -1, "Browse")
        self.button.Bind(
            wx.EVT_BUTTON, self.callback
        )
        self.sizer.Add(self.button, (self.row, 2))


    def convert(self, value, param, ctx):
        if not value.endswith(".csv"):
            self.fail("File should be a csv file", param, ctx)
        return value


class Guick(wx.Frame):
    def __init__(self, ctx):
        wx.Frame.__init__(self, None, -1, ctx.command.name)
        self.ctx = ctx
        self.entry = {}
        self.button = {}
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
                panel = self.build_command_gui(parent, command)
                self.notebook.AddPage(panel, name, 1, 0)
                self.panel.SetBackgroundColour(wx.Colour((240, 240, 240, 255)))
            font = wx.Font(wx.FontInfo(14).Bold())
            self.notebook.SetFont(font)
            vbox.Add(self.notebook, 0, wx.EXPAND | wx.ALL, 10)
        # Otherwise, create a single panel
        else:
            parent = self.panel
            command = ctx.command
            panel = self.build_command_gui(parent, command)
            vbox.Add(panel, 0, wx.EXPAND | wx.ALL, 10)

        # # Create the log
        self.log_panel = LogPanel(self.panel)
        vbox.Add(self.log_panel, 1, flag=wx.EXPAND | wx.ALL, border=10)
        sys.stdout = RedirectText(self.log_panel.log_ctrl)
        self.panel.SetSizerAndFit(vbox)
        self.Fit()

        self.CreateStatusBar()
        self.SetStatusText("")

        self.Centre()

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
        dlg.ShowModal()  # Show dialog modally

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


    def build_command_gui(self, parent, command):
        # self.panel = scrolled.ScrolledPanel(

        panel = wx.Panel(parent, -1)
        # Load the history file if it exists
        config = tomlkit.document()
        try:
            with open(self.history_file, encoding="utf-8") as fp:
                config = tomlkit.load(fp)
        except FileNotFoundError:
            pass
        if not config.get(command.name):
            script_history = tomlkit.table()
            config.add(command.name, script_history)

        # Check if we have optional / required options
        required_param = []
        optional_param = []
        longest_param_name = ""
        for param in command.params:
            if len(param.name) > len(longest_param_name):
                longest_param_name = param.name
            if param.required:
                required_param.append(param)
            else:
                optional_param.append(param)
        # main_sb = wx.StaticBox(self.panel, label="Main Static box")
        self.Bind(wx.EVT_CLOSE, self.on_close_button)
        main_boxsizer = wx.BoxSizer(wx.VERTICAL)

        if required_param:
            sb = wx.StaticBox(panel, label="Required Parameters")
            font = wx.Font(wx.FontInfo(10).Bold())

            # set font for the statictext
            sb.SetFont(font)
            self.required_boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
            main_boxsizer.Add(self.required_boxsizer,
                flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
            self.required_gbs = wx.GridBagSizer(vgap=1, hgap=5)
        if optional_param:
            font = wx.Font(wx.FontInfo(10).Bold())
            sb = wx.StaticBox(panel, label="Optional Parameters")
            sb.SetFont(font)
            self.optional_boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
            main_boxsizer.Add(self.optional_boxsizer,
                flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
            self.optional_gbs = wx.GridBagSizer(vgap=1, hgap=5)

        real_params = 0
        idx_required_param = -1
        idx_optional_param = -1
        for param in command.params:
            if param.required:
                sizer = self.required_gbs
                idx_required_param += 1
                idx_param = idx_required_param
            else:
                sizer = self.optional_gbs
                idx_optional_param += 1
                idx_param = idx_optional_param
            if not param.is_eager and not param.hidden:
                try:
                    prefilled_value = config[command.name][param.name]
                except KeyError:
                    prefilled_value = str(param.default) if param.default else ""
                real_params += 1
                if isinstance(param.type, click.Path):
                    if param.type.file_okay:
                        # If help text is something like:
                        # Excel file (.xlsx, .csv)
                        # Text file (.txt or .log)
                        # Extract the file type and the extensions, so that the file
                        # dialog can filter the files
                        wildcards = "All files|*.*"
                        if param.help:
                            wildcard_raw = re.search(r"(\w+) file[s]? \(([a-zA-Z ,\.]*)\)", param.help)
                            if wildcard_raw:
                                file_type, extensions_raw = wildcard_raw.groups()
                                extensions = re.findall(r"\.(\w+(?:\.\w+)?)", extensions_raw)
                                extensions_text = ";".join([f"*.{ext}" for ext in extensions])
                                wildcards = f"{file_type} files|{extensions_text}"
                        if param.type.readable:
                            mode = "read"
                        elif param.type.writable:
                            mode = "write"
                        widgets = PathEntry(
                            parent=panel,
                            sizer=sizer,
                            param=param,
                            row=2 * idx_param,
                            default_text=prefilled_value,
                            callback=lambda evt, wildcards=wildcards, mode=mode: self.file_open(evt, wildcards, mode),
                            longest_param_name=longest_param_name,
                        )
                        self.button[param.name] = widgets.button
                    else:
                        widgets = PathEntry(
                            parent=panel,
                            sizer=sizer,
                            param=param,
                            row=2 * idx_param,
                            default_text=prefilled_value,
                            callback=self.dir_open,
                            longest_param_name=longest_param_name
                        )
                        self.button[param.name] = widgets.button
                elif isinstance(param.type, click.File):
                    # If help text is something like:
                    # Excel file (.xlsx, .csv)
                    # Text file (.txt or .log)
                    # Extract the file type and the extensions, so that the file
                    # dialog can filter the files
                    wildcards = "All files|*.*"
                    if param.help:
                        wildcard_raw = re.search(r"(\w+) file[s]? \(([a-zA-Z ,\.]*)\)", param.help)
                        if wildcard_raw:
                            file_type, extensions_raw = wildcard_raw.groups()
                            extensions = re.findall(r"\.(\w+(?:\.\w+)?)", extensions_raw)
                            extensions_text = ";".join([f"*.{ext}" for ext in extensions])
                            wildcards = f"{file_type} files|{extensions_text}"
                    if "r" in param.type.mode:
                        mode = "read"
                    elif "w" in param.type.mode:
                        mode = "write"
                    widgets = PathEntry(
                        parent=panel,
                        sizer=sizer,
                        param=param,
                        row=2 * idx_param,
                        default_text=prefilled_value,
                        callback=lambda evt, wildcards=wildcards, mode=mode: self.file_open(evt, wildcards, mode),
                        longest_param_name=longest_param_name,
                    )
                    self.button[param.name] = widgets.button
                # Choice
                elif isinstance(param.type, click.Choice):
                    widgets = ChoiceEntry(
                        parent=panel,
                        sizer=sizer,
                        param=param,
                        row=2 * idx_param,
                        longest_param_name=longest_param_name,
                        default_text=prefilled_value
                    )
                # bool
                elif isinstance(param.type, click.types.BoolParamType):
                    widgets = BoolEntry(
                        parent=panel,
                        sizer=sizer,
                        param=param,
                        row=2 * idx_param,
                        longest_param_name=longest_param_name,
                        default_text=prefilled_value
                    )
                elif isinstance(param.type, click.types.IntRange):
                    widgets = SliderEntry(
                        parent=panel,
                        sizer=sizer,
                        param=param,
                        row=2 * idx_param,
                        longest_param_name=longest_param_name,
                        default_text=prefilled_value,
                        min_value=param.type.min,
                        max_value=param.type.max
                    )
                else:
                    widgets = NormalEntry(
                        parent=panel,
                        sizer=sizer,
                        param=param,
                        row=2 * idx_param,
                        longest_param_name=longest_param_name,
                        default_text=prefilled_value
                    )
                self.entry[param.name] = widgets.entry
                self.text_error[param.name] = widgets.text_error
        # line = wx.StaticLine(p, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        # gbs.Add(line, (i+1, 0), (i+1, 3), wx.EXPAND|wx.RIGHT|wx.TOP, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel, -1, label="Ok")
        hbox.Add(
            ok_button,
            flag=wx.BOTTOM | wx.RIGHT,
            border=10,
        )
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok_button)

        cancel_button = wx.Button(panel, label="Cancel")
        hbox.Add(
            cancel_button,
            flag=wx.BOTTOM | wx.LEFT,
            border=10,
        )
        cancel_button.Bind(wx.EVT_BUTTON, self.on_close_button)
        main_boxsizer.Add(hbox, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.ALL, border=10)
        if optional_param:
            self.optional_gbs.AddGrowableCol(1)
            self.optional_boxsizer.Add(self.optional_gbs, 1, wx.EXPAND | wx.ALL, 10)
            self.optional_boxsizer.SetSizeHints(panel)
        if required_param:
            self.required_gbs.AddGrowableCol(1)
            self.required_boxsizer.Add(self.required_gbs, 1, wx.EXPAND | wx.ALL, 10)
            self.required_boxsizer.SetSizeHints(panel)

        panel.SetSizerAndFit(main_boxsizer)
        return panel

    def dir_open(self, event):
        dlg = wx.DirDialog(
            self, message="Choose Directory",
            defaultPath=os.getcwd(),
            style=wx.RESIZE_BORDER
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            param = [
                param_name
                for param_name, entry in self.button.items()
                if entry == event.GetEventObject()
            ][0]
            self.entry[param].SetValue(path)

    def file_open(self, event, wildcards="All files|*.*", mode="read"):
        param = [
            param_name
            for param_name, entry in self.button.items()
            if entry == event.GetEventObject()
        ][0]
        path = self.entry[param].GetValue()
        last_folder = Path(path).parent if path != "" else os.getcwd()
        if mode == "read":
            style = wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST
        else:
            style = wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT
        dlg = wx.FileDialog(
            self,
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

    def on_close_button(self, event):
        sys.exit()

    def on_ok_button(self, event):
        # Disable the button
        # event.GetEventObject().Disable()
        config = tomlkit.document()
        try:
            with open(self.history_file, mode="rt", encoding="utf-8") as fp:
                config = tomlkit.load(fp)
        except FileNotFoundError:
            pass
        if not config.get(self.ctx.command.name):
            script_history = tomlkit.table()
            config.add(self.ctx.command.name, script_history)
        opts = {
            key: entry.GetValue() if entry.GetValue() != "" else None
            for key, entry in self.entry.items()
        }
        args = []
        errors = {}
        try:
            idx = self.notebook.GetSelection()
            selected_command_name = list(self.ctx.command.commands)[idx]
            selected_command = self.ctx.command.commands.get(selected_command_name)
        except AttributeError:
            selected_command = self.ctx.command
        # for param in self.ctx.command.params:
        for param in selected_command.params:
            try:
                value, args = param.handle_parse_result(self.ctx, opts, args)
            except Exception as exc:
                errors[exc.param.name] = exc

        # for param in self.ctx.command.commands.get(selected_command).params:
        # for param in self.ctx.command.params:
        for param in selected_command.params:
            if not param.hidden:
                if errors.get(param.name):
                    self.text_error[param.name].SetLabel(str(errors[param.name]))
                    self.text_error[param.name].SetToolTip(str(errors[param.name]))
                else:
                    with contextlib.suppress(KeyError):
                        self.text_error[param.name].SetLabel("")
        if errors:
            event.GetEventObject().Enable()
            return
        # for param in self.ctx.command.params:
        for param in selected_command.params:
            with contextlib.suppress(KeyError):
                config[self.ctx.command.name][param.name] = self.entry[
                    param.name
                ].GetValue()
        with open(self.history_file, mode="wt", encoding="utf-8") as fp:
            tomlkit.dump(config, fp)

        if args and not self.ctx.allow_extra_args and not self.ctx.resilient_parsing:
            event.GetEventObject().Enable()
            raise Exception("unexpected argument")

        self.ctx.args = args
        thread = Thread(target=selected_command.invoke, args=(self.ctx,), daemon=True)
        thread.start()
        # event.GetEventObject().Enable()
        # self.Destroy()


class GroupGui(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        # print(args)
        # if not args and self.no_args_is_help and not ctx.resilient_parsing:
        #     raise Exception(ctx)

        app = wx.App()
        frame = Guick(ctx)
        frame.Show()
        app.MainLoop()


class CommandGui(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        # If args defined on the command line, use the CLI
        if args:
            args = super().parse_args(ctx, args)
            return args
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise Exception(ctx)

        app = wx.App()
        frame = Guick(ctx)
        frame.Show()
        app.MainLoop()
