import os
import click
import pytest
import sys
import wx
from loguru import logger
import io
from contextlib import redirect_stdout
from rich import print
import rich.color


import guick

logger = logger.opt(colors=True)


@pytest.fixture
def wxapp():
    app = wx.App(False)
    yield app
    app.Destroy()


@pytest.fixture
def frame(wxapp):
    """Create a TextStyleFrame instance for testing"""
    frame = wx.Frame(None)
    frame.log_panel = guick.LogPanel(frame)
    windowSizer = wx.BoxSizer()
    windowSizer.Add(frame.log_panel, 1, wx.ALL | wx.EXPAND, 5)
    frame.SetSizerAndFit(windowSizer)
    frame.Show()
    # Process pending events to ensure the window is fully initialized
    wxapp.ProcessPendingEvents()
    wx.SafeYield()
    yield frame
    frame.Destroy()


@pytest.mark.parametrize(
    ("style", "color", "function", "expected_color"),
    [
        ("underline", "red", lambda attr: attr.GetFontUnderlined(), guick.TermColors.RED.value),
        ("strikethrough", "red", lambda attr: attr.GetFont().GetStrikethrough(), guick.TermColors.RED.value),
        ("bold", "red", lambda attr: attr.GetFontWeight() == wx.FONTWEIGHT_BOLD, guick.TermColors.BRIGHT_RED.value),
        ("italic", "red", lambda attr: attr.GetFontStyle() == wx.FONTSTYLE_ITALIC, guick.TermColors.RED.value),
        ("underline", "bright_red", lambda attr: attr.GetFontUnderlined(), guick.TermColors.BRIGHT_RED.value),
        ("strikethrough", "bright_red", lambda attr: attr.GetFont().GetStrikethrough(), guick.TermColors.BRIGHT_RED.value),
        ("bold", "bright_red", lambda attr: attr.GetFontWeight() == wx.FONTWEIGHT_BOLD, guick.TermColors.BRIGHT_RED.value),
        ("italic", "bright_red", lambda attr: attr.GetFontStyle() == wx.FONTSTYLE_ITALIC, guick.TermColors.BRIGHT_RED.value),
    ],
)
def test_string_style(frame, style, function, color, expected_color):
    underline = style == "underline"
    bold = style == "bold"
    italic = style == "italic"
    strikethrough = style == "strikethrough"
    with io.StringIO() as buf, redirect_stdout(buf):
        click.echo(click.style(f"hello {style}", fg=color, strikethrough=strikethrough, underline=underline, bold=bold, italic=italic), color=True)
        args = buf.getvalue()
    # args = "\x1b[4mhello underlined"
    expected = f"hello {style}\n"
    frame.log_panel.log_ctrl.append_ansi_text(args)
    log_content = frame.log_panel.log_ctrl.GetValue()
    assert log_content == expected
    # Find the position of "Test text" in the log
    text_pos = log_content.find(expected)

    # Get the TextAttr at the position of the actual text (after "Text: ")
    text_start = text_pos
    text_attr = wx.TextAttr()
    frame.log_panel.log_ctrl.GetStyle(text_start, text_attr)

    # Check that the font is bold
    click.echo(text_attr.GetTextEffects())
    click.echo(wx.TEXT_ATTR_EFFECT_STRIKETHROUGH)
    assert function(text_attr)
    assert text_attr.GetTextColour()[:3] == expected_color


@pytest.mark.parametrize(
    ("bg_color", "expected_color"),
    [
        ("red", guick.TermColors.RED.value),
        ("bright_red", guick.TermColors.BRIGHT_RED.value),
    ],
)
def test_string_bg(frame, bg_color, expected_color):
    with io.StringIO() as buf, redirect_stdout(buf):
        click.echo(click.style(f"hello {bg_color}", bg=bg_color), color=True)
        args = buf.getvalue()
    # args = "\x1b[4mhello underlined"
    expected = f"hello {bg_color}\n"
    frame.log_panel.log_ctrl.append_ansi_text(args)
    log_content = frame.log_panel.log_ctrl.GetValue()
    assert log_content == expected
    # Find the position of "Test text" in the log
    text_pos = log_content.find(expected)

    # Get the TextAttr at the position of the actual text (after "Text: ")
    text_start = text_pos
    text_attr = wx.TextAttr()
    frame.log_panel.log_ctrl.GetStyle(text_start, text_attr)

    # Check that the font is bold
    click.echo(text_attr.GetTextEffects())
    click.echo(wx.TEXT_ATTR_EFFECT_STRIKETHROUGH)
    assert text_attr.GetBackgroundColour()[:3] == expected_color


