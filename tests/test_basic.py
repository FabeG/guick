import enum
import wx
import itertools
import os
import sys
from click.testing import CliRunner

import click
import pytest
from loguru import logger

import guick
import time


def test_deprecated_string_option(tmp_path, mocker):
    @click.command(cls=guick.CommandGui)
    @click.option("--s", default="no value", deprecated=True)
    def cli(s):
        logger.info(f"S:[{s}]")
        # print("no valuex" in sys.stdout.GetValue())
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")
    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["s"].SetValue("test")
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert "S:[test]" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        # TODO: distinguish no value -> default_value, value UNSET, and empty string
        # ("", "S:[no value]"),
        ("42", "S:[42]"),
        ("\N{SNOWMAN}", "S:[\N{SNOWMAN}]"),
    ],
)
def test_string_option(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--s", default="no value")
    def cli(s):
        logger.info(f"S:[{s}]")
        # print("no valuex" in sys.stdout.GetValue())
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")
    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["s"].SetValue(args)
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        # ("", "I:[84]"),
        ("23", "I:[46]"),
        ("x", "'x' is not a valid integer."),
    ],
)
def test_int_option(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--i", default=42)
    def cli(i):
        logger.info(f"I:[{i * 2}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["i"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["i"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        # ("", "U:[ba122011-349f-423b-873b-9d6a79c688ab]"),
        (
            "821592c1-c50e-4971-9cd6-e89dc6832f86",
            "U:[821592c1-c50e-4971-9cd6-e89dc6832f86]",
        ),
        ("x", "'x' is not a valid UUID."),
    ],
)
def test_uuid_option(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option(
        "--u", default="ba122011-349f-423b-873b-9d6a79c688ab", type=click.UUID
    )
    def cli(u):
        logger.info(f"U:[{u}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["u"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["u"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        # ("", "F:[42.0]"),
        ("23.5", "F:[23.5]"),
        ("x", "'x' is not a valid float."),
    ],
)
def test_float_option(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--f", default=42.0)
    def cli(f):
        logger.info(f"F:[{f}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["f"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["f"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect", "default"), [(True, "True", True), (False, "False", True)]
)
def test_boolean_switch(tmp_path, mocker, args, expect, default):
    @click.command(cls=guick.CommandGui)
    @click.option("--on/--off", default=default)
    def cli(on):
        logger.info(on)

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["on"].SetValue(args)
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")

