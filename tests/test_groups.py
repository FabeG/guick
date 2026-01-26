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


def test_groups(tmp_path, mocker, wx_app):
    @click.group(cls=guick.GroupGui)
    def greeting():
        pass

    @greeting.command()
    @click.option('--count', default=1)
    def hello(count):
        for x in range(count):
            logger.info("Hello!")

    @greeting.command()
    @click.option('--count', default=1)
    def goodbye(count):
        for x in range(count):
            logger.info("Goodbye!")
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    original_init = guick.Guick
    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["hello"].entries["count"].SetValue("2")
        guick.on_ok_button(None)
        return guick
    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        greeting()
    assert "Hello!" in (tmp_path / "logfile.log").read_text(encoding="utf-8")

