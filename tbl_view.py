""" database table viewers """

import wx

from tab_panel_gui import TabPanel, TabPanelStack


class TblTP(TabPanel):

    def __init__(self, parent: TabPanelStack, tbl_desc):
        super().__init__(parent)
        self.tbl_desc = tbl_desc
        # subclasses end initialization by calling self.push()

    @classmethod
    def cls_text(cls):
        return 'Table'

    def inst_text(self):
        return self.tbl_desc.disp_names[0]


class TblItemTP(TblTP):
    pass


