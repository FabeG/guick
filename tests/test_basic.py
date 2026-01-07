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


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        # TODO: distinguish no value -> default_value, value UNSET, and empty string
        ("", "S:[no value]"),
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
        guick.cmd_panels["cli"].on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("", "I:[84]"),
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["i"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("", "U:[ba122011-349f-423b-873b-9d6a79c688ab]"),
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["u"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        ("", "F:[42.0]"),
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["f"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
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
        guick.cmd_panels[list(guick.cmd_panels.keys())[0]].on_ok_button(None)
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
        guick.cmd_panels["write-to-dir"].on_ok_button(None)
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
        guick.cmd_panels["write-to-dir"].on_ok_button(None)
        error = guick.cmd_panels["write-to-dir"].text_errors["o"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["write-to-dir"].on_close_button(None)
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
        guick.cmd_panels["showtype"].on_ok_button(None)
        error = guick.cmd_panels["showtype"].text_errors["f"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["showtype"].on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    with pytest.raises(SystemExit):
        showtype()
    assert "does not exist" in (tmp_path / "logfile.log").read_text(encoding="utf-8")

    def init_gui_new(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["showtype"].entries["f"].SetValue(".")
        guick.cmd_panels["showtype"].on_ok_button(None)
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
        guick.cmd_panels["exists"].on_ok_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["method"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
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
        guick.cmd_panels["cli"].on_ok_button(None)
        error = guick.cmd_panels["cli"].text_errors["start_date"].GetLabel()
        if error:
            logger.info(error)
            guick.cmd_panels["cli"].on_close_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert expect in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_datetime_option_custom(tmp_path, mocker):
    @click.command(cls=guick.CommandGui)
    @click.option("--start_date", type=click.DateTime(formats=["%A %B %d, %Y"]))
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
        guick.cmd_panels["cli"].entries["start_date"].SetValue("Wednesday June 05, 2010")
        guick.cmd_panels["cli"].on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        cli()
    assert "2010-06-05T00:00:00" in (tmp_path / "logfile.log").read_text(encoding="utf-8")
