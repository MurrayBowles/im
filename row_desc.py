''' row descriptor '''

from dataclasses import dataclass
from typing import Tuple

from col_desc import ColDesc

@dataclass
class RowDesc(object):
    col_descs: Tuple[ColDesc]

    def __init__(self, col_desc_seq):
        self.col_descs = tuple(col_desc_seq)    # why doesn't dataclass generate this?

    def has_col_desc(self, col_desc):
        # Python is so compact and clutter-free!
        try:
            self.col_descs.index(col_desc)
            return True
        except ValueError:  # WTF: not KeyError!
            return False
