""" test tag.py and db.py tag operations """

import pytest

from db import *
from test_db import _mk_date, _mk_name

def test_tags():
    folder = DbFolder.add(session, _mk_date(), _mk_name('folder'))
    tag = DbTag.add(session, _mk_name('tag'))

    folder.mod_tag_flags(session, tag, add_flags=TagFlags.DIRECT)
    tags = folder.get_tags(session)
    assert len(tags) == 1
    assert tags[0].flags == TagFlags.DIRECT

    folder.mod_tag_flags(session, tag, add_flags=TagFlags.EXTERNAL)
    tags = folder.get_tags(session)
    assert len(tags) == 1
    assert tags[0].flags == TagFlags.DIRECT | TagFlags.EXTERNAL

    folder.mod_tag_flags(session, tag, del_flags=TagFlags.DIRECT)
    tags = folder.get_tags(session)
    assert len(tags) == 1
    assert tags[0].flags == TagFlags.EXTERNAL

    folder.mod_tag_flags(session, tag, del_flags=TagFlags.EXTERNAL)
    tags = folder.get_tags(session)
    assert len(tags) == 0
