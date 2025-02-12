import contextlib
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
import wx.lib.agw.labelbook as LB
import wx.lib.buttons as buttons
import wx.lib.scrolledpanel as scrolled
from wx.lib.newevent import NewEvent

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
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, style=wx.TE_MULTILINE | wx.TE_RICH2)

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
                self.SetDefaultStyle(current_attr)
                self.AppendText(part)


class AboutDialog(wx.Dialog):
    def __init__(self, parent, head, description):
        super().__init__(parent, title="About")

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Application title
        title = wx.StaticText(self, label=f"  {head}  ")
        title_font = title.GetFont()
        title_font.MakeBold().MakeLarger()
        title.SetFont(title_font)
        main_sizer.Add(title, flag=wx.ALIGN_CENTER | wx.TOP, border=20)

        # Description
        description_st = wx.StaticText(self, label=description)
        font = get_best_monospace_font()
        description_st.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=font))
        main_sizer.Add(description_st, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        # OK button
        ok_button = wx.Button(self, label="OK")
        ok_button.Bind(wx.EVT_BUTTON, self.on_close)
        main_sizer.Add(ok_button, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        # Set sizer and auto-fit dialog size
        self.SetSizer(main_sizer)
        # Resize dialog to fit content
        self.Fit()

    def on_close(self, event):
        self.Destroy()


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
    def __init__(self, parent, sizer, param, row, default_text=None, longest_param_name=""):
        self.param = param
        self.parent = parent
        self.entry = None
        self.text_error = None
        self.default_text = default_text
        self.longest_param_name = longest_param_name
        self.sizer = sizer
        self.row = row
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
        if self.default_text:
            self.entry.SetValue(self.default_text)
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))

    def build_button(self):
        # Invisible button to keep layout straight
        b = buttons.GenButton(self.parent, -1, '      ', style=wx.BORDER_NONE)
        b.Enable(False)
        self.sizer.Add(b, (self.row, 2))

    def build_error(self):
        self.text_error = wx.StaticText(self.parent, -1, "", size=(500, -1))
        font = wx.Font(wx.FontInfo(8))
        self.text_error.SetFont(font)
        self.text_error.SetForegroundColour((255, 0, 0))
        self.sizer.Add(self.text_error, flag=wx.EXPAND, pos=(self.row + 1, 1))


class ChoiceEntry(NormalEntry):
    def build_entry(self):
        self.entry = wx.ComboBox(
            self.parent, -1, size=(500, -1), choices=list(self.param.type.choices)
        )
        if self.default_text:
            self.entry.SetValue(self.default_text)
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))


class BoolEntry(NormalEntry):
    def build_entry(self):
        self.entry = wx.CheckBox(self.parent, -1)
        if self.default_text:
            self.entry.SetValue(bool(self.default_text))
        self.sizer.Add(self.entry, flag=wx.EXPAND, pos=(self.row, 1))


class PathEntry(NormalEntry):
    def __init__(self, parent, sizer, param, row, longest_param_name="", default_text=None, callback=None):
        self.button = None
        self.callback = callback
        super().__init__(parent, sizer, param, row, default_text, longest_param_name)

    def build_button(self):
        self.button = wx.Button(self.parent, -1, "Browse")
        self.button.Bind(
            wx.EVT_BUTTON, self.callback
        )
        self.sizer.Add(self.button, (self.row, 2))


