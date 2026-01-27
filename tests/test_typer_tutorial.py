from typing import Annotated
import wx
import tomlkit

import pytest
import typer
from loguru import logger

import guick


def test_typer_app(tmp_path, mocker):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: str):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App")
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


def test_typer_argument_required(tmp_path, mocker):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument()]):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App")
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


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ("", "Hello World"),
        ("Camilia", "Hello Camilia"),
    ],
)
def test_typer_argument_with_default(tmp_path, mocker, args, expected):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument()] = "World"):
        logger.info(f"Hello {name}")

    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App")
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


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ("", "Hello Rick"),
        ("Camilia", "Hello Camilia"),
    ],
)
def test_typer_argument_with_dynamic_default(tmp_path, mocker, args, expected):
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

    mocker.patch("wx.App")
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


def test_typer_argument_with_help_text(tmp_path, mocker):
    app = typer.Typer()

    @app.command(cls=guick.TyperCommandGui)
    def main(name: Annotated[str, typer.Argument(help="Who to greet")] = "World"):
        """
        Say hi to NAME very gently, like Dirk.
        """
        print(f"Hello {name}")

    mocker.patch("wx.App")
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

    if __name__ == "__main__":
        app()


def test_typer_argument_with_help_panel(tmp_path, mocker):
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

    if __name__ == "__main__":
        app()
    logger.remove()
    logger.add(
        tmp_path / "logfile.log",
        level="INFO",
    )

    mocker.patch("wx.App")
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
        dlg = wx.FindWindowByName("AboutDialog")
        assert "".join(main.__doc__.splitlines()) in "".join(
            dlg.text_ctrl.GetValue().splitlines()
        )
        assert "The last name" in "".join(dlg.text_ctrl.GetValue().splitlines())
        assert "Who to greet" in "".join(dlg.text_ctrl.GetValue().splitlines())
        return guick

    mocker.patch("guick.gui.Guick", init_gui)
    # mocker.patch("guick.Guick.on_close_buttton", lambda: pass)
    with pytest.raises(SystemExit):
        app()

    if __name__ == "__main__":
        app()
