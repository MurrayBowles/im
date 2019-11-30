''' a report view of a Table '''

import wx
import wx.lib.agw.ultimatelistctrl as ulc

import db
from row_desc import RowDesc
from tab_panel_gui import TabPanel, TabPanelStack
from tbl_query import TblQuery
from tbl_view import TblTP


class TblULC(ulc.UltimateListCtrl):

    def __init__(self, *args, **kwargs):
        tbl_desc = kwargs.pop('tbl_desc')
        super().__init__(*args, **kwargs)
        self.tbl_desc = tbl_desc

        vc = tbl_desc.viewed_cols(TblReportTP)
        cds = [tbl_desc.lookup_col_desc(name) for name in vc]
        query = self.query = TblQuery(tbl_desc, RowDesc(cds))
        for x, cd in enumerate(cds):
            self.InsertColumn(x, cd.disp_names[0])

        num_rows = query.get_num_rows(db.session)
        self.SetItemCount(num_rows)

    def OnGetItemText(self, row, col):
        try:
            r = self.query.get_rows(db.session, skip=row, limit=1)
        except Exception as ed:
            print('cc')
        c = r[0].cols[col]
        return str(c)

    def OnGetItemAttr(self, row):
        return None

    def OnGetItemToolTip(self, row, col):
        return None

    def OnGetItemTextColour(self, row, col):
        return None

class TblReportTP(TblTP):

    def __init__(self, parent: TabPanelStack, tbl_desc):
        super().__init__(parent, tbl_desc)
        self.tbl_desc = tbl_desc

        sizer = wx.BoxSizer(wx.VERTICAL)

        #header
        sizer.AddSpacer(5)
        h = wx.StaticText(self, -1, '  ' + tbl_desc.menu_text())
        sizer.Add(h, 0, 0) # wx.EXPAND)
        sizer.AddSpacer(5)

        try:
            report = self.report = TblULC(
                self, -1, agwStyle=wx.LC_REPORT|wx.LC_VRULES|wx.LC_HRULES|wx.LC_VIRTUAL,
                tbl_desc=tbl_desc)
        except Exception as ed:
            print('kk')
        sizer.Add(report, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.push()




