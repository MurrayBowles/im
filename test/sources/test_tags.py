""" test tags.py, and db.py tag operations """

import pytest

from db import *
from test_db import _mk_date, _mk_name

def test_tags():
    session = open_mem_db()

    db_folder = DbFolder.add(session, _mk_date(), _mk_name('db_folder'))
    db_tag = DbTag.add(session, _mk_name('db_tag'))

    db_folder.mod_tag_flags(session, db_tag, add_flags=TagFlags.DIRECT)
    item_tags = db_folder.get_tags(session)
    assert len(item_tags) == 1
    assert item_tags[0].flags == TagFlags.DIRECT

    db_folder.mod_tag_flags(session, db_tag, add_flags=TagFlags.EXTERNAL)
    item_tags = db_folder.get_tags(session)
    assert len(item_tags) == 1
    assert item_tags[0].flags == TagFlags.DIRECT | TagFlags.EXTERNAL

    db_folder.mod_tag_flags(session, db_tag, del_flags=TagFlags.DIRECT)
    item_tags = db_folder.get_tags(session)
    assert len(item_tags) == 1
    assert item_tags[0].flags == TagFlags.EXTERNAL

    db_folder.mod_tag_flags(session, db_tag, del_flags=TagFlags.EXTERNAL)
    item_tags = db_folder.get_tags(session)
    assert len(item_tags) == 0

tag_source_data = [
    (   'global', [
        ('b',),
        ('shadow', 'global-shadowed'),
        ('global-unique',)
    ]),
    (   'local', [
        ('a b',),
        ('b c',),
        ('shadow', 'local-shadow'),
        ('local-unique',)
    ])
]
# source-data: ( source-description-string, mapping-data-list )
# mapping-data: ( text, [ db-tag-text ] )

def test_tag_mappings():
    session = open_mem_db()

    def db_tag_text(tmd):
        return tmd[1] if len(tmd) >= 2 else tmd[0]

    db_tags = {}
    dts = set()
    for tsd in tag_source_data:
        for tmd in tsd[1]:
            dtt = db_tag_text(tmd)
            if dtt not in db_tags:
                dt = DbTag.add(session, dtt)
                db_tags[dtt] = dt
                dts.add(dt)
    pass

    tag_sources = {}
    for tsd in tag_source_data:
        ts = FsTagSource.add(session, description=tsd[0])
        tag_sources[tsd[0]] = ts
        for tmd in tsd[1]:
            dtt = db_tag_text(tmd)
            dt = db_tags[dtt]
            assert dt is not None
            tm = FsTagMapping.add(session, ts, tmd[0], FsTagBinding.BOUND, dt)
            assert tm is not None
        mappings = ts.mappings(session)
        assert len(mappings) == len(tsd[1])
        smd = sorted(tsd[1], key=lambda x: x[0])
        sm = sorted(mappings, key=lambda x: x.text)
        for md,m in zip(smd,sm):
            assert md[0] == m.text
        pass

    pass