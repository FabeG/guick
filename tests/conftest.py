import sys

import pytest
import wx


@pytest.fixture(scope="session")
def wx_app():
    sys.argv = [sys.argv[0]]  # clear args to avoid interference
    """Create a wx.App instance for all tests"""
    app = wx.App(False)  # False = don't redirect stdout/stderr
    # app.SetExitOnFrameDelete(False) 
    yield app
    app.Destroy()

@pytest.fixture(autouse=True)
def cleanup_gui():
    """Automatically runs after every test to clean up windows."""
    yield
    
    # This part runs AFTER the test finishes
    def finalize():
        for window in wx.GetTopLevelWindows():
            if window:
                window.Destroy()
        # Process all pending destruction events
        wx.SafeYield() 
    
    # We use CallAfter to ensure we are in the right context
    wx.CallAfter(finalize)
    # Give it a tiny bit of breath to clear the queue
    wx.SafeYield()
