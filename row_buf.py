''' Database row buffers and descriptors '''

from dataclasses import dataclass
from typing import Any, List

from row_desc import RowDesc


@dataclass
class RowBuf(object):
    cols: List[Any]

    def extract(self, buf_row_desc: RowDesc, tgt_row_desc: RowDesc) -> 'RowBuf':
        rb = RowBuf([])
        for tcd in tgt_row_desc.col_descs:
            rb.cols.append(self.cols[buf_row_desc.col_descs.index(tcd)])
        return rb

