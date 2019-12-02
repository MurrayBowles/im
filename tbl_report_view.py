''' a report view of a Table '''

from typing import List
import wx
import wx.lib.agw.ultimatelistctrl as ulc

from col_desc import ColDesc, LinkColDesc, SuperCD
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

    def _add_cd_menu_items0(self, cd, tree, names, path):
        if isinstance(cd, LinkColDesc):
            if isinstance(cd, SuperCD):
                ns = names
            else:
                ns = names + [cd.disp_names[0]]
            subtree = []
            for fcd in cd.foreign_td.row_desc.col_descs:
                self._add_cd_menu_items0(fcd, subtree, ns, path + [cd])
            tree.append((cd, names + [cd.disp_names[0]], subtree))
        else:
            for old_cd in self.tbl_query.row_desc.col_descs:
                if path + [cd] == old_cd.path():
                    break
            else:
                tree.append((cd, names + [cd.disp_names[0]]))

    def add_cd_menu_items2(self, menu, tab_idx, tree):
        for node in tree:
            if len(node) == 2:
                item = menu.Append(-1, ' '.join(node[1]))
                self.Bind(
                    wx.EVT_MENU, lambda event: self.on_tab_menu_click(event, tab_idx, node))
            else:  # 3
                sub = wx.Menu()
                self.add_cd_menu_items2(sub, tab_idx, node[2])
                menu.AppendSubMenu(sub, ' '.join(node[1]))

    def _add_cd_menu_items(self, menu, tab_idx, row_desc: RowDesc):
        tree = []
        for cd in row_desc.col_descs:
            self._add_cd_menu_items0(cd, tree, [], [])
        self.add_cd_menu_items2(menu, tab_idx, tree)
        pass

    def on_hdr_right_click(self, event):
        col = self._get_col_idx(event)
        menu = wx.Menu()
        self._add_cd_menu_items(menu, col, self.tbl_query.tbl_desc.row_desc)
        if col == -1:  # clicked right of the rightmost column
            pass
        else:
            # TODO: add filter, sorter items
            pass
        self.PopupMenu(menu)
        pass

    def on_tab_menu_click(self, event, node):
        pass




