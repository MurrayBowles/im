''' a report view of a Table '''

from dataclasses import dataclass
from typing import Any, List, Optional
import copy
import wx
import wx.lib.agw.ultimatelistctrl as ulc

from col_desc import ColDesc, LinkColDesc, SuperCD, TraitColDesc
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


@dataclass
class ColItem(object):
    disp_path: List[List[str]]      # joined with spaces to make the column title
    db_path: List[str]              # joined with _s to make the SQL alias
    cd_path: List[ColDesc]
    children: Optional[List[Any]]   # List[ColItem]

    @staticmethod
    def _add_col_item(
        ci_list, cd, disp_path, db_path, cd_path, viewed_cd_paths, hide_id=False
    ):
        if cd.db_name == 'id' and hide_id:
            return
        cdp = cd_path + cd.path()
        if isinstance(cd, LinkColDesc):
            if isinstance(cd, TraitColDesc):
                dip = disp_path
                dbp = db_path
                cil = ci_list
            else:
                dip = disp_path + [cd.disp_names]
                dbp = db_path + [cd.db_name]
                cil = []
            for fcd in cd.foreign_td.row_desc.col_descs:
                ColItem._add_col_item(
                    cil, fcd, dip, dbp, cdp, viewed_cd_paths, hide_id=True)
            if cil != ci_list and len(cil) != 0:
                ci_list.append(ColItem(
                    disp_path=disp_path + [cd.disp_names], db_path=db_path + [cd.db_name],
                    cd_path=cdp, children=cil))
        else:
            for vcp in viewed_cd_paths:
                for cdpe, vcpe in zip(cdp, vcp):
                    if cdpe.db_name != vcpe.db_name:
                        break
                else:
                    break  # cdp and vdp matched
            else:
                ci_list.append(ColItem(
                    disp_path=disp_path + [cd.disp_names], db_path=db_path + [cd.db_name],
                    cd_path=cdp, children=None))
                viewed_cd_paths.append(cdp)

    @staticmethod
    def col_items(cd_list: List[ColDesc], viewed_cds: List[ColDesc]):
        res = []
        viewed_cd_paths = [vcd.path() for vcd in viewed_cds]
        for cd in cd_list:
            ColItem._add_col_item(res, cd, [], [], [], viewed_cd_paths)
        return res


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

    def _gather_cd_menu_items(self, cd, tree, names, path):
        if isinstance(cd, LinkColDesc):
            if isinstance(cd, SuperCD):
                ns = names
            else:
                ns = names + [cd.disp_names[0]]
            subtree = []
            for fcd in cd.foreign_td.row_desc.col_descs:
                self._gather_cd_menu_items(fcd, subtree, ns, path + [cd])
            tree.append((cd, names + [cd.disp_names[0]], subtree))
        else:
            for old_cd in self.tbl_query.row_desc.col_descs:
                if path + [cd] == old_cd.path():
                    break
            else:
                tree.append((cd, names + [cd.disp_names[0]]))

    def _add_cd_menu_item(self, menu, tab_idx, col_item):
        title = ' '.join([dn[0] for dn in col_item.disp_path])
        if col_item.children is None:
            def lll(node):
                return lambda event: self.on_tab_menu_click(event, tab_idx, col_item)
            item = menu.Append(-1, title)
            self.Bind(wx.EVT_MENU, lll(col_item), item)
        else:  # 3
            sub = wx.Menu()
            for cci in col_item.children:
                self._add_cd_menu_item(sub, tab_idx, cci)
            menu.AppendSubMenu(sub, title)

    def _add_cd_menu_items(self, menu, tab_idx, row_desc: RowDesc):
        ci_list = ColItem.col_items(row_desc.col_descs, self.tbl_query.row_desc.col_descs)
        for ci in ci_list:
            self._add_cd_menu_item(menu, tab_idx, ci)
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

    def on_tab_menu_click(self, event, tab_idx, node):
        pass




