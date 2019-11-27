''' empty-tab GUI '''

import wx

from tab_panel_gui import TabPanel, TabPanelStack

class EmptyTP(TabPanel):

    def __init__(self, parent: TabPanelStack):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.push()

    @classmethod
    def cls_text(cls):
        return '+'


class TableTP(TabPanel):

    def __init__(self, parent: TabPanelStack, tbl_desc):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.tbl_desc = tbl_desc
        self.push()

    @classmethod
    def cls_text(cls):
        return 'Table'

    def inst_text(self):
        return self.tbl_desc.disp_names[0]

