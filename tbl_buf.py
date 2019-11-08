''' table, block, and row buffers '''

from dataclasses import dataclass
from typing import List

from row_buf import RowBuf
from tbl_query import TblQuery


@dataclass
class BlkBuf(object):
    first_key: TblRowKey   # key of first row
    last_key: TblRowKey    # key of last row
    rows: List[RowBuf]  # never empty
    query: TblQuery

    @classmethod
    def from_row_buf_list(cls, rows: List[RowBuf], query: TblQuery):
        assert len(row_buf_list) > 0
        self.rows = list(rows)
        self.first_key = row[0].key()
        self.last_key = row[-1].key()
        self.query = query

class TblBuf(object):
    query: TblQuery         # the access interface to the table
    blk_bufs: List[BlkBuf]  # sorted by .first_key

    def __init__(self, tbl_query: TblQuery):
        self.set_query(tbl_query)

    def set_query(self, tbl_query):
        self.tbl_query = tbl_query
        self.blk_bufs = []

    def add_col(self, col_desc: ColDesc, idx: int = -1):
        pass

    def del_col(self, idx: int):
        pass

    def move_col(self, fro: int, to: int):
        pass

    def set_sorter(self, sorter: Sorter = None):
        self.query.set_sorter(sorter)
        self.blk_bufs = []  # invalidate the buffers

    def set_filter(self, filter):
        self.query.set_filter(filter)
        self.blk_bufs = []  # invalidate the buffers

    def get_rows(self, session, limit=None, skip=0):
        row_bufs = self.tbl_query.get_rows(session, limit, skip)
        bb = BlkBuf.from_row_buf_list(row_bufs, self.tbl_query)
        self.blk_bufs = [bb]
        return bb.rows

from base_path import dev_base_ie_source_path
from db import open_file_db

if __name__ == '__main__':
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    q_image = TblQuery.from_names('DbImage', ['name', 'folder_id', 'folder_name'])
    tb = TblBuf(q_image)
    rows = tb.get_rows(session, 10)
    pass