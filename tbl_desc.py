""" database table descriptor, used by tbl/row_buf and tbl_xxx_view """

from dataclasses import dataclass
from typing import Any, List, Mapping, NewType, Tuple, Type

from col_desc import ColDesc, TextColDesc
from tbl_view import TblView, TblItemView, TblReportView
from util import force_list

import db
ImTblCls = Type[db.Base] # a database table class

# TODO: put Sorters in their own file
SorterElt = Tuple[ColDesc, bool]

class Sorter(object):
    elts: List[SorterElt]

class TblDesc(object):
    tbl_cls: ImTblCls
    disp_names: List[str] # display names, in decreasing length
    col_descs: List[ColDesc]
    def_viewed_cols: Mapping[Type[TblView], ColDesc]
    # TODO: sorter: Sorter
    # TODO tag_field

    def __init__(self, tbl_cls, disp_names, col_descs, def_viewed_cols):
        self.tbl_cls = tbl_cls  # the python database-table class
        self.disp_names = force_list(disp_names)
        self.col_descs = col_descs
        self.def_viewed_cols = def_viewed_cols
        pass

    def viewed_cols(self, view_cls):
        # TODO: per-table[-per-user] cfg bindings
        if view_cls not in self.def_viewed_cols:
            return self.def_viewed_cols[RblReportView]
        else:
            return self.def_viewwed_cols[view_cls]

    def __repr__(self):
        s = 'TblDesc(%s, %s' % (self.tbl_cls.__name__, repr(self.disp_names))
        s += ', %s, %s' % (repr(self.col_descs), repr(self.def_viewed_cols))
        s += ')'
        return s

if __name__== '__main__':
    ItemTD = TblDesc(db.Item, 'Item', [
        TextColDesc('name', ['Name'])
    ], {
        TblReportView: ['name']
    })
    s = repr(ItemTD)
    pass