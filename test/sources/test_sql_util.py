''' test SQL utilities '''

import pytest

from sql_util import JoinState

from tbl_desc import TblDesc
import tbl_descs
TblDesc.complete_tbl_descs()

def test_join_state():

    def get_col_refs(td: TblDesc):
        js = JoinState(td)
        col_ref_fn = js.sql_col_ref_fn(select=True)
        for cd in td.row_desc.col_descs:
            cd.sql_select(col_ref_fn)
        return js.select_strs, js.sql_strs

    def check(td: TblDesc, exp_col_refs, exp_join_strs):
        col_refs, join_strs = get_col_refs(td)
        for exp_col_ref, col_ref in zip(exp_col_refs, col_refs):
            if col_ref != exp_col_ref:
                assert col_ref == exp_col_ref
        for exp_join_str, join_str in zip(exp_join_strs, join_strs):
            if join_str != exp_join_str:
                assert join_str == exp_join_str

    DbFolder_td = TblDesc.lookup_tbl_desc('DbFolder')
    check(DbFolder_td,
        ['db_folder.id AS id', 'item_0.name AS name', 'item_0.type AS type', 'db_folder.date AS date',
            'db_folder.date2_year AS date2_year', 'db_folder.date2_month AS date2_month',
            'db_folder.date2_day AS date2_day'],
        ['JOIN item AS item_0 ON db_folder.id == item_0.id'])
    DbImage_td = TblDesc.lookup_tbl_desc('DbImage')
    check(DbImage_td,
        ['db_image.id AS id', 'item_0.name AS name', 'item_0.type AS type',
            'db_image.folder_id AS folder_id', 'db_folder_1.date AS folder_date', 'item_1.name AS folder_name'],
        ['JOIN item AS item_0 ON db_image.id == item_0.id',
            'JOIN db_folder AS db_folder_1 ON db_image.folder_id == db_folder_1.id',
            'JOIN item AS item_1 ON db_folder_1.id == item_1.id'])
