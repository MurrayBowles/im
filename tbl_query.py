''' database queries: Filters, Sorters '''

from typing import List

from base_path import dev_base_ie_source_path
from db import DbFolder
from db import open_file_db, close_db
from tbl_desc import TblDesc
from col_desc import ColDesc, DataColDesc


class TblQuery(object):

    tbl_desc: TblDesc
    col_descs: List[ColDesc]
    # filter: Filter
    # sorter: Sorter

    def __init__(self, tbl_desc, col_descs):
        self.tbl_desc = tbl_desc
        self.col_descs = col_descs

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

    def get(self, session, limit=None, skip=0):
        cols = []
        for cd in self.col_descs:
            if isinstance(cd, DataColDesc):
                cols.append(getattr(self.tbl_desc.db_tbl_cls, cd.db_name))
            else:
                raise ValueError('%s has unsupported type' % (cd.db_name))
        try:
            q = session.query(*cols)
        except Exception as ed:
            pass
        return q[skip:] if limit is None else q[skip:skip+limit]

from tbl_desc import DbFolder_td, DbImage_td

if __name__ == '__main__':
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    q = TblQuery.from_names('DbFolder', ['date', 'name'])
    res = q.get(session, skip=1)
    q = TblQuery.from_names('DbImage', ['name'])
    req = q.get(session)
    pass