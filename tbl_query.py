''' database access interface '''

import copy
from typing import List, Optional

from sqlalchemy.orm import aliased, with_polymorphic

from col_desc import ColDesc, DataColDesc, LinkColDesc, ShortcutCD, CDXState
from db import DbFolder, DbImage
from filter import Filter
from row_buf import RowBuf
from row_desc import RowDesc
from sorter import Sorter
from sql_query import SqlQuery
from sql_util import JoinState
from tbl_desc import TblDesc
import tbl_descs


class TblQuery(object):

    tbl_desc: TblDesc
    row_desc: RowDesc
    filter: Optional[Filter]
    sorter: Sorter
    sql_query: SqlQuery     # set by self.get_sql_query(), get_rows()

    def __init__(
        self, tbl_desc: TblDesc, row_desc: RowDesc, filter: Filter = None, sorter: Sorter = None
    ):
        self.tbl_desc = tbl_desc
        self.row_desc = row_desc
        self.set_filter(filter)
        self.set_sorter(sorter)
        self.sql_query = None

    def __repr__(self):
        return 'TblQuery(%r, %r, %r, %r)' % (
            self.tbl_desc, self.row_desc, self.filter, self.sorter)

    def menu_text(self):
        return self.tbl_desc.menu_text()

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
            'sorter': self.sorter.get_state(),
            'filter': self.filter.get_state()
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
        col_descs2 = self.row_desc.col_descs + self.tbl_desc.row_desc.col_descs
        self.sorter = Sorter.from_state(state['sorter'], col_descs2)
        self.filter = Filter.from_state(state['filter'], col_descs2)
        pass

    @classmethod
    def from_names(cls, tbl_db_name: str, col_db_names: List[str], **kwargs):
        tbl_desc = TblDesc.lookup_tbl_desc(tbl_db_name)
        col_descs = []
        for col_db_name in col_db_names:
            cd = tbl_desc.lookup_col_desc(col_db_name)
            col_descs.append(cd)
        return TblQuery(tbl_desc, RowDesc(col_descs), **kwargs)

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
            missing_key_col_descs.append(key_col_desc)
        return missing_key_col_descs

    def set_sorter(self, sorter: Sorter = None):
        self.sql_query = None
        self.sorter = copy.copy(sorter if sorter is not None else self.tbl_desc.sorter)

    def set_filter(self, filter: Filter):
        self.sql_query = None
        self.filter = filter

    def get_sql_query(self):
        if self.sql_query is None:
            self.sql_query = SqlQuery(
                self.tbl_desc, self.row_desc, filter=self.filter, sorter=self.sorter)
        return self.sql_query

    def get_rows(self, session, limit=None, skip=0) -> List[RowBuf]:
        if self.sql_query is None:
            self.sql_query = SqlQuery(
                self.tbl_desc, self.row_desc, filter=self.filter, sorter=self.sorter)
        try:
            row_bufs = []
            q = str(self.sql_query)
            if limit is not None:
                q += ' LIMIT %u' % limit
            if skip != 0:
                if limit is None:
                    q += ' LIMIT -1'  # SQLite won't do OFFSET without LIMIT
                q += ' OFFSET %u' % skip
            db_rows = session.execute(q)
            join_state = self.sql_query.join_state
            row_bufs = []
            for dbr in db_rows:
                cols = []
                for cd in self.sql_query.cli_select.col_descs:
                    try:
                        col = cd.get_val(
                            lambda col_name: dbr[join_state.select_cols[col_name][0]],
                            CDXState())
                    except Exception as ed:
                        print('hi')
                    cols.append(col)
                row_bufs.append(RowBuf(cols))
            return row_bufs
        except Exception as ed:
            print('hey')
            pass

    def get_num_rows(self, session) -> int:
        sql_query = SqlQuery(self.tbl_desc, 'count')
        q = str(sql_query)
        try:
            num_rows = session.execute(q).scalar()
        except Exception as ed:
            print('hey')
        return num_rows

    def get_index(self, session, key: RowBuf) -> int:
        def get_tup(scs, cvs):
            if len(scs) > 1:
                high = get_tup(scs[0:1], cvs[0:1])
                low = get_tup(scs[1:], cvs[1:])
                return ('|', high,
                        ('&', ('==', scs[0].col_desc, cvs[0]), low))
            else:
                rel = '>' if scs[0].descending else '<'
                return (rel, scs[0].col_desc, cvs[0])
        filter_tup = get_tup(self.tbl_desc.sorter.cols, key.cols)
        filter = Filter(filter_tup)
        sql_query = SqlQuery(self.tbl_desc, 'count', filter=filter)
        try:
            idx = session.execute(str(sql_query)).scalar()
        except Exception as ed:
            print('hey')
        return idx

if __name__ == '__main__':
    from db import open_file_db
    import jsonpickle
    from base_path import dev_base_ie_source_path

    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    TblDesc.complete_tbl_descs()
    q_folder = TblQuery.from_names('DbFolder', ['date', 'name', 'id'])
    sql_folder = q_folder.get_sql_query()
    r = repr(q_folder)
    r_folder = q_folder.get_rows(session)
    q_image = TblQuery.from_names('DbImage', ['name', 'folder_id', 'folder_name'])
    filter = Filter(('>', q_image.row_desc.col_descs[2], 'm'))
    q_image.set_filter(filter)
    sql_image = q_image.get_sql_query()
    r_image = q_image.get_rows(session, skip=126, limit=10)
    r_raw_image = session.query(DbImage)[:]
    # FIXME: results from my, web; no results from main, corbett
    json = jsonpickle.encode(q_image)
    try:
        q_image2 = jsonpickle.decode(json)
    except Exception as ed:
        print('hi')
    num_folders = q_folder.get_num_rows(session)
    num_images = q_image.get_num_rows(session)
    q_folder_s = TblQuery.from_names('DbFolder', ['date', 'name'])
    folder_2_idx = q_folder.get_index(
        session,
        RowBuf([r_folder[2].cols[0], r_folder[2].cols[1]])
    )
    print('hay')
    pass