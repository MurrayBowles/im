''' database queries: Filters, Sorters '''

import copy
from typing import List, Optional

from sqlalchemy.orm import aliased, with_polymorphic

from base_path import dev_base_ie_source_path
from col_desc import ColDesc, DataColDesc, LinkColDesc, ShortcutCD
from db import DbFolder, DbImage
from db import open_file_db, close_db
from row_buf import RowBuf
from tbl_key import Sorter
from tbl_desc import TblDesc


class TblQuery(object):

    tbl_desc: TblDesc
    col_descs: List[Optional[ColDesc]]
        # elements are never deleted, to keep TblColKey/SorterCol.idx stable:
        # when "deleted", a column is replaced by None
    # filter: Filter
    sorter: Sorter

    def __init__(self, tbl_desc, col_descs, sorter=None):
        self.tbl_desc = tbl_desc
        self.col_descs = copy.copy(col_descs)
        self.sorter = copy.copy(sorter if sorter is not None else tbl_desc.sorter)
        self.db_query = None

    def __repr__(self):
        return 'TblQuery(%r, %r)' % (self.tbl_desc, self.col_descs, self.sorter)

    def __getstate__(self):
        col_descs = []
        for cd in self.col_descs:
            try:
                self.tbl_desc.lookup_col_desc(cd.db_name)
                col_descs.append(cd.db_name)    # the name string for builtin columns
            except KeyError:
                col_descs.append(cd)            # the ColDesc for user-defined columns
        s = {
            'tbl_cls_name': self.tbl_desc.db_tbl_cls.__name__,
            'col_descs': col_descs,
            'sorter': self.sorter.get_state()
        }
        return s

    def __setstate__(self, state):
        self.tbl_desc = TblDesc.lookup_tbl_desc(state['tbl_cls_name'])
        self.col_descs = []
        for scd in state['col_descs']:
            if type(scd) is str:
                self.col_descs.append(self.tbl_desc.lookup_col_desc(scd))
            else:
                self.col_descs.append(scd)
        self.sorter = Sorter.from_state(
            state['sorter'], self.col_descs + self.tbl_desc.col_descs)
        pass

    @classmethod
    def from_names(cls, tbl_db_name, col_db_names):
        tbl_desc = TblDesc.lookup_tbl_desc(tbl_db_name)
        col_descs = []
        for col_db_name in col_db_names:
            cd = tbl_desc.lookup_col_desc(col_db_name)
            col_descs.append(cd)
        return TblQuery(tbl_desc, col_descs)

    def get_db_query(self, session):
        if self.db_query is None:
            cols = []
            join_set = set()    # Set of Tuples
            for cd in self.col_descs:
                try:
                    if isinstance(cd, DataColDesc) or isinstance(cd, LinkColDesc):
                        cols.append(getattr(self.tbl_desc.db_tbl_cls, cd.db_name).label(cd.db_name))
                    elif isinstance(cd, ShortcutCD):
                        join_list = []  # List of (child TD, parent/ref CD db_name, parent/ref TD)
                        td1 = self
                        x = 0
                        for pcd in cd.path_cds:
                            if x == len(cd.path_cds) - 1:
                                t1_name = td1.db_tbl_cls.__name__ + '_' + str(x + 1)
                                t1_alias = aliased(td1.db_tbl_cls, name=t1_name)
                                cols.append(getattr(t1_alias, pcd.db_name).label(cd.db_name))
                            else:
                                td2 = pcd.foreign_td
                                join_list.append((td1, pcd.db_name, td2))
                                # TODO: explicitly specify joins
                                pass
                                td1 = td2
                            x += 1
                        join_set.add(tuple(join_list))
                    else:
                        raise ValueError('%s has unsupported type' % (cd.db_name))
                except Exception as ed:
                    print('hi')
            try:
                q = session.query(*cols)
                # TODO: explicitly suggest joins
                for sc in self.sorter.cols:
                    if sc.descending:
                        q = q.order_by(getattr(self.tbl_desc.db_tbl_cls, sc.col_desc.db_name).desc())
                    else:
                        q = q.order_by(getattr(self.tbl_desc.db_tbl_cls, sc.col_desc.db_name))
                    pass
            except Exception as ed:
                print('hey')
                pass
            self.db_query = q
        return self.db_query

    def get_rows(self, session, limit=None, skip=0):
        if self.db_query is None:
            self.get_db_query(session)
        try:
            row_bufs: RowBuf = []
            db_rows = self.db_query[skip:] if limit is None else self.db_query[skip:skip+limit]
            for dbr in db_rows:
                cols = []
                for dbc in dbr:
                    cols.append(dbc)  # TODO: non-identity cases?
                row_bufs.append(RowBuf(cols))
            return row_bufs
        except Exception as ed:
            print('hey')
            pass

from tbl_desc import DbFolder_td, DbImage_td
import jsonpickle

if __name__ == '__main__':
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    TblDesc.complete_tbl_descs()
    q_folder = TblQuery.from_names('DbFolder', ['date', 'name', 'id'])
    r_folder = q_folder.get_rows(session, skip=1)
    q_image = TblQuery.from_names('DbImage', ['name', 'folder_id', 'folder_name'])
    r_image = q_image.get_rows(session, skip=126, limit=10)
    r_raw_image = session.query(DbImage)[:]
    # FIXME: results from my, web; no results from main, corbett
    json = jsonpickle.encode(q_image)
    try:
        q_image2 = jsonpickle.decode(json)
    except Exception as ed:
        print('hi')
    pass