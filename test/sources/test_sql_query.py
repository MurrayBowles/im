''' test SQL queries '''

import pytest

from sql_query import SqlQuery
from sql_util import JoinState

from tbl_desc import TblDesc
import tbl_descs
TblDesc.complete_tbl_descs()

def test_queries():

    def check(q, exp_sql):
        sql = str(q)
        if sql != exp_sql:
            assert sql == exp_sql

    td = TblDesc.lookup_tbl_desc('DbFolder')
    check(SqlQuery.from_names(td, 'count'),
        'SELECT COUNT(*) FROM db_folder')
    check(SqlQuery.from_names(td, ['date2', 'name', 'id']),
        'SELECT db_folder.date2_year AS date2_year, db_folder.date2_month AS date2_month, '
        + 'db_folder.date2_day AS date2_day, item_0.name AS name, '
        + 'db_folder.id AS id FROM db_folder JOIN item AS item_0 ON db_folder.id == item_0.id'),
    check(SqlQuery.from_names(td, ['date2', 'name', 'id'], sorter=td.sorter),
        'SELECT db_folder.date2_year AS date2_year, db_folder.date2_month AS date2_month, '
        + 'db_folder.date2_day AS date2_day, item_0.name AS name, db_folder.id AS id '
        + 'FROM db_folder JOIN item AS item_0 ON db_folder.id == item_0.id '
        + 'ORDER BY date2_year DESC, date2_month DESC, date2_day DESC, name')
