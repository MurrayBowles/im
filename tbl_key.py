''' key and sort specifications '''

from dataclasses import dataclass
from typing import List, Optional

from col_desc import ColDesc


@dataclass
class TblColKey(object):
    col_desc: ColDesc
    idx: Optional[int]  # the index of col_desc in its tbl_buf.query.col_descs


@dataclass
class TblKey(object):
    col_keys: List[TblColKey]


@dataclass
class SorterCol(object):
    col_desc: ColDesc
    descending: bool
    idx: Optional[int]  # the index of col_desc in its query.col_descs

    def get_state(self):
        return '%s%s' % ('-' if self.descending else '+', self.col_desc.db_name)

    @classmethod
    def from_state(cls, state, col_descs: List[ColDesc]):
        col_desc = ColDesc.find(state[1:], col_descs)
        return SorterCol(col_desc, state[0] == '-')

@dataclass
class Sorter(object):
    cols: List[SorterCol]

    def get_state(self):
        return [ s.get_state() for s in self.cols ]

    @classmethod
    def from_state(cls, state, col_descs: List[ColDesc]):
        return Sorter([SorterCol.from_state(col_state, col_descs) for col_state in state])

