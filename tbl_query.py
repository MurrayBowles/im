''' database queries: Filters, Sorters '''

from typing import List

from tbl_desc import TblDesc
from col_desc import ColDesc, DataColDesc


class TblQuery(object):

    tbl_desc: TblDesc
    col_descs: List[ColDesc]
    # filter: Filter
    # sorter: Sorter

    def __init__(self, tbl_desc, col_descs):
        self.tbl_desc = tbl_desc
        self.cols = col_descs

    def __repr__(self):
        return 'TblQuery(%r, %r)' % (self.tbl_desc, self.col_descs)

    @classmethod
    def from_names(cls, tbl_db_name, col_db_names):
        tbl_desc = TblDesc.lookup_tbl_desc(tbl_db_name)
        col_descs = []
        for col_db_name in col_db_names:
            cd = tbl_desc.lookup_col_desc(col_db_name)
            col_descs.append(cd)
        return TblQuery(tbl_desc, col_descs)

    def db_query(self, session, limit=None, skip=0):
        cols = []
        for cd in self.col_descs:
            if isinstance(cd, DataColDesc):
                cols.append(getattr(self.tbl_desc.db_tbl_cls, cd.db_name))
            else:
                raise ValueError('%s has unsupported type' % (cd.db_name))
        q = session.Query(*cols)
        pass

from tbl_desc import DbFolder_td, DbImage_td

if __name__ == '__main__':
    q = TblQuery.from_names('DbFolder', ['date', 'name'])
    dbq = q.db_query(session, limit=10)
    pass