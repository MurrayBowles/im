''' a report view of a Table '''

import wx
import wx.lib.agw.ultimatelistctrl as ulc

from tab_panel_gui import TabPanel, TabPanelStack
from tbl_view import TblTP


class TblReportTP(TblTP):

    def __init__(self, parent: TabPanelStack, tbl_desc):
        super().__init__(parent, tbl_desc)
        try:
            report = ulc.UltimateListCtrl(
                self, -1, agwStyle=wx.LC_REPORT|wx.LC_VRULES|wx.LC_HRULES|wx.LC_VIRTUAL)
        except Exception as ed:
            print('kk')
        vc = tbl_desc.viewed_cols(TblReportTP)
        for x, name in zip(range(len(vc)), vc):
            report.InsertColumn(x, name)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(report, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.push()




