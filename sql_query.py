''' SQL query generator '''

from typing import List, Optional

from filter import Filter
from row_desc import RowDesc
from sorter import Sorter
from sql_util import JoinState
from tbl_desc import TblDesc


class SqlQuery(object):
    tbl_desc: TblDesc
    join_state: JoinState
    select: Optional[RowDesc]
    select_str: str
    filter: Optional[Filter]
    where_str: str
    sorter: Optional[Sorter]
    order_str: str
    query_str: str

    def __init__(self, tbl_desc: TblDesc, select, filter: Filter = None, sorter: Sorter= None):
        self.tbl_desc = tbl_desc
        self.join_state = JoinState(tbl_desc)
        if select == 'count':
            self.select = RowDesc([tbl_desc.lookup_col_desc('id')])
            # self.select_str = 'SELECT COUNT(%s.id)' % tbl_desc.sql_name()
            self.select_str = 'SELECT COUNT(*)'
        else:
            self.select = select
            cols = [self.join_state.sql_col_ref(cd, alias=True) for cd in self.select.col_descs]
            self.select_str = 'SELECT ' + ', '.join(cols)
        self.filter = filter
        if filter is not None:
            self.where_str = ' ' + filter.sql_str(self.join_state)
        else:
            self.where_str = ''
        self.sorter = sorter
        if sorter is not None:
            sort_cols = []
            for sc in sorter.cols:
                sort_col = self.join_state.sql_col_ref(sc.col_desc, row_desc=self.select)
                if sc.descending:
                    sort_col += ' DESC'
                sort_cols.append(sort_col)
            self.order_str = ' ORDER BY ' + ', '.join(sort_cols)
        else:
            self.order_str = ''
        self.query_str = self.select_str
        self.query_str += ' FROM ' + self.tbl_desc.sql_name()
        for join in self.join_state.sql_strs:
            self.query_str += ' ' + join
        self.query_str += self.where_str
        self.query_str += self.order_str
        pass

    @staticmethod
    def from_names(tbl_desc: TblDesc, select_names, **kwargs):
        if select_names == 'count':
            select = select_names
        else:
            col_descs = []
            for col_db_name in select_names:
                cd = tbl_desc.lookup_col_desc(col_db_name)
                col_descs.append(cd)
            select = RowDesc(col_descs)
        return SqlQuery(tbl_desc, select=select, **kwargs)

    def __str__(self):
        return self.query_str

if __name__ == '__main__':
    import tbl_descs
    TblDesc.complete_tbl_descs()
    td = TblDesc.lookup_tbl_desc('DbFolder')
    q_count = SqlQuery.from_names(td, 'count')
    s_count = str(q_count)
    q_unsorted = SqlQuery.from_names(td, ['date', 'name', 'id'])
    s_unsorted = str(q_unsorted)
    q_sorted = SqlQuery.from_names(td, ['date', 'name', 'id'], sorter=td.sorter)
    s_sorted = str(q_sorted)
    pass
