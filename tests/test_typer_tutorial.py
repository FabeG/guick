from typing import Annotated
import os
import wx
import tomlkit

import pytest
import typer
from loguru import logger

import guick


def test_typer_app(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: str):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    # mock click.get_app and return tmp_path
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["main"].entries["name"].SetValue("Camilia")
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    assert "Hello Camilia" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_typer_argument_required(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument()]):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.on_ok_button(None)
        error = guick.cmd_panels["main"].text_errors["name"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    mocker.patch("guick.gui.Guick", original_init)
    assert "Missing parameter: name" in (tmp_path / "logfile.log").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ("", "Hello World"),
        ("Camilia", "Hello Camilia"),
    ],
)
def test_typer_argument_with_default(tmp_path, mocker, args, expected, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument()] = "World"):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        if args:
            guick.cmd_panels["main"].entries["name"].SetValue(args)
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    mocker.patch("guick.gui.Guick", original_init)
    assert expected in (tmp_path / "logfile.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ("", "Hello Rick"),
        ("Camilia", "Hello Camilia"),
    ],
)
def test_typer_argument_with_dynamic_default(tmp_path, mocker, args, expected, wx_app):
    app = typer.Typer()

    def get_name():
        return "Rick"

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument(default_factory=get_name)]):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        if args:
            guick.cmd_panels["main"].entries["name"].SetValue(args)
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    assert expected in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_typer_argument_with_help_text(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument(help="Who to greet")] = "World"):
        """
        Say hi to NAME very gently, like Dirk.
        """
        print(f"Hello {name}")

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        assert (
            "Who to greet"
            in guick.cmd_panels["main"].static_texts["name"].GetToolTipText()
        )
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()


def test_typer_argument_with_help_panel(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: Annotated[str, typer.Argument(help="Who to greet")],
        lastname: Annotated[
            str,
            typer.Argument(help="The last name", rich_help_panel="Secondary Arguments"),
        ] = "",
        age: Annotated[
            str,
            typer.Argument(
                help="The user's age", rich_help_panel="Secondary Arguments"
            ),
        ] = "",
    ):
        """
        Say hi to NAME very gently, like Dirk.
        """
        print(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        assert "Required Parameters" in guick.cmd_panels["main"].sections
        assert "Secondary Arguments" in guick.cmd_panels["main"].sections
        guick.on_help(None)
        dlg = wx.FindWindowByName("HelpDialog")
        assert "".join(main.__doc__.splitlines()).strip() in "".join(
            dlg.text_ctrl.GetValue().splitlines()
        )
        assert "The last name" in "".join(dlg.text_ctrl.GetValue().splitlines())
        assert "Who to greet" in "".join(dlg.text_ctrl.GetValue().splitlines())
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()


def test_typer_argument_unset_envvar(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: Annotated[
            str, typer.Argument(envvar=["AWESOME_NAME", "GOD_NAME"])
        ] = "World"
    ):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    assert "Hello World" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_typer_argument_with_envvar(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: Annotated[
            str, typer.Argument(envvar=["AWESOME_NAME", "GOD_NAME"])
        ] = "World"
    ):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    os.environ["AWESOME_NAME"] = "Wednesday"
    with pytest.raises(SystemExit):
        app()
    assert "Hello Wednesday" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_typer_argument_with_sec_envvar(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: Annotated[
            str, typer.Argument(envvar=["AWESOME_NAME", "GOD_NAME"])
        ] = "World"
    ):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    os.environ.pop("AWESOME_NAME", None)
    os.environ["GOD_NAME"] = "Anubis"
    with pytest.raises(SystemExit):
        app()
    assert "Hello Anubis" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_typer_option_with_help_text(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: str,
        lastname: Annotated[
            str, typer.Option(help="Last name of person to greet.")
        ] = "",
        formal: Annotated[bool, typer.Option(help="Say hi formally.")] = False,
    ):
        """
        Say hi to NAME, optionally with a --lastname.

        If --formal is used, say hi very formally.
        """
        if formal:
            print(f"Good day Ms. {name} {lastname}.")
        else:
            print(f"Hello {name} {lastname}")

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        assert (
            "Last name of person to greet."
            in guick.cmd_panels["main"].static_texts["lastname"].GetToolTipText()
        )
        assert (
            "Say hi formally."
            in guick.cmd_panels["main"].static_texts["formal"].GetToolTipText()
        )
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()


def test_typer_option_with_help_panel(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: str,
        lastname: Annotated[
            str, typer.Option(help="Last name of person to greet.")
        ] = "",
        formal: Annotated[
            bool,
            typer.Option(
                help="Say hi formally.", rich_help_panel="Customization and Utils"
            ),
        ] = False,
        debug: Annotated[
            bool,
            typer.Option(
                help="Enable debugging.", rich_help_panel="Customization and Utils"
            ),
        ] = False,
    ):
        """
        Say hi to NAME, optionally with a --lastname.

        If --formal is used, say hi very formally.
        """
        if formal:
            print(f"Good day Ms. {name} {lastname}.")
        else:
            print(f"Hello {name} {lastname}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        assert "Optional Parameters" in guick.cmd_panels["main"].sections
        assert "Customization and Utils" in guick.cmd_panels["main"].sections
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()


def test_typer_option_required(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: str, lastname: Annotated[str, typer.Option()]):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.on_ok_button(None)
        error = guick.cmd_panels["main"].text_errors["name"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    assert "Missing parameter: name" in (tmp_path / "logfile.log").read_text(
        encoding="utf-8"
    )


def test_typer_password(tmp_path, mocker, wx_app):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: str, password: Annotated[str, typer.Option(prompt=True, hide_input=True)]
    ):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["main"].entries["name"].SetValue("Camilia")
        guick.cmd_panels["main"].entries["password"].SetValue("123")
        guick.on_ok_button(None)
        assert not guick.cmd_panels["main"].entries["name"].HasFlag(wx.TE_PASSWORD)
        assert guick.cmd_panels["main"].entries["password"].HasFlag(wx.TE_PASSWORD)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()


def test_typer_argument_validate_nok(tmp_path, mocker, wx_app):
    app = typer.Typer()

    def name_callback(value: str):
        if value != "Camila":
            raise typer.BadParameter("Only Camila is allowed")
        return value

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str | None, typer.Option(callback=name_callback)] = None):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["main"].entries["name"].SetValue("Rick")
        guick.on_ok_button(None)
        error = guick.cmd_panels["main"].text_errors["name"].GetLabel()
        if error:
            logger.info(error)
            guick.on_close_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    assert "Only Camila is allowed" in (tmp_path / "logfile.log").read_text(
        encoding="utf-8"
    )