class CsvFile(click.Path):
    name = "csv_file"

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

        # If url defined in epilog, add a help menu
        url_matches = []
        if ctx.command.epilog:
            URL_EXTRACT_PATTERN = "(https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*))"
            url_matches = re.findall(URL_EXTRACT_PATTERN, ctx.command.epilog)
        # If version option defined, add a version menu
        version_option = False
        if any(
            param.name == "version" and param.is_eager
            for param in ctx.command.params
        ):
            version_option = True
        try:
            if url_matches or version_option:
                menubar = wx.MenuBar()
                file_menu = wx.Menu()

                if url_matches:
                    help_item = wx.MenuItem(file_menu, wx.ID_EXIT, '&Help')
                    file_menu.Append(help_item)
                    self.Bind(wx.EVT_MENU, lambda x, y=url_matches[0]: self.on_help(x, y), help_item)

                if version_option:
                    version_item = wx.MenuItem(file_menu, wx.ID_EXIT, '&Version')
                    file_menu.Append(version_item)
                    self.Bind(wx.EVT_MENU, self.OnVersion, version_item)

                menubar.Append(file_menu, '&Help')

                self.SetMenuBar(menubar)
        except Exception as e:
            print(e)

        # Set history file name
        history_folder = Path(platformdirs.user_config_dir("history", "guick")) / ctx.info_name
        history_folder.mkdir(parents=True, exist_ok=True)
        self.history_file = history_folder / "history.toml"

        # If it is a group, create a notebook for each command
        if isinstance(ctx.command, click.Group):
            self.notebook = wx.Notebook(self, -1)
            parent = self.notebook
            for name in ctx.command.commands:
                command = ctx.command.commands.get(name)
                self.build_command_gui(parent, command)
                parent.AddPage(self.panel, name, 1, 0)
        # Otherwise, create a single panel
        else:
            parent = self
            command = ctx.command
            self.build_command_gui(parent, command)

        self.CreateStatusBar()
        self.SetStatusText("Resize this frame to see how the sizers respond...")

        self.SetClientSize(self.panel.GetSize())
        self.Centre()

    def on_help(self, event, url):
        webbrowser.open(url)

    def OnVersion(self, event):
        for param in self.ctx.command.params:
            if param.name == "version":

                with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                    try:
                        param.callback(self.ctx, param, True)
                    except Exception:
                        pass
                    output = buf.getvalue()
        title = output.split("\n")[0]
        description = "\n".join(output.split("\n")[1:])
        dlg = AboutDialog(self, title, description)
        dlg.ShowModal()  # Show dialog modally


    def build_command_gui(self, parent, command):
        # self.panel = scrolled.ScrolledPanel(
        self.panel = wx.Panel(
            parent,
            -1,
            style=wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN | wx.FULL_REPAINT_ON_RESIZE,
        )
        # Create the log
        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        self.log = ANSITextCtrl(
            self.panel,
            wx.ID_ANY,
            size=(300, 100),
            style=style
        )
        self.log.SetBackgroundColour(wx.Colour(0, 0, 0))
        # Set monospace font for log output
        chosen_font = get_best_monospace_font()
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName=chosen_font)
        self.log.SetFont(font)

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
        main_boxsizer = wx.BoxSizer(wx.VERTICAL)

        if required_param:
            sb = wx.StaticBox(self.panel, label="Required Parameters")
            font = wx.Font(wx.FontInfo(10).Bold())

            # set font for the statictext
            sb.SetFont(font)
            self.required_boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
            main_boxsizer.Add(self.required_boxsizer,
                flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
            self.required_gbs = wx.GridBagSizer(vgap=1, hgap=5)
        if optional_param:
            sb = wx.StaticBox(self.panel, label="Optional Parameters")
            sb.SetFont(font)
            self.optional_boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
            main_boxsizer.Add(self.optional_boxsizer,
                flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
            self.optional_gbs = wx.GridBagSizer(vgap=1, hgap=5)
        sb = wx.StaticBox(self.panel, label="Log")
        sb.SetFont(font)
        self.log_st = wx.StaticBoxSizer(sb, wx.VERTICAL)
        self.log_st.Add(self.log, 1, wx.EXPAND | wx.ALL, 10)
        main_boxsizer.Add(self.log_st, 1,
            flag=wx.EXPAND | wx.ALL, border=10)
        sys.stdout = RedirectText(self.log)

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
            if not param.is_eager:
                try:
                    prefilled_value = config[command.name][param.name]
                except KeyError:
                    prefilled_value = str(param.default) if param.default else ""
                real_params += 1
                if isinstance(param.type, CsvFile):
                    self.build_file_entry(
                        param,
                        2 * idx_param,
                        wildcards="csv files|*.csv",
                        default_text=prefilled_value,
                    )
                elif isinstance(param.type, click.Path):
                    if param.type.file_okay:
                        widgets = PathEntry(self.panel, sizer, param, 2 * idx_param, default_text=prefilled_value, callback=self.file_open, longest_param_name=longest_param_name)
                        self.button[param.name] = widgets.button
                    else:
                        widgets = PathEntry(self.panel, sizer, param, 2 * idx_param, default_text=prefilled_value, callback=self.dir_open, longest_param_name=longest_param_name)
                        self.button[param.name] = widgets.button
                # Choice
                elif isinstance(param.type, click.Choice):
                    widgets = ChoiceEntry(self.panel, sizer, param, 2 * idx_param, longest_param_name=longest_param_name, default_text=prefilled_value)
                # bool
                elif isinstance(param.type, click.types.BoolParamType):
                    widgets = BoolEntry(self.panel, sizer, param, 2 * idx_param, longest_param_name=longest_param_name, default_text=prefilled_value)
                else:
                    widgets = NormalEntry(self.panel, sizer, param, 2 * idx_param, longest_param_name=longest_param_name, default_text=prefilled_value)
                self.entry[param.name] = widgets.entry
                self.text_error[param.name] = widgets.text_error
        self.optional_gbs.AddGrowableCol(1)
        self.required_gbs.AddGrowableCol(1)
        # line = wx.StaticLine(p, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        # gbs.Add(line, (i+1, 0), (i+1, 3), wx.EXPAND|wx.RIGHT|wx.TOP, 5)

        if True:

            ok_button = wx.Button(self.panel, -1, label="Ok")
            main_boxsizer.Add(
                ok_button,
                flag=wx.BOTTOM | wx.RIGHT | wx.ALIGN_RIGHT,
                border=10,
            )
            ok_button.Bind(wx.EVT_BUTTON, self.on_ok_button)

            # button5 = wx.Button(parent, label="Cancel")
            # self.gbs.Add(
            #     button5,
            #     pos=(2 * (real_params + 1), 2),
            #     flag=wx.BOTTOM | wx.RIGHT,
            #     border=10,
            # )
        self.optional_boxsizer.Add(self.optional_gbs, 1, wx.EXPAND | wx.ALL, 10)
        self.required_boxsizer.Add(self.required_gbs, 1, wx.EXPAND | wx.ALL, 10)
        self.optional_boxsizer.SetSizeHints(self)
        self.required_boxsizer.SetSizeHints(self)
        main_boxsizer.SetSizeHints(self)

        self.panel.SetSizerAndFit(main_boxsizer)

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

    def file_open(self, event, wildcard="All files|*.*"):
        dlg = wx.FileDialog(
            self,
            message="Choose a file",
            defaultDir=os.getcwd(),
            defaultFile="",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
        )

        # Show the dialog and retrieve the user response. If it is the OK response,
        # process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            path = dlg.GetPath()
            dlg.Destroy()
            param = [
                param_name
                for param_name, entry in self.button.items()
                if entry == event.GetEventObject()
            ][0]
            self.entry[param].SetValue(path)

    def on_ok_button(self, event):
        config = tomlkit.document()
        try:
            with open(self.history_file, mode="rt", encoding="utf-8") as fp:
                config = tomlkit.load(fp)
                print(config)
        except FileNotFoundError:
            pass
        if not config.get(self.ctx.command.name):
            script_history = tomlkit.table()
            config.add(self.ctx.command.name, script_history)
        opts = {
            key: entry.GetValue() if entry.GetValue() != "" else None
            for key, entry in self.entry.items()
        }
        print(opts)
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
            print(param)
            try:
                value, args = param.handle_parse_result(self.ctx, opts, args)
            except Exception as exc:
                errors[exc.param.name] = exc
                print(exc)

        # for param in self.ctx.command.commands.get(selected_command).params:
        # for param in self.ctx.command.params:
        for param in selected_command.params:
            if errors.get(param.name):
                self.text_error[param.name].SetLabel(str(errors[param.name]))
            else:
                with contextlib.suppress(KeyError):
                    self.text_error[param.name].SetLabel("")
        if errors:
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
            raise Exception("unexpected argument")

        self.ctx.args = args
        thread = Thread(target=selected_command.invoke, args=(self.ctx,), daemon=True)
        thread.start()


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
