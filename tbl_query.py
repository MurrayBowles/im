''' database access interface '''

import copy
from typing import List, Optional

from sqlalchemy.orm import aliased, with_polymorphic

from col_desc import ColDesc, DataColDesc, LinkColDesc, ShortcutCD
from db import DbFolder, DbImage
from row_buf import RowBuf
from row_desc import RowDesc
from sorter import Sorter
from sql_util import JoinState
from tbl_desc import TblDesc
import tbl_descs


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
        self.sql_query = None
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
            missing_key_col_descs.append(key_col_desc)
        return missing_key_col_descs

    def set_sorter(self, sorter: Sorter = None):
        self.sql_query = None
        self.db_query = None  # invalidate the compiled database query
        self.sorter = copy.copy(sorter if sorter is not None else self.tbl_desc.sorter)

    def set_filter(self, filter):
        self.sql_query = None
        self.db_query = None  # invalidate the compiled database query

    def _finish_sql_query(self, sql_query, join_state, row_desc:RowDesc=RowDesc([]), sorter=None):
        sort_strs = []
        if sorter is not None:
            for sc in self.sorter.cols:
                sort_str = join_state.sql_col_ref(sc.col_desc, row_desc=row_desc)
                if sc.descending:
                    sort_str += ' DESC'
                sort_strs.append(sort_str)
        for join in join_state.sql_strs:
            sql_query += ' ' + join
        if len(sort_strs) != 0:
            sql_query += ' ORDER BY ' + ', '.join(sort_strs)
        return sql_query

    def get_sql_query(self):
        if self.sql_query is not None:
            return self.sql_query
        cols = []
        join_state = JoinState(self.tbl_desc)
        for cd in self.row_desc.col_descs:
            cols.append(join_state.sql_col_ref(cd, alias=True))
        self.sql_query = 'SELECT ' + ', '.join(cols)
        self.sql_query += ' FROM ' + self.tbl_desc.sql_name()
        self.sql_query = self._finish_sql_query(
            self.sql_query, join_state, self.row_desc, self.sorter)
        return self.sql_query

    def get_rows(self, session, limit=None, skip=0) -> List[RowBuf]:
        if self.sql_query is None:
            self.get_sql_query()
        try:
            row_bufs = []
            q = self.sql_query
            if limit is not None:
                q += ' LIMIT %u' % limit
            if skip != 0:
                if limit is None:
                    q += ' LIMIT -1'  # SQLite won't do OFFSET without LIMIT
                q += ' OFFSET %u' % skip
            db_rows = session.execute(q)
            row_bufs = [RowBuf([dbc for dbc in dbr]) for dbr in db_rows]
            return row_bufs
        except Exception as ed:
            print('hey')
            pass

    def get_num_rows(self, session) -> int:
        tbl_name = self.tbl_desc.sql_name()
        sql_query = 'SELECT COUNT(%s.id) FROM %s' % (tbl_name, tbl_name)
        sql_query = self._finish_sql_query(sql_query, JoinState(self.tbl_desc))
        try:
            num_rows = session.execute(sql_query).scalar()
        except Exception as ed:
            print('hey')
        return num_rows

    def get_index(self, session, key_desc: RowDesc, key: RowBuf) -> int:
        tbl_name = self.tbl_desc.sql_name()
        sql_query = 'SELECT COUNT(%s.id) FROM %s' % (tbl_name, tbl_name)
        join_state = JoinState(self.tbl_desc)
        conditions = []
        for cd, cv in zip(key_desc.col_descs, key.cols):
            condition = join_state.add_col_ref(cd) + ' < %s' % cv
            conditions.append(condition)
        sql_query += ' WHERE ' +  ' AND '.join(conditions)
        sql_query = self._finish_sql_query(
            sql_query, join_state, sorter=self.sorter)
        try:
            idx = session.execute(sql_query).scalar()
        except Exception as ed:
            print('hey')
        return idx

from db import open_file_db
import jsonpickle
from base_path import dev_base_ie_source_path

if __name__ == '__main__':
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    TblDesc.complete_tbl_descs()
    q_folder = TblQuery.from_names('DbFolder', ['date', 'name', 'id'])
    sql_folder = q_folder.get_sql_query()
    r = repr(q_folder)
    r_folder = q_folder.get_rows(session, skip=1)
    q_image = TblQuery.from_names('DbImage', ['name', 'folder_id', 'folder_name'])
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
    '''
    folder_2_idx = q_folder.get_index(
        session,
        RowDesc([q_folder.row_desc.col_descs[2]]),
        RowBuf([3242])
    )
    '''
    print('hay')
    pass