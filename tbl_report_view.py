''' a report view of a Table '''

from typing import List
import wx
import wx.lib.agw.ultimatelistctrl as ulc

from col_desc import ColDesc
import db
from row_desc import RowDesc
from tab_panel_gui import TabPanel, TabPanelStack
from tbl_query import TblQuery
from tbl_view import TblTP


class TblULC(ulc.UltimateListCtrl):
    tbl_query: TblQuery

    def __init__(self, *args, **kwargs):
        tbl_query = kwargs.pop('tbl_query')
        super().__init__(*args, **kwargs)
        self.tbl_query = tbl_query

        for x, cd in enumerate(self.tbl_query.row_desc.col_descs):
            self.InsertColumn(x, cd.disp_names[0])

        num_rows = tbl_query.get_num_rows(db.session)
        self.SetItemCount(num_rows)

    def OnGetItemText(self, row, col):
        try:
            r = self.tbl_query.get_rows(db.session, skip=row, limit=1)
            c = r[0].cols[col]
            cd = self.tbl_query.row_desc.col_descs[col]
            return cd.gui_str(c)
        except Exception as ed:
            print('cc')

    def OnGetItemAttr(self, row):
        return None

    def OnGetItemToolTip(self, row, col):
        return self.OnGetItemText(row, col)

    def OnGetItemTextColour(self, row, col):
        return None

class TblReportTP(TblTP):

    def __init__(self, parent: TabPanelStack, tbl_query: TblQuery):
        super().__init__(parent, tbl_query)
        self.tbl_query = tbl_query

        sizer = wx.BoxSizer(wx.VERTICAL)

        #header
        sizer.AddSpacer(5)
        h = wx.StaticText(self, -1, '  ' + tbl_query.menu_text())
        sizer.Add(h, 0, 0) # wx.EXPAND)
        sizer.AddSpacer(5)

        try:
            report = self.report = TblULC(
                self, -1,
                agwStyle=(
                    wx.LC_REPORT | wx.LC_VIRTUAL
                  | ulc.ULC_SHOW_TOOLTIPS | wx.LC_VRULES | wx.LC_HRULES),
                tbl_query=tbl_query)
        except Exception as ed:
            print('kk')

        self.Bind(ulc.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_right_click)
        self.Bind(ulc.EVT_LIST_COL_RIGHT_CLICK, self.on_hdr_right_click)

        sizer.Add(report, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.push()

    def _get_col_idx(self, event):
        pos = event.GetPoint()  # (x, y)
        x = pos[0]
        lc = self.report
        col_pos = 0
        for col_idx in range(lc.GetColumnCount()):
            e = col_pos + lc.GetColumn(col_idx).GetWidth()
            if x < e:
                return col_idx
            col_pos = e
        else:
            return -1

    def on_item_right_click(self, event):
        row = event.GetIndex()
        col = self._get_col_idx(event)
        assert col >= 0
        # TODO add filter item
        pass

    def on_hdr_right_click(self, event):
        col = self._get_col_idx(event)
        mx = wx.menu()
        if col == -1:  # clicked right of the rightmost column
            pass
        else:
            # TODO: add filter, sorter items
            pass
        pass




