''' row descriptor '''

from dataclasses import dataclass
from typing import Tuple

from col_desc import ColDesc

@dataclass
class RowDesc(object):
    col_descs: Tuple[ColDesc]

    def __init__(self, col_desc_seq):
        self.col_descs = tuple(col_desc_seq)    # why doesn't dataclass generate this?
