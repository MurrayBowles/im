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

    def has_col_desc(self, col_desc):
        # Python is so compact and clutter-free!
        try:
            self.row_desc.col_descs.index(col_desc)
            return True
        except ValueError:  # WTF: not KeyError!
            return False

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

    @staticmethod
    def _register_join_chain(join_chains, join_chain):
        ''' Return idx, l: a join_chains index, the length of the match.
        cases:
            1. join_chain exactly matches (a prefix of a) a list in join_chains, l == len(join_chain)
            2. a list in join_chains matches a prefix of join_chain, l == the length of the prefix
            3. no match: idx is the index of a new empty list added to join_chains, l == 0
        '''
        arg_len = len(join_chain)
        jcx = 0
        for jc in join_chains:
            check_len = len(jc)
            min_len = min(arg_len, check_len)
            try:
                for x in range(0, min_len):
                    if(jc[x] is not join_chain[x]):
                        raise ValueError
            except ValueError:
                jcx += 1
                continue
            if check_len >= arg_len:
                # case 1: join_chain matches join_chains[jcx]
                return jcx, arg_len
            else:
                # case 2: join_chain extends join_chains[jcx]
                join_chains[jcx].extend(join_chain[min_len:])
            return jcx, check_len
        # case 3: join_chain matches nothing in join_chains
        join_chains.append(join_chain)
        return jcx, 0

    def _add_chain_joins(self, joins, join_chains, join_chain):
        ''' Add joins for join_chain to joins[], and return the target-table SQL name '''
        jcx, num_match = TblQuery._register_join_chain(join_chains, join_chain)
        jcx_str = str(jcx)
        if num_match == 0:
            td1 = self.tbl_desc
            td1_name = td1.sql_name()
        else:
            td1 = join_chain[num_match - 1].foreign_td
            td1_name = td1.sql_name(jcx_str)
        for x in range(num_match, len(join_chain)):
            pcd = join_chain[x]
            td2 = pcd.foreign_td
            join_str = 'JOIN %s AS %s ON %s.%s == %s.id' % (
                td2.sql_name(),
                td2.sql_name(jcx_str),
                td1_name,
                pcd.db_name,
                td2.sql_name(jcx_str)
            )
            joins.append(join_str)
            td1 = td2
            td1_name = td1.sql_name(jcx_str)
        return td1_name

    def get_sql_query(self):
        if self.sql_query is not None:
            return self.sql_query
        self.debug = []
        cols = []
        joins = []
        join_chains = []
        for cd in self.row_desc.col_descs:
            if isinstance(cd, DataColDesc) or isinstance(cd, LinkColDesc):
                self.debug.append(
                    ('plain-getattr', self.tbl_desc.sql_name(), cd.db_name)
                )
                cols.append('%s.%s AS %s' % (
                    self.tbl_desc.sql_name(), cd.db_name, cd.db_name))
            elif isinstance(cd, ShortcutCD):
                target_sql_name = self._add_chain_joins(
                    joins, join_chains, cd.path_cds[0:-1])
                cols.append('%s.%s AS %s' % (
                    target_sql_name, cd.path_cds[-1].db_name, cd.db_name))
            else:
                raise ValueError('%s has unsupported type' % (cd.db_name))
        self.sql_query = 'SELECT ' + ', '.join(cols)
        self.sql_query += ' FROM ' + self.tbl_desc.sql_name()
        for join in joins:
            self.sql_query += ' ' + join
        if len(self.sorter.cols) != 0:
            sort_strs = []
            for sc in self.sorter.cols:
                cd = sc.col_desc
                if self.has_col_desc(cd):
                    sort_str = cd.db_name
                elif isinstance(cd, DataColDesc) or isinstance(cd, LinkColDesc):
                    sort_str = '%s.%s' % (self.tbl_desc.sql_name(), cd.db_name)
                elif isinstance(cd, ShortcutCD):
                    target_sql_name = self._add_chain_joins(
                        joins, join_chains, cd.path_cds[0:-1])
                    sort_str = '%s.%s' % (target_sql_name, cd.path_cds[-1].db_name)
                else:
                    raise ValueError('%s has unsupported type' % (cd.db_name))
                if sc.descending:
                    sort_str += ' DESC'
                sort_strs.append(sort_str)
            self.sql_query += ' ORDER BY ' + ', '.join(sort_strs)
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
    print('hay')
    pass