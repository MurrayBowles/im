''' sort specifications '''

from dataclasses import dataclass
from typing import Any, List, Optional

from col_desc import ColDesc
from row_desc import RowDesc
from util import attrs_eq

@dataclass
class SorterCol(object):
    col_desc: ColDesc
    descending: bool

    def get_state(self):
        return '%s%s' % ('-' if self.descending else '+', self.col_desc.db_name)

    @classmethod
    def from_state(cls, state, col_descs: List[ColDesc]):
        col_desc = ColDesc.find(state[1:], col_descs)
        return SorterCol(col_desc, state[0] == '-')

@dataclass
class Sorter(object):
    cols: List[SorterCol]
    row_desc: RowDesc

    def __init__(self, cols: List[SorterCol]):
        self.cols = cols
        self.row_desc = RowDesc([sc.col_desc for sc in self.cols])

    def get_state(self):
        return [ s.get_state() for s in self.cols ]

    @classmethod
    def from_state(cls, state, col_descs: List[ColDesc]):
        return Sorter([SorterCol.from_state(col_state, col_descs) for col_state in state])
