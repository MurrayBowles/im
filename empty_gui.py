''' empty-tab GUI '''

import wx

from tab_panel_gui import TabPanel, TabPanelStack

class EmptyTP(TabPanel):

    def __init__(self, parent: TabPanelStack):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.push()

    def save(self):
        return {'type': 'Empty'}

    @classmethod
    def cls_text(cls):
        return '+'