@pytest.mark.parametrize(
    ("style", "function", "expected_color"),
    [
        ("underline red", lambda attr: attr.GetFontUnderlined(), guick.TermColors.RED.value),
        ("strike red", lambda attr: attr.GetFont().GetStrikethrough(), guick.TermColors.RED.value),
        ("bold red", lambda attr: attr.GetFontWeight() == wx.FONTWEIGHT_BOLD, guick.TermColors.BRIGHT_RED.value),
        ("italic red", lambda attr: attr.GetFontStyle() == wx.FONTSTYLE_ITALIC, guick.TermColors.RED.value),
        ("underline bright_red", lambda attr: attr.GetFontUnderlined(), guick.TermColors.BRIGHT_RED.value),
        ("strike bright_red", lambda attr: attr.GetFont().GetStrikethrough(), guick.TermColors.BRIGHT_RED.value),
        ("bold bright_red", lambda attr: attr.GetFontWeight() == wx.FONTWEIGHT_BOLD, guick.TermColors.BRIGHT_RED.value),
        ("italic bright_red", lambda attr: attr.GetFontStyle() == wx.FONTSTYLE_ITALIC, guick.TermColors.BRIGHT_RED.value),
    ],
)
def test_print_rich(frame, style, function, expected_color):
    # Force rich to output ANSI codes
    os.environ['FORCE_COLOR'] = '1'
    with io.StringIO() as buf, redirect_stdout(buf):
        print(f"[{style}]hello {style}[/{style}]")
        args = buf.getvalue()
    print(args)
    # args = "\x1b[4mhello underlined"
    expected = f"hello {style}\n"
    frame.log_panel.log_ctrl.append_ansi_text(args)
    log_content = frame.log_panel.log_ctrl.GetValue()
    assert log_content == expected
    # Find the position of "Test text" in the log
    text_pos = log_content.find(expected)

    # Get the TextAttr at the position of the actual text (after "Text: ")
    text_start = text_pos
    text_attr = wx.TextAttr()
    frame.log_panel.log_ctrl.GetStyle(text_start, text_attr)

    assert function(text_attr)
    assert text_attr.GetTextColour()[:3] == expected_color


@pytest.mark.parametrize(
    ("color", "expected_color"),
    [
        (col_number, rich.color.Color.from_ansi(col_number).get_truecolor()) for col_number in range(18, 256)
    ],
)
def test_string_bg_256colors(frame, color, expected_color):
    from rich.console import Console
    os.environ['FORCE_COLOR'] = '1'
    os.environ["TERM"] = "xterm-256color"
    with io.StringIO() as buf, redirect_stdout(buf):

        console = Console(color_system="256")
        console.print(f"[color({color}) on color({color})]hello {color}[/]")
        args = buf.getvalue()
    # args = "\x1b[4mhello underlined"
    expected = f"hello {color}\n"
    frame.log_panel.log_ctrl.append_ansi_text(args)
    log_content = frame.log_panel.log_ctrl.GetValue()
    assert log_content == expected
    # Find the position of "Test text" in the log
    text_pos = log_content.find(expected)

    # Get the TextAttr at the position of the actual text (after "Text: ")
    text_start = text_pos
    text_attr = wx.TextAttr()
    frame.log_panel.log_ctrl.GetStyle(text_start, text_attr)

    assert text_attr.GetBackgroundColour()[:3] == expected_color
    assert text_attr.GetTextColour()[:3] == expected_color


def test_string_rgb(frame):
    logger.remove()
    with io.StringIO() as buf:
        logger.add(buf, colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
        logger.info("<fg 10,120,244><bg 200,50,150>hello RGB</></>")
        args = buf.getvalue()
    # args = "\x1b[4mhello underlined"
    expected = f"hello RGB\n"
    frame.log_panel.log_ctrl.append_ansi_text(args)
    log_content = frame.log_panel.log_ctrl.GetValue()
    assert expected in log_content
    # Find the position of "Test text" in the log
    text_pos = log_content.find(expected)

    # Get the TextAttr at the position of the actual text (after "Text: ")
    text_start = text_pos
    text_attr = wx.TextAttr()
    frame.log_panel.log_ctrl.GetStyle(text_start, text_attr)

    assert text_attr.GetBackgroundColour()[:3] == (200, 50, 150)
    assert text_attr.GetTextColour()[:3] == (10, 120, 244)
