""" database table descriptor, used by tbl_acc, tbl/row_buf, and tbl_xxx_view """

from dataclasses import dataclass
from typing import Any, List, Mapping, NewType, Tuple, Type

from col_desc import ColDesc, DataColDesc, LinkColDesc
from col_desc import DateCD, IdCD, ParentCD, ShortcutCD, TextCD
from row_desc import RowDesc
from tbl_key import Sorter, SorterCol
from tbl_view import TblView, TblItemView, TblReportView
from util import find_descendent_class, force_list

import db
ImTblCls = Type[db.Base] # a database table class


class TblDesc(object):
    db_tbl_cls: ImTblCls        # the Python database-table class
    disp_names: List[str]       # display names, in decreasing length
    row_desc: RowDesc           # this table's predefined columns
    def_viewed_row: Mapping[Type[TblView], RowDesc]
    sorter: Sorter
    # TODO tag_field

    objs = []  # List[TblDesc]

    def __init__(self, db_tbl_cls, disp_names, col_desc_list, def_viewed_cols, sorter_str):
        self.db_tbl_cls = db_tbl_cls
        self.disp_names = force_list(disp_names)
        self.row_desc = RowDesc(col_desc_list)
        self.def_viewed_row = def_viewed_cols
        self.sorter_str = sorter_str
        self.sorter = None
        TblDesc.objs.append(self)
        pass

    @classmethod
    def lookup_tbl_desc(cls, db_name):
        for td in cls.objs:
            if td.db_tbl_cls.__name__ == db_name:
                return td
        raise KeyError('%s is not a known TblDesc' %s (db_name))

    def lookup_col_desc(self, db_name):
        for cd in self.row_desc.col_descs:
            if cd.db_name == db_name:
                if not hasattr(cd, 'db_attr'):
                    cd.db_attr = getattr(self.db_tbl_cls, db_name, None)
                return cd
        raise KeyError('%s has no attribute %s' % (
            self.db_tbl_cls.__name__, db_name))

    def col_idx(self, col_desc):
        return self.row_desc.col_descs.index(cd)

    def set_sorter(self, sorter: Sorter):
        self.sorter = sorter

    def set_sorter_by_col_name(self, key_str):
        ''' Set the Sorter for this table.
            key_str is {{+-}col_spec,...  (with no spaces)
        '''
        col_specs = key_str.split(',')
        sorter_cols = []
        x = 0
        for col_spec in col_specs:
            cd = self.lookup_col_desc(col_spec[1:])
            sorter_cols.append(SorterCol(cd, col_spec[0] == '-', idx=x))
            x += 1
        sorter = Sorter(sorter_cols)
        self.set_sorter(sorter)

    def _complete_col_desc(self, col_desc: ColDesc):
        if isinstance(col_desc, DataColDesc) or isinstance(col_desc, LinkColDesc):
            col_desc.db_attr = getattr(self.db_tbl_cls, col_desc.db_name, None)
            if isinstance(col_desc, LinkColDesc):
                col_desc.foreign_td = TblDesc.lookup_tbl_desc(col_desc.foreign_tbl_name)
                pass
        elif isinstance(col_desc, ShortcutCD):
            tbl_desc = self
            col_desc.path_cds = []
            for step_name in col_desc.path_str.split('.'):
                if tbl_desc is None:
                    raise ValueError('no TblDesc to evaluate %s' % (step_name))
                step_cd = tbl_desc.lookup_col_desc(step_name)
                if isinstance(step_cd, ShortcutCD):
                    if step_cd.path_cds is None:
                        tbl_desc._complete_col_desc(step_cd)
                    if isinstance(step_cd.path_cds[-1], LinkCD):
                        tbl_desc = step_cd.path_cds[-1].foreign_td
                    else:
                        tbl_desc = None
                    col_desc.path_cds.extend(step_cd.path_cds)
                elif isinstance(step_cd, LinkColDesc):
                    if step_cd.foreign_td is None:
                        tbl_desc._complete_col_desc(step_cd)
                    tbl_desc = step_cd.foreign_td
                    col_desc.path_cds.append(step_cd)
                elif isinstance(step_cd, DataColDesc):
                    tbl_desc = None
                    col_desc.path_cds.append(step_cd)

    def _complete(self):
        for col_desc in self.row_desc.col_descs:
            self._complete_col_desc(col_desc)
        self.set_sorter_by_col_name(self.sorter_str)

    @classmethod
    def complete_tbl_descs(cls):
        for tbl_desc in cls.objs:
            tbl_desc._complete()

    def viewed_cols(self, view_cls):
        # TODO: per-table[-per-user] cfg bindings
        if view_cls not in self.def_viewed_row:
            return self.def_viewed_row[TblReportView]
        else:
            return self.def_viewed_row[view_cls]

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (
            self.__class__.__name__,
            self.db_tbl_cls.__name__, self.disp_names,
            self.row_desc,
            self.def_viewed_row)


class ItemTblDesc(TblDesc):
    def __init__(self, db_tbl_cls, disp_names, col_descs, def_viewed_cols, sorter_str):
        extended_col_descs = [
            IdCD('id', ['ID']),
            TextCD('name', ['Name']),
            TextCD('type', 'Type')  # FIXME: TblTypeColDesc
        ]
        extended_col_descs.extend(col_descs)
        super().__init__(db_tbl_cls, disp_names, extended_col_descs, def_viewed_cols, sorter_str)
    pass


Item_td = ItemTblDesc(db.Item, 'Item', [], {
    TblReportView: ['name', 'type']
}, '+id')

DbFolder_td = ItemTblDesc(db.DbFolder, ['Database Folder', 'DbFolder'], [
    DateCD('date', ['Date'])
], {
    TblReportView: ['name', 'date']
}, '-date,+name')

DbImage_td = ItemTblDesc(db.DbImage, 'Database Image', [
    ParentCD('folder_id', 'Folder', foreign_tbl_name='DbFolder'),
    ShortcutCD('folder_date', 'Folder Date', path_str='folder_id.date'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder_id.name')
], {
    TblReportView: ['name', 'parent_id']
}, '-folder_date,+folder_name,+name')

TblDesc.complete_tbl_descs()

if __name__== '__main__':
    Item_s = repr(Item_td)
    report_vcs = Item_td.viewed_cols(TblReportView)
    item_vcs = Item_td.viewed_cols(TblItemView)
    DbFolder_s = repr(DbFolder_td)
    TblDesc.complete_tbl_descs()
    pass