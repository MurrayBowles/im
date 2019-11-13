''' test row buffer '''

import pytest

from row_buf import RowBuf
from col_desc import TextCD
from row_desc import RowDesc

def test_extract():
    a_cd = TextCD('a', 'A')
    b_cd = TextCD('b', 'B')
    c_cd = TextCD('c', 'C')
    rd = RowDesc([a_cd, b_cd, c_cd])
    rb = RowBuf(['alpha', 'beta', 'gamma'])

    e_ab = rb.extract(rd, RowDesc([a_cd, b_cd]))
    assert e_ab.cols[0] == rb.cols[0]
    assert e_ab.cols[1] == rb.cols[1]

    e_ba = rb.extract(rd, RowDesc([b_cd, a_cd]))
    assert e_ba.cols[0] == rb.cols[1]
    assert e_ba.cols[1] == rb.cols[0]

    e_none = rb.extract(rd, RowDesc([]))
    assert len(e_none.cols) == 0

    e_all = rb.extract(rd, rd)
    assert len(e_all.cols) == len(rb.cols)
    for x,y in zip(e_all.cols, rb.cols):
        assert x == y



