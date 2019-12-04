""" persistent data for GUI: cfg.gui """

import wx

class GuiCfg(object):

    def __init__(self):
        self.pos = (-1, -1)
        self.size = (1200, 800)
        self.notebook = None
