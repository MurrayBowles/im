''' test sorter '''

import pytest

from col_desc import TextCD
from sorter import Sorter, SorterCol

def test_pickle():
    a_cd = TextCD('a', 'A')
    a_sc = SorterCol(a_cd, False)
    b_cd = TextCD('b', 'B')
    b_sc = SorterCol(b_cd, True)
    col_descs = [a_cd, b_cd]
    sorter_cols = [a_sc, b_sc]
    original = Sorter(sorter_cols)
    saved = original.get_state()
    assert saved == ['+a', '-b']
    restored = Sorter.from_state(saved, col_descs)
    assert restored == original
