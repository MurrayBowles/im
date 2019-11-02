""" database table descriptor, used by tbl_acc, tbl/row_buf, and tbl_xxx_view """

from dataclasses import dataclass
from typing import Any, List, Mapping, NewType, Tuple, Type

from col_desc import ColDesc, DataColDesc, LinkColDesc
from col_desc import DateCD, IdCD, ParentCD, ShortcutCD, TextCD
from tbl_view import TblView, TblItemView, TblReportView
from util import find_descendent_class, force_list

import db
ImTblCls = Type[db.Base] # a database table class

# TODO: put Sorters in their own file
SorterElt = Tuple[ColDesc, bool]


class Sorter(object):
    elts: List[SorterElt]


class TblDesc(object):
    db_tbl_cls: ImTblCls        # the Python database-table class
    disp_names: List[str]       # display names, in decreasing length
    col_descs: List[ColDesc]    # this table's predefined columns
    def_viewed_cols: Mapping[Type[TblView], List[ColDesc]]
    # TODO: sorter: Sorter
    # TODO tag_field

    objs = []  # List[TblDesc]

    def __init__(self, db_tbl_cls, disp_names, col_descs, def_viewed_cols):
        self.db_tbl_cls = db_tbl_cls
        self.disp_names = force_list(disp_names)
        self.col_descs = col_descs
        self.def_viewed_cols = def_viewed_cols
        TblDesc.objs.append(self)
        pass

    @classmethod
    def lookup_tbl_desc(cls, db_name):
        for td in cls.objs:
            if td.db_tbl_cls.__name__ == db_name:
                return td
        raise KeyError('%s is not a known TblDesc' %s (db_name))

    def lookup_col_desc(self, db_name):
        for cd in self.col_descs:
            if cd.db_name == db_name:
                cd.db_attr = getattr(self.db_tbl_cls, db_name, None)
                return cd
        raise KeyError('%s has no attribute %s' % (
            self.db_tbl_cls.__name__, db_name))

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


    @classmethod
    def complete_tbl_descs(cls):
        for tbl_desc in cls.objs:
            for col_desc in tbl_desc.col_descs:
                tbl_desc._complete_col_desc(col_desc)

    def viewed_cols(self, view_cls):
        # TODO: per-table[-per-user] cfg bindings
        if view_cls not in self.def_viewed_cols:
            return self.def_viewed_cols[TblReportView]
        else:
            return self.def_viewed_cols[view_cls]

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (
            self.__class__.__name__,
            self.db_tbl_cls.__name__, self.disp_names,
            self.col_descs, self.def_viewed_cols)


class ItemTblDesc(TblDesc):
    def __init__(self, db_tbl_cls, disp_names, col_descs, def_viewed_cols):
        extended_col_descs = [
            IdCD('id', ['ID']),
            TextCD('name', ['Name']),
            TextCD('type', 'Type')  # FIXME: TblTypeColDesc
        ]
        extended_col_descs.extend(col_descs)
        super().__init__(db_tbl_cls, disp_names, extended_col_descs, def_viewed_cols)
    pass


Item_td = ItemTblDesc(db.Item, 'Item', [], {
    TblReportView: ['name', 'type']
})

DbFolder_td = ItemTblDesc(db.DbFolder, ['Database Folder', 'DbFolder'], [
    DateCD('date', ['Date'])
], {
    TblReportView: ['name', 'date']
})

DbImage_td = ItemTblDesc(db.DbImage, 'Database Image', [
    ParentCD('folder_id', 'Folder', foreign_tbl_name='DbFolder'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder_id.name')
], {
    TblReportView: ['name', 'parent_id']
})

TblDesc.complete_tbl_descs()

if __name__== '__main__':
    Item_s = repr(Item_td)
    report_vcs = Item_td.viewed_cols(TblReportView)
    item_vcs = Item_td.viewed_cols(TblItemView)
    DbFolder_s = repr(DbFolder_td)
    pass