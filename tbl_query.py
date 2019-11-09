''' database access interface '''

import copy
from typing import List, Optional

from sqlalchemy.orm import aliased, with_polymorphic

from col_desc import ColDesc, DataColDesc, LinkColDesc, ShortcutCD
from db import DbFolder, DbImage
from row_buf import RowBuf
from row_desc import RowDesc
from sorter import Sorter
from tbl_desc import TblDesc


class TblQuery(object):

    tbl_desc: TblDesc
    row_desc: RowDesc
    # filter: Filter
    sorter: Sorter
        # the Sorter's ColDescs must be either from tbl_desc.col_descs or self.col_descs

    def __init__(self, tbl_desc: TblDesc, row_desc:RowDesc, sorter:Sorter=None):
        self.tbl_desc = tbl_desc
        self.row_desc = row_desc
        self.set_sorter(sorter)
        self.db_query = None

    def __repr__(self):
        return 'TblQuery(%r, %r, %r)' % (self.tbl_desc, self.row_desc, self.sorter)

    def __getstate__(self):
        if self.row_desc == self.tbl_desc.row_desc:
            row_desc = self.tbl_desc.row_desc
        else:
            col_descs = []
            for cd in self.row_desc.col_descs:
                try:
                    self.tbl_desc.lookup_col_desc(cd.db_name)
                    col_descs.append(cd.db_name)    # the name string for builtin columns
                except KeyError:
                    col_descs.append(cd)            # the ColDesc for user-defined columns
            row_desc = RowDesc(col_descs)
        s = {
            'tbl_cls_name': self.tbl_desc.db_tbl_cls.__name__,
            'row_desc': RowDesc(col_descs),
            'sorter': self.sorter.get_state()
        }
        return s

    def __setstate__(self, state):
        self.tbl_desc = TblDesc.lookup_tbl_desc(state['tbl_cls_name'])
        col_descs = []
        num_builtin = 0
        for scd in state['row_desc'].col_descs:
            if type(scd) is str:
                col_descs.append(self.tbl_desc.lookup_col_desc(scd))
                num_builtin += 1
            else:
                col_descs.append(scd)
        if num_builtin == len(self.tbl_desc.row_desc.col_descs):
            self.row_desc = self.tbl_desc.row_desc
        else:
            self.row_desc = RowDesc(col_descs)
        self.sorter = Sorter.from_state(
            state['sorter'], self.row_desc.col_descs + self.tbl_desc.row_desc.col_descs)
        pass

    @classmethod
    def from_names(cls, tbl_db_name, col_db_names):
        tbl_desc = TblDesc.lookup_tbl_desc(tbl_db_name)
        col_descs = []
        for col_db_name in col_db_names:
            cd = tbl_desc.lookup_col_desc(col_db_name)
            col_descs.append(cd)
        return TblQuery(tbl_desc, RowDesc(col_descs))

    def add_col(self, col_desc: ColDesc, idx: int = -1):
        pass

    def del_col(self, idx: int):
        pass

    def move_col(self, fro: int, to: int):
        pass

    def missing_key_col_descs(self):
        ''' Return a list of any key fields not in the query's RowDesc '''
        missing_key_col_descs = []
        for key_col_desc in self.sorter.row_desc.col_descs:
            try:
                self.row_desc.col_descs.index(key_col_desc)
            except ValueError:  # WTF: not KeyError!
                missing_key_col_descs.append(key_col_desc)
        return missing_key_col_descs

    def set_sorter(self, sorter: Sorter = None):
        self.db_query = None  # invalidate the compiled database query
        self.sorter = copy.copy(sorter if sorter is not None else self.tbl_desc.sorter)

    def set_filter(self, filter):
        self.db_query = None  # invalidate the compiled database query

    def get_db_query(self, session):
        if self.db_query is None:
            cols = []
            self.debug = []
            join_set = set()    # Set of Tuples
            for cd in self.row_desc.col_descs:
                try:
                    if isinstance(cd, DataColDesc) or isinstance(cd, LinkColDesc):
                        self.debug.append(
                            ('plain-getattr', self.tbl_desc.db_tbl_cls.__name__, cd.db_name)
                        )
                        cols.append(getattr(self.tbl_desc.db_tbl_cls, cd.db_name).label(cd.db_name))
                    elif isinstance(cd, ShortcutCD):
                        join_list = []  # List of (child TD, parent/ref CD db_name, parent/ref TD)
                        td1 = self.tbl_desc
                        x = 0
                        for pcd in cd.path_cds:
                            if x == len(cd.path_cds) - 1:
                                t1_name = td1.db_tbl_cls.__name__ + '_' + str(x + 1)
                                t1_alias = aliased(td1.db_tbl_cls, name=t1_name)
                                self.debug.append(
                                    ('alias-getattr', td1.db_tbl_cls.__name__, t1_name, cd.db_name)
                                )
                                cols.append(getattr(t1_alias, pcd.db_name).label(cd.db_name))
                            else:
                                td2 = pcd.foreign_td
                                self.debug.append(
                                    ('join', td1.db_tbl_cls.__name__, pcd.db_name, td2.db_tbl_cls.__name__)
                                )
                                join_list.append((td1, pcd.db_name, td2))
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
                for join in join_set:
                    join_chain = []
                    for join_step in join:
                        join_chain.append(join_step[2].db_tbl_cls)
                    pass  # q = q.join(*join_chain)
                for sc in self.sorter.cols:
                    order_attr = getattr(self.tbl_desc.db_tbl_cls, sc.col_desc.db_name)
                    if sc.descending:
                        order_attr = order_attr.desc()
                    q = q.order_by(order_attr)
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

from db import open_file_db
from tbl_desc import DbFolder_td, DbImage_td
import jsonpickle
from base_path import dev_base_ie_source_path

if __name__ == '__main__':
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    TblDesc.complete_tbl_descs()
    q_folder = TblQuery.from_names('DbFolder', ['date', 'name', 'id'])
    r = repr(q_folder)
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
    print('hay')
    pass