@pytest.mark.parametrize("default", [True, False])
@pytest.mark.parametrize(("args", "expect"), [(True, "True"), (False, "False")])
def test_boolean_flag(tmp_path, mocker, default, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--f", is_flag=True, default=default)
    def cli(f):
        logger.info(f)

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["f"].SetValue(args)
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("value", "expect"),
        [
            (True, "True"),
            (False, "False")
        ]
)
def test_boolean_conversion(tmp_path, mocker, value, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--flag", type=bool)
    def cli(flag):
        logger.info(flag)

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["flag"].SetValue(value)
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_file_option(tmp_path, mocker):
    @click.command(cls=guick.CommandGui)
    @click.option("--file", type=click.File("w"))
    def cli_input(file):
        file.write("Hello World!\n")

    @click.command(cls=guick.CommandGui)
    @click.option("--file", type=click.File("r"))
    def cli_output(file):
        logger.info(file.read())

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels[list(guick.cmd_panels.keys())[0]].entries["file"].SetValue(str(tmp_path / "example.txt"))
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli_input()
    with pytest.raises(SystemExit):
        cli_output()
    assert "Hello World" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_path_option(tmp_path, mocker):
    @click.command(cls=guick.CommandGui)
    @click.option("-O", type=click.Path(file_okay=False, exists=True, writable=True))
    def write_to_dir(o):
        with open(tmp_path / o / "foo.txt", "wb") as f:
            f.write(b"meh\n")

    os.mkdir(tmp_path / "test")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        logger.info(list(guick.cmd_panels.keys()))
        guick.cmd_panels["write-to-dir"].entries["o"].SetValue(str(tmp_path / "test"))
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        write_to_dir()
    assert "meh" in (tmp_path / "test" / "foo.txt").read_text(encoding="utf-8")

    def init_gui_second(ctx, size=None):
        guick = original_init(ctx)
        logger.info(list(guick.cmd_panels.keys()))
        guick.cmd_panels["write-to-dir"].entries["o"].SetValue(str(tmp_path / "test" / "foo.txt"))
        guick.on_ok_button(None)
        error = guick.cmd_panels["write-to-dir"].text_errors["o"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui_second)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        write_to_dir()
    assert "is a file" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_path_option_2(tmp_path, mocker):
    @click.command(cls=guick.CommandGui)
    @click.option("-f", type=click.Path(exists=True))
    def showtype(f):
        logger.info(f"is_file={os.path.isfile(f)}")
        logger.info(f"is_dir={os.path.isdir(f)}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["showtype"].entries["f"].SetValue("xxx")
        guick.on_ok_button(None)
        error = guick.cmd_panels["showtype"].text_errors["f"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    with pytest.raises(SystemExit):
        showtype()
    assert "does not exist" in (tmp_path / "logfile.log").read_text(encoding="utf-8")

    def init_gui_new(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["showtype"].entries["f"].SetValue(".")
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui_new)

    with pytest.raises(SystemExit):
        showtype()
    assert "is_file=False" in (tmp_path / "logfile.log").read_text(encoding="utf-8")
    assert "is_dir=True" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("xxx", "exists=False"),
        (".", "exists=True"),
    ],
)
def test_path_option_3(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("-f", type=click.Path())
    def exists(f):
        logger.info(f"exists={os.path.exists(f)}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui_new(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["exists"].entries["f"].SetValue(args)
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui_new)

    with pytest.raises(SystemExit):
        exists()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("foo", "S:[foo]"),
        ("meh", "'meh' is not one of 'foo', 'bar', 'baz'."),
    ],
)
def test_choice_option(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--method", type=click.Choice(["foo", "bar", "baz"]))
    def cli(method):
        logger.info(f"S:[{method}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["method"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("foo", "S:[foo]"),
        ("meh", "'meh' is not one of 'foo', 'bar', 'baz'."),
    ],
)
def test_choice_argument(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.argument("method", type=click.Choice(["foo", "bar", "baz"]))
    def cli(method):
        logger.info(f"S:[{method}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["method"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("foo", "S:[foo-value]"),
        ("meh", "'meh' is not one of 'foo', 'bar', 'baz'."),
    ],
)
@pytest.mark.skipif(click.__version__ <= "8.1.8", reason="requires click 8.1.8 or higher")
def test_choice_argument_enum(tmp_path, mocker, args, expect):
    class MyEnum(str, enum.Enum):
        FOO = "foo-value"
        BAR = "bar-value"
        BAZ = "baz-value"

    @click.command(cls=guick.CommandGui)
    @click.argument("method", type=click.Choice(MyEnum, case_sensitive=False))
    def cli(method: MyEnum):
        assert isinstance(method, MyEnum)
        # in the original click test, there is a call to click.echo without .value
        # TODO check why click.echo and logger.info are not the same
        logger.info(f"S:[{method.value}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["method"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("foo", "S:[foo]"),
        ("meh", "'meh' is not one of 'foo', 'bar', 'baz'."),
    ],
)
@pytest.mark.skipif(click.__version__ <= "8.1.8", reason="requires click 8.1.8 or higher")
def test_choice_argument_custom_type(tmp_path, mocker, args, expect):
    class MyClass:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:
            return self.value

    @click.command(cls=guick.CommandGui)
    @click.argument("method", type=click.Choice([MyClass("foo"), MyClass("bar"), MyClass("baz")]))
    def cli(method: MyClass):
        assert isinstance(method, MyClass)
        # in the original click test, there is a call to click.echo without .value
        # TODO check why click.echo and logger.info are not the same
        logger.info(f"S:[{method}]")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["method"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("2015-09-29", "2015-09-29T00:00:00"),
        ("2015-09-29T09:11:22", "2015-09-29T09:11:22"),
        ("2015-09", "'2015-09' does not match the formats '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'."),
    ],
)
def test_datetime_option_default(tmp_path, mocker, args, expect):
    @click.command(cls=guick.CommandGui)
    @click.option("--start_date", type=click.DateTime())
    def cli(start_date):
        logger.info(start_date.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )
    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        guick.on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["start_date"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "date_format", "expect_entry", "expected_date"),
    [
        ((23, 50, 52), "%H-%M-%S", "23-50-52", "23:50:52"),
        # ("2015-09-29T09:11:22", "2015-09-29T09:11:22"),
        # ("2015-09", "'2015-09' does not match the formats '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'."),
    ],
)
def test_datetime_option_with_timepicker(tmp_path, mocker, args, date_format, expect_entry, expected_date):

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    dt = wx.DateTime.FromHMS(*args)

    RealCalendarCtrl = wx.adv.TimePickerCtrl
    def calendar_factory(parent, *args, **kwargs):
        ctrl = RealCalendarCtrl(parent, *args, **kwargs)
        ctrl.Hide()
        ctrl.GetValue = mocker.Mock(return_value=dt)
        ctrl.SetValue = mocker.Mock()
        return ctrl

    mocker.patch(
        "guick.gui.wx.adv.TimePickerCtrl",
        side_effect=calendar_factory
    )

    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    @click.command(cls=guick.CommandGui)
    @click.option("--start_hour", type=click.DateTime(formats=[date_format]))
    def set_date(start_hour):
        logger.info(start_hour.strftime("%H:%M:%S"))
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        # guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        param = [param for param in guick.cmd_panels["set-date"].ctx.command.params if param.name == "start_hour"][0]
        guick.cmd_panels["set-date"].sections["Optional Parameters"].date_time_picker(None, param)
        dlg = wx.FindWindowByName("DatePicker")
        ok_btn = dlg.FindWindowById(wx.ID_OK)
        ok_btn.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId))
        guick.on_ok_button(None)
        assert guick.cmd_panels["set-date"].entries["start_hour"].GetValue() == expect_entry
        error = guick.cmd_panels["set-date"].text_errors["start_hour"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        set_date()
    assert expected_date in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "date_format", "expect_entry", "expected_date"),
    [
        ((28, 9, 2015), "%Y %m %d", "2015 09 28", "2015-09-28T00:00:00"),
        ((28, 9, 2015), "%A %B %d, %Y", "Monday September 28, 2O15", "2015-09-28T00:00:00"),
    ],
)
def test_datetime_option_with_datepicker(tmp_path, mocker, args, date_format, expect_entry, expected_date):

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    dt = wx.DateTime.FromDMY(args[0], args[1] - 1, args[2])

    RealCalendarCtrl = wx.adv.CalendarCtrl
    def calendar_factory(parent, *args, **kwargs):
        ctrl = RealCalendarCtrl(parent, *args, **kwargs)
        ctrl.Hide()
        ctrl.GetDate = mocker.Mock(return_value=dt)
        ctrl.SetDate = mocker.Mock()
        return ctrl

    mocker.patch(
        "guick.gui.wx.adv.CalendarCtrl",
        side_effect=calendar_factory
    )

    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    @click.command(cls=guick.CommandGui)
    @click.option("--start_date", type=click.DateTime(formats=[date_format]))
    def set_date(start_date):
        logger.info(start_date.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        # guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        param = [param for param in guick.cmd_panels["set-date"].ctx.command.params if param.name == "start_date"][0]
        guick.cmd_panels["set-date"].sections["Optional Parameters"].date_time_picker(None, param)
        dlg = wx.FindWindowByName("DatePicker")
        ok_btn = dlg.FindWindowById(wx.ID_OK)
        ok_btn.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId))
        guick.on_ok_button(None)
        assert guick.cmd_panels["set-date"].entries["start_date"].GetValue() == expect_entry
        error = guick.cmd_panels["set-date"].text_errors["start_date"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        set_date()
    assert expected_date in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "date_format", "expect_entry", "expected_date"),
    [
        ((23, 50, 52, 23, 8, 1987), "%y/%m/%d %H:%M:%S", "87/08/23 23:50:52", "1987-08-23T23:50:52"),
        # ("2015-09-29T09:11:22", "2015-09-29T09:11:22"),
        # ("2015-09", "'2015-09' does not match the formats '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'."),
    ],
)
def test_datetime_option_with_datetimepicker(tmp_path, mocker, args, date_format, expect_entry, expected_date):

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    dt = wx.DateTime.FromHMS(*args[:3])

    RealTimePickerCtrl = wx.adv.TimePickerCtrl
    def timepicker_factory(parent, *args, **kwargs):
        ctrl = RealTimePickerCtrl(parent, *args, **kwargs)
        ctrl.Hide()
        ctrl.GetValue = mocker.Mock(return_value=dt)
        ctrl.SetValue = mocker.Mock()
        return ctrl

    mocker.patch(
        "guick.gui.wx.adv.TimePickerCtrl",
        side_effect=timepicker_factory
    )

    dt2 = wx.DateTime.FromDMY(args[3], args[4] - 1, args[5])

    RealCalendarCtrl = wx.adv.CalendarCtrl
    def calendar_factory(parent, *args, **kwargs):
        ctrl = RealCalendarCtrl(parent, *args, **kwargs)
        ctrl.Hide()
        ctrl.GetDate = mocker.Mock(return_value=dt2)
        ctrl.SetDate = mocker.Mock()
        return ctrl

    mocker.patch(
        "guick.gui.wx.adv.CalendarCtrl",
        side_effect=calendar_factory
    )

    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    @click.command(cls=guick.CommandGui)
    @click.option("--start_datetime", type=click.DateTime(formats=[date_format]))
    def set_date(start_datetime):
        logger.info(start_datetime.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        # guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        param = [param for param in guick.cmd_panels["set-date"].ctx.command.params if param.name == "start_datetime"][0]
        guick.cmd_panels["set-date"].sections["Optional Parameters"].date_time_picker(None, param)
        dlg = wx.FindWindowByName("DatePicker")
        ok_btn = dlg.FindWindowById(wx.ID_OK)
        ok_btn.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId))
        guick.on_ok_button(None)
        assert guick.cmd_panels["set-date"].entries["start_datetime"].GetValue() == expect_entry
        error = guick.cmd_panels["set-date"].text_errors["start_datetime"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        set_date()
    assert expected_date in (tmp_path / "logfile.log").read_text(encoding="utf-8")



def test_datetime_option_filename_to_read(tmp_path, mocker):

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    tmp_file = tmp_path / "tempfile.txt"
    tmp_file.write_text("Temporary file content", encoding="utf-8")

    mock_dialog = mocker.Mock()
    mock_dialog.GetPath.return_value = str(tmp_file)
    mock_dialog.ShowModal.return_value = wx.ID_OK  # if needed

    mocker.patch(
        "guick.gui.wx.FileDialog",
        return_value=mock_dialog
    )


    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    @click.command(cls=guick.CommandGui)
    @click.option("--filename", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=str), help="Excel files (.csv, .xlsx)")
    def set_file(filename):
        logger.info(filename)
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        # guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        param = [param for param in guick.cmd_panels["set-file"].ctx.command.params if param.name == "filename"][0]
        guick.cmd_panels["set-file"].sections["Optional Parameters"].file_open(None, param)
        guick.on_ok_button(None)
        assert guick.cmd_panels["set-file"].entries["filename"].GetValue() == str(tmp_file)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        set_file()
    assert str(tmp_file) in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_datetime_option_filename_to_write(tmp_path, mocker):

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    tmp_file = tmp_path / "tempfile.txt"
    tmp_file.write_text("Temporary file content", encoding="utf-8")

    mock_dialog = mocker.Mock()
    mock_dialog.GetPath.return_value = str(tmp_file)
    mock_dialog.ShowModal.return_value = wx.ID_OK  # if needed

    mocker.patch(
        "guick.gui.wx.FileDialog",
        return_value=mock_dialog
    )


    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    @click.command(cls=guick.CommandGui)
    @click.option("--filename", type=click.Path(exists=False, file_okay=True, dir_okay=False, readable=False, writable=True, path_type=str), help="Text files (.log, .text)")
    def set_file(filename):
        logger.info(filename)
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        # guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        param = [param for param in guick.cmd_panels["set-file"].ctx.command.params if param.name == "filename"][0]
        guick.cmd_panels["set-file"].sections["Optional Parameters"].file_open(None, param)
        guick.on_ok_button(None)
        assert guick.cmd_panels["set-file"].entries["filename"].GetValue() == str(tmp_file)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        set_file()
    assert str(tmp_file) in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_datetime_option_dirname(tmp_path, mocker):

    mocker.patch("wx.App")
    mocker.patch("wx.App.MainLoop")

    mock_dialog = mocker.Mock()
    mock_dialog.GetPath.return_value = str(tmp_path)
    mock_dialog.ShowModal.return_value = wx.ID_OK  # if needed

    mocker.patch(
        "guick.gui.wx.DirDialog",
        return_value=mock_dialog
    )


    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    @click.command(cls=guick.CommandGui)
    @click.option("--folder", type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=False, writable=True, path_type=str))
    def set_folder(folder):
        logger.info(folder)
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        # guick.cmd_panels["cli"].entries["start_date"].SetValue(args)
        param = [param for param in guick.cmd_panels["set-folder"].ctx.command.params if param.name == "folder"][0]
        guick.cmd_panels["set-folder"].sections["Optional Parameters"].dir_open(None, param)
        guick.on_ok_button(None)
        assert guick.cmd_panels["set-folder"].entries["folder"].GetValue() == str(tmp_path)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        set_folder()
    assert str(tmp_path) in (tmp_path / "logfile.log").read_text(encoding="utf-8")
