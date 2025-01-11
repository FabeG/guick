import functools

# import wx
import inspect
import os
import typing as t

import click
import tomlkit
import wx


class CsvFile(click.Path):
    name = "csv_file"

    def convert(self, value, param, ctx):
        if not value.endswith(".csv"):
            self.fail("File should be a csv file", param, ctx)
        return value


class Guick(wx.Frame):
    def __init__(self, ctx):
        infos = ctx.to_info_dict()
        self.ctx = ctx
        self.entry = {}
        self.button = {}
        wx.Frame.__init__(self, None, -1, ctx.command.name)
        self.panel = wx.Panel(
            self,
            -1,
            style=wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN | wx.FULL_REPAINT_ON_RESIZE,
        )
        box1 = wx.StaticBox(self.panel, -1, "This is a wx.StaticBox")

        # This gets the recommended amount of border space to use for items
        # within in the static box for the current platform.
        topBorder, otherBorder = box1.GetBordersForSizer()
        bsizer1 = wx.BoxSizer(wx.VERTICAL)
        bsizer1.AddSpacer(topBorder)

        t1 = wx.StaticBoxSizer(box1, wx.HORIZONTAL)
        bsizer1.Add(t1, 1, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, otherBorder + 10)
        self.gbs = wx.GridBagSizer(5, 5)
        self.text_error = {}

        config = tomlkit.document()
        try:
            with open("history.toml", mode="rt", encoding="utf-8") as fp:
                config = tomlkit.load(fp)
        except FileNotFoundError:
            pass
        if not config.get(ctx.command.name):
            script_history = tomlkit.table()
            config.add(ctx.command.name, script_history)

        real_params = 0
        for i, param in enumerate(ctx.command.params):
            if not param.is_eager:
                try:
                    defaults_text = config[ctx.command.name][param.name]
                except KeyError:
                    defaults_text = None
                real_params += 1
                if isinstance(param.type, CsvFile):
                    self.build_file_entry(
                        param,
                        2 * i,
                        wildcards="csv files|*.csv",
                        default_text=defaults_text,
                    )
                elif isinstance(param.type, click.Path):
                    self.build_file_entry(param, 2 * i, default_text=defaults_text)
                # Choice
                elif isinstance(param.type, click.Choice):
                    self.build_choice_entry(param, 2 * i)
                # bool
                elif isinstance(param.type, click.types.BoolParamType):
                    self.build_bool_entry(param, 2 * i)
                else:
                    self.build_normal_entry(param, 2 * i)
            # File or folder
        self.gbs.AddGrowableCol(1)
        # line = wx.StaticLine(p, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        # gbs.Add(line, (i+1, 0), (i+1, 3), wx.EXPAND|wx.RIGHT|wx.TOP, 5)

        button3 = wx.Button(self.panel, label="Help")
        self.gbs.Add(button3, pos=(2 * (real_params + 1), 0), flag=wx.LEFT, border=10)

        ok_button = wx.Button(self.panel, label="Ok")
        self.gbs.Add(
            ok_button,
            pos=(2 * (real_params + 1), 1),
            flag=wx.BOTTOM | wx.RIGHT | wx.ALIGN_RIGHT,
            border=10,
        )
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok_button)

        button5 = wx.Button(self.panel, label="Cancel")
        self.gbs.Add(
            button5,
            pos=(2 * (real_params + 1), 2),
            flag=wx.BOTTOM | wx.RIGHT,
            border=10,
        )
        wrapper = wx.BoxSizer()
        wrapper.Add(self.gbs, 1, wx.EXPAND | wx.ALL, 10)

        self.CreateStatusBar()
        self.SetStatusText("Resize this frame to see how the sizers respond...")

        self.panel.SetSizerAndFit(wrapper)
        self.SetClientSize(self.panel.GetSize())
        self.Centre()

    def build_file_entry(
        self, param, row, wildcards="All files|*.*", default_text=None
    ):
        static_text = wx.StaticText(self.panel, -1, param.name)
        static_text.SetToolTip(param.help)
        self.gbs.Add(static_text, (row, 0))
        self.entry[param.name] = wx.TextCtrl(
            self.panel, -1, size=(500, -1), style=wx.TE_RICH
        )
        if default_text:
            self.entry[param.name].SetValue(default_text)
        self.gbs.Add(self.entry[param.name], flag=wx.EXPAND, pos=(row, 1))
        self.button[param.name] = wx.Button(self.panel, -1, "Browse")
        self.button[param.name].Bind(
            wx.EVT_BUTTON, lambda x, y=wildcards: self.file_open(x, y)
        )
        self.gbs.Add(self.button[param.name], (row, 2))
        self.text_error[param.name] = wx.StaticText(self.panel, -1, "", size=(500, -1))
        self.text_error[param.name].SetForegroundColour(
            (255, 0, 0)
        )  # set text back color
        self.gbs.Add(self.text_error[param.name], flag=wx.EXPAND, pos=(row + 1, 1))

    def build_choice_entry(self, param, row):
        static_text = wx.StaticText(self.panel, -1, param.name)
        static_text.SetToolTip(param.help)
        self.gbs.Add(static_text, (row, 0))
        self.entry[param.name] = wx.ComboBox(
            self.panel, -1, size=(500, -1), choices=list(param.type.choices)
        )
        self.gbs.Add(self.entry[param.name], (row, 1))
        self.text_error[param.name] = wx.StaticText(self.panel, -1, "", size=(500, -1))
        self.text_error[param.name].SetForegroundColour(
            (255, 0, 0)
        )  # set text back color
        self.gbs.Add(self.text_error[param.name], flag=wx.EXPAND, pos=(row + 1, 1))

    def build_bool_entry(self, param, row):
        static_text = wx.StaticText(self.panel, -1, param.name)
        static_text.SetToolTip(param.help)
        self.gbs.Add(static_text, (row, 0))
        self.entry[param.name] = wx.CheckBox(self.panel, -1)
        self.gbs.Add(self.entry[param.name], (row, 1))
        self.text_error[param.name] = wx.StaticText(self.panel, -1, "", size=(500, -1))
        self.text_error[param.name].SetForegroundColour(
            (255, 0, 0)
        )  # set text back color
        self.gbs.Add(self.text_error[param.name], flag=wx.EXPAND, pos=(row + 1, 1))

    def build_normal_entry(self, param, row):
        static_text = wx.StaticText(self.panel, -1, param.name)
        static_text.SetToolTip(param.help)
        self.gbs.Add(static_text, (row, 0))
        # Password
        if param.hide_input:
            entry = wx.TextCtrl(
                self.panel, -1, size=(500, -1), style=wx.TE_RICH | wx.TE_PASSWORD
            )
        # Normal case
        else:
            entry = wx.TextCtrl(self.panel, -1, size=(500, -1), style=wx.TE_RICH)
        self.entry[param.name] = entry
        self.gbs.Add(entry, flag=wx.EXPAND, pos=(row, 1))
        self.text_error[param.name] = wx.StaticText(self.panel, -1, "", size=(500, -1))
        self.text_error[param.name].SetForegroundColour((255, 0, 0))
        self.gbs.Add(self.text_error[param.name], flag=wx.EXPAND, pos=(row + 1, 1))

    def file_open(self, event, wildcard):
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
            param = [
                param_name
                for param_name, entry in self.button.items()
                if entry == event.GetEventObject()
            ][0]
            self.entry[param].SetValue(path)

    def on_ok_button(self, event):
        config = tomlkit.document()
        try:
            with open("history.toml", mode="rt", encoding="utf-8") as fp:
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
        for param in self.ctx.command.params:
            print(param)
            try:
                value, args = param.handle_parse_result(self.ctx, opts, args)
            except Exception as exc:
                errors[exc.param.name] = exc

        for param in self.ctx.command.params:
            if errors.get(param.name):
                self.text_error[param.name].SetLabel(str(errors[param.name]))
            else:
                try:
                    self.text_error[param.name].SetLabel("")
                except KeyError:
                    pass
        if errors:
            return
        for param in self.ctx.command.params:
            try:
                config[self.ctx.command.name][param.name] = self.entry[
                    param.name
                ].GetValue()
            except KeyError:
                pass
        with open("history.toml", mode="wt", encoding="utf-8") as fp:
            tomlkit.dump(config, fp)

        if args and not self.ctx.allow_extra_args and not self.ctx.resilient_parsing:
            raise Exception("unexpected argument")

        self.ctx.args = args
        self.ctx.command.invoke(self.ctx)


class GroupGui(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise Exception(ctx)

        app = wx.App()
        frame = Guick(ctx)
        frame.Show()
        app.MainLoop()


class CommandGui(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(self.callback)

    def parse_args(self, ctx, args: list[str]) -> list[str]:
        if args:
            args = super().parse_args(ctx, args)
            return args
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise Exception(ctx)

        app = wx.App()
        frame = Guick(ctx)
        frame.Show()
        app.MainLoop()
