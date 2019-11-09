''' table, block, and row buffers '''

from dataclasses import dataclass
from typing import List

from col_desc import ColDesc
from row_buf import RowBuf
from row_desc import RowDesc
from sorter import Sorter
from tbl_query import TblQuery


@dataclass
class BlkBuf(object):
    data_row_desc: RowDesc
    key_row_desc: RowDesc
    first_key: RowBuf       # key of first row
    last_key: RowBuf        # key of last row
    row_bufs: List[RowBuf]  # never empty

    @classmethod
    def from_row_buf_list(cls, row_bufs: List[RowBuf], query: TblQuery):
        assert len(row_bufs) > 0
        data_row_desc = query.row_desc
        key_row_desc = query.sorter.row_desc
        first_key = row_bufs[0].extract(data_row_desc, key_row_desc)
        last_key = row_bufs[-1].extract(data_row_desc, key_row_desc)
        try:
            return BlkBuf(
                data_row_desc=data_row_desc, key_row_desc=key_row_desc,
                first_key=first_key, last_key=last_key,
                row_bufs=row_bufs
            )
        except Exception as ed:
            print('a')


class TblBuf(object):
    cli_query: TblQuery     # the query specified by the client
    buf_query: TblQuery     # the query used by TblBuf (may have added key columns)
    blk_bufs: List[BlkBuf]  # sorted by .first_key

    def __init__(self, cli_query: TblQuery):
        self.set_query(cli_query)

    def _set_tbl_query(self):
        added_key_col_descs = self.cli_query.missing_key_col_descs()
        if len(added_key_col_descs) == 0:
            self.tbl_query = self.cli_query
        else:
            # add added_key_col_descs to the query
            self.tbl_query = TblQuery(
                self.cli_query.tbl_desc,
                RowDesc(list(self.cli_query.row_desc.col_descs) + added_key_col_descs),
                self.cli_query.sorter
            )

    def set_query(self, cli_query):
        self.cli_query = cli_query
        self._set_tbl_query()
        self.blk_bufs = []

    def add_col(self, col_desc: ColDesc, idx: int = -1):
        pass

    def del_col(self, idx: int):
        pass

    def move_col(self, fro: int, to: int):
        pass

    def set_sorter(self, sorter: Sorter = None):
        self.cli_query.set_sorter(sorter)
        self._set_tbl_query()
        self.blk_bufs = []  # invalidate the buffers

    def set_filter(self, filter):
        self.cli_query.set_filter(filter)
        self.tbl_query.set_filter(filter)
        self.blk_bufs = []  # invalidate the buffers

    def get_rows(self, session, limit=None, skip=0):
        row_bufs = self.tbl_query.get_rows(session, limit, skip)
        bb = BlkBuf.from_row_buf_list(row_bufs, self.tbl_query)
        self.blk_bufs = [bb]
        r = [
            rb.extract(bb.data_row_desc, self.cli_query.row_desc)
            for rb in bb.row_bufs
        ]
        return bb.rows

from base_path import dev_base_ie_source_path
from db import open_file_db

if __name__ == '__main__':
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    q_image = TblQuery.from_names('DbImage', ['name', 'folder_id', 'folder_name'])
    tb = TblBuf(q_image)
    row_bufs = tb.get_rows(session, 10)
    pass