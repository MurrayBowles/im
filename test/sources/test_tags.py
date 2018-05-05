""" test tags.py, and db.py tag operations """

import pytest

import check_tags
from db import *
from test_db import _mk_date, _mk_name


def test_tags():
    session = open_mem_db()
    ctx = check_tags.Ctx(session)

    ops = [
        ('+db-folder', 'db_folder'),
        ('+tag', ('t', ' db_tag')),

        ('!db-folder-tag', [('db_folder', [('+d', 't')])]),
        ('?db-folder-tag', [('db_folder', [('=d', 't')])]),

        ('!db-folder-tag', [('db_folder', [('+e', 't')])]),
        ('?db-folder-tag', [('db_folder', [('=de', 't')])]),

        ('!db-folder-tag', [('db_folder', [('-e', 't')])]),
        ('?db-folder-tag', [('db_folder', [('=d', 't')])]),

        ('!db-folder-tag', [('db_folder', [('-d', 't')])]),
        ('?db-folder-tag', [('db_folder', [('0', 't')])])
    ]
    ctx.execute(ops)
    pass


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


def test_tag_mappings2():
    ops = [
        ('+tag', [
            'global-shadowed', 'global-unique',
            'local-shadow', 'local-unique',
            'a b', 'b', 'b c'
        ]),
        ('+mapping', [
            ('bg', 'b', 'b'),
            ('bg', 'shadow', 'global-shadowed'),
            ('bg', 'global-unique', 'global-unique')
        ]),
        ('+mapping', [
            ('bl', 'a b', 'a b'),
            ('bl', 'b c', 'b c'),
            ('bl', 'shadow', 'local-shadow'),
            ('bl', 'local-unique', 'local-unique')
        ])
    ]
    session = open_mem_db()
    ctx = check_tags.Ctx(session)
    ctx.execute(ops)
    pass


def test_check_tags():
    session = open_mem_db()
    ctx = check_tags.Ctx(session)
    ctx.execute([
        ('+tag', [
            ('scythe', 'band|Scythe'),
            ('repunk', 'venue|Repunknante'),
            ('nt', 'band|Neglected Truth'),
            ('dys', 'band|Dysphoric')
        ]),
        ('+mapping', [
            ('bg', 'band|Neglected Truth', 'nt'),
            ('bl', 'band|Dysphoric', 'dys')
        ])
    ])
    pass

def test_check_ie_folder():
    session = open_mem_db()
    ctx = check_tags.Ctx(session)
    ie_folder_spec = (
        'ie-folder', '', [
            ('w', 'word1'),
            ('w', 'word2'),
            ('u', 'cool|shot')
        ], 'band', [
            ('image1', [
                ('b', 'grimple')
            ]),
            ('image2', [
                ('w', 'op'),
                ('w', 'ivy')
            ])
        ])
    ctx.execute([
        ('!fs-source', ('d', 'e:', '/photos')),
        ('+fs-folder', ('fs-folder', ['image1', 'image2'])),
        ('+ie-folder', [ie_folder_spec]),
        ('?ie-folder', [ie_folder_spec]),
        ('init-fs-folder-tags', ('fs-folder', 'ie-folder')),
        ('check-fs-folder-tags', [
            ('fs-folder', [
                ('wun', ['word1']),
                ('wun', ['word2']),
                ('tun', 'cool|shot')
            ], [
                ('image1', [
                    ('tun', 'grimple')
                ]),
                ('image2', [
                    ('wun', ['op']),
                    ('wun', ['ivy'])
                ])
            ])
        ])
    ])
    pass