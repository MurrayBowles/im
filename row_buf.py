''' Database row buffers '''

from dataclasses import dataclass
from typing import Any, List

#from tbl_key import TblColKey, SorterKeyTup
#from tbl_query import TblQuery


@dataclass
class RowBuf(object):
    cols: List[Any]

    '''
    def get_key_tup(self, tbl_query:TblQuery):
        tbl_desc = tbl_query.tbl_desc
        keys = []
        for sc in tbl_query.sorter.cols:
            cx = tbl_desc.col_desc_idx(sc.col_desc)
            keys.append(TblColKey(idx=cx, col_desc=sc.col_desc)
        return SorterKeyTuple.from_list(keys)
    '''

