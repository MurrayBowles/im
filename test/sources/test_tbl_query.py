''' test database access interface '''

import jsonpickle
import pytest

from base_path import dev_base_ie_source_path
from db import open_file_db

from tbl_desc import TblDesc
import tbl_descs
TblDesc.complete_tbl_descs()

from filter import Filter
from imdate import IMDate
from row_buf import RowBuf
from tbl_query import TblQuery

def test_pickle():
    original = TblQuery.from_names('DbImage', ['name', 'folder_id', 'folder_name'])
    filter = Filter(('==', original.row_desc.col_descs[0], 'xxx'))
    original.set_filter(filter)
    saved = jsonpickle.encode(original)
    restored = jsonpickle.decode(saved)
    assert restored.tbl_desc == original.tbl_desc
    assert restored.row_desc.col_descs == original.row_desc.col_descs
    assert restored.sorter.row_desc.col_descs == original.sorter.row_desc.col_descs
    for rsc, osc in zip(restored.sorter.cols, original.sorter.cols):
        assert rsc.col_desc == osc.col_desc
        assert rsc.descending == osc.descending
    assert restored.filter.tup == original.filter.tup
    pass

def test_access():
    session = open_file_db(dev_base_ie_source_path + '\\test.db', 'r')
    q_folder = TblQuery.from_names('DbFolder', ['date2', 'name'])
    r_folder = q_folder.get_rows(session, limit=4, skip=1)
    exp_r_folder = [
        RowBuf(cols=[IMDate(2017, 10, 7), 'virginia']),
        RowBuf(cols=[IMDate(2017, 9, 24), 'empire seven']),
        RowBuf(cols=[IMDate(2017, 9, 23), 'diana']),
        RowBuf(cols=[IMDate(2017, 9, 22), 'caravan'])
    ]
    assert len(r_folder) == 4
    assert r_folder == exp_r_folder
    q_image = TblQuery.from_names('DbImage', ['name', 'folder_name'])
    r_image = q_image.get_rows(session, skip=100, limit=4)
    exp_r_image = [
        RowBuf(cols=['9135', 'virginia']),
        RowBuf(cols=['9139', 'virginia']),
        RowBuf(cols=['9140', 'virginia']),
        RowBuf(cols=['9141', 'virginia'])
    ]
    assert len(r_image) == 4
    assert r_image == exp_r_image
    num_folders = q_folder.get_num_rows(session)
    assert num_folders == 58
    folder_2_idx = q_folder.get_index(
        session,
        RowBuf([r_folder[2].cols[0], r_folder[2].cols[1]])
    )
    assert folder_2_idx == (2 + 1)  # we did a skip=1 to get r_folder
    pass