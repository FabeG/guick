import pytest
import wx

@pytest.fixture(scope="session", autouse=True)
def wx_app():
    """Create a wx.App instance for all tests"""
    app = wx.App(False)  # False = don't redirect stdout/stderr
    yield app
    app.Destroy()