def test_typer_argument_validate_ok(tmp_path, mocker, wx_app):
    app = typer.Typer()

    def name_callback(value: str):
        if value != "Camila":
            raise typer.BadParameter("Only Camila is allowed")
        return value

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str | None, typer.Option(callback=name_callback)] = None):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.cmd_panels["main"].entries["name"].SetValue("Camila")
        guick.on_ok_button(None)
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
    assert "Hello Camila" in (tmp_path / "logfile.log").read_text(encoding="utf-8")


def test_typer_version(tmp_path, mocker, wx_app):
    app = typer.Typer()
    __version__ = "0.1.0"

    def version_callback(value: bool):
        if value:
            print(f"Awesome guick Version: {__version__}")
            raise typer.Exit()

    @app.command(cls=guick.TyperCommandGui)
    def main(
        name: Annotated[str, typer.Option()] = "World",
        version: Annotated[
            bool | None,
            typer.Option("--version", callback=version_callback, is_eager=True),
        ] = None,
    ):
        print(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App.MainLoop")
    mocker.patch("click.get_app_dir", return_value=str(tmp_path))
    # Save original
    original_show_modal = wx.Dialog.ShowModal

    # Replace ShowModal for all Dialog instances
    def mock_show_modal(self):
        self.Show()
        return wx.ID_OK

    wx.Dialog.ShowModal = mock_show_modal

    original_init = guick.Guick

    def init_gui(ctx, size=None):
        guick = original_init(ctx)
        guick.OnVersion(None)
        dlg = wx.FindWindowByName("VersionDialog")
        assert f"Awesome guick Version: {__version__}" in "".join(
            dlg.text_ctrl.GetValue().splitlines()
        )
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()
