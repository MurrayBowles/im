""" test ie_db (import/export folders/images to/from the database) """

from collections import deque
import os
import pytest

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

import check_tags
from db import *
#session = open_mem_db()

from ie_cfg import IECfg
from ie_db import *
from test_ie_fs import test_scan_dir_set_expected_list
from test_ie_fs import test_scan_dir_sel_selected_list
from test_ie_fs import test_scan_dir_sel_expected_list
from test_ie_fs import test_scan_file_set_corbett_psds_expected_list
from test_ie_fs import test_scan_file_sel_corbett_psds_selected_list
from test_ie_fs import test_scan_file_sel_corbett_psds_expected_list
from test_ie_fs import test_scan_file_set_corbett_tiffs_expected_list
from test_ie_fs import test_scan_file_sel_corbett_tiffs_selected_list
from test_ie_fs import test_scan_file_sel_corbett_tiffs_expected_list
from mock_task import MockSlicer
from task import Task, TaskState
base_path = '\\users\\user\\PycharmProjects\\im\\test\\import-export sources'
# TODO: get PyCharm/pytest to provide this, up to the last directory

ie_cfg = IECfg()
ie_cfg.import_thumbnails = True

def check_images(fs_folder, ie_image_iter, image_expected_list):
    assert len(ie_image_iter) == len(image_expected_list)
    for ie_image, expected_image_str in zip(ie_image_iter, image_expected_list):
        if fs_folder.db_folder is not None:
            for ext in thumbnail_exts:
                if ext in ie_image.insts:
                    assert ie_image.thumbnail is not None
        exp_image, exp_exts = expected_image_str.split('-')
        if exp_exts[0] == 'X':
            if ie_image.tags is None:
                pass
            else:
                if len(ie_image.tags) > 0:
                    pass
                else:
                    pass
            # FIXME: Heisenbug!
            # assert ie_image.tags is not None
    pass

def check_worklist_no_fs_folders(
        session, fs_source, import_mode, paths, expected_list):
    def pub_fn(msg, **kw):
        pass
    worklist = get_ie_worklist(session, fs_source, import_mode, paths)
    assert len(worklist) == len(expected_list)
    for work, expected in zip(worklist, expected_list):
        assert work.fs_folder is None
        assert fs_source.rel_path(work.ie_folder.fs_path) == expected[0]
    for work in worklist:
        fg_start_ie_work_item(session, ie_cfg, work, fs_source)
        bg_proc_ie_work_item(work, fs_source, pub_fn)
    for work, expected in zip(worklist, expected_list):
        assert work.fs_folder is not None
        check_images(
            work.fs_folder, work.ie_folder.images.values(), expected[1])
    pass

def check_worklist_with_fs_folders(
        session, fs_source, import_mode, paths, expected_list):
    fs_folders = []
    for expected in expected_list:
        fs_folder = FsFolder.get(session, fs_source, expected[0])[0]
        fs_folders.append(fs_folder)
    worklist = get_ie_worklist(session, fs_source, import_mode, paths)
    assert len(worklist) == len(expected_list)
    for work, expected, fs_folder in zip(
            worklist, expected_list, fs_folders):
        assert work.fs_folder is fs_folder
        assert fs_source.rel_path(work.ie_folder.fs_path) == expected[0]
        # session.expunge(fs_folder)

def test_get_workist_dir_set_my_dirs():
    session = open_mem_db()
    ie_cfg.import_mode = ImportMode.SET

    path = os.path.join(base_path, 'my format')
    fs_source = FsSource.add(
        session, 'c:', path, FsSourceType.DIR, readonly=True, tag_source=None)
    check_worklist_no_fs_folders(
        session, fs_source, ie_cfg.import_mode, [path],
        test_scan_dir_set_expected_list
    )
    check_worklist_with_fs_folders(
        session, fs_source, ie_cfg.import_mode, [path],
        test_scan_dir_set_expected_list
    )
    session.commit()

def test_get_workist_dir_sel_my_dirs():
    session = open_mem_db()
    ie_cfg.import_mode = ImportMode.SEL

    path = os.path.join(base_path, 'my format')
    fs_source = FsSource.add(
        session, 'c:', path, FsSourceType.DIR, readonly=True, tag_source=None)
    check_worklist_no_fs_folders(
        session, fs_source, ie_cfg.import_mode, test_scan_dir_sel_selected_list,
        test_scan_dir_sel_expected_list
    )
    fs_folders = []
    check_worklist_with_fs_folders(
        session, fs_source, ImportMode.SEL,
        test_scan_dir_sel_selected_list,
        test_scan_dir_sel_expected_list
    )
    session.commit()

def test_get_worklist_file_set_corbett_psds():
    session = open_mem_db()
    ie_cfg.import_mode = ImportMode.SET

    path = os.path.join(base_path, 'main1415 corbett psds')
    fs_source = FsSource.add(
        session, 'c:', path, FsSourceType.FILE, readonly=True, tag_source=None)
    check_worklist_no_fs_folders(
        session, fs_source, ie_cfg.import_mode, [path],
        test_scan_file_set_corbett_psds_expected_list
    )
    check_worklist_with_fs_folders(
        session, fs_source, ie_cfg.import_mode, [path],
        test_scan_file_set_corbett_psds_expected_list
    )
    session.commit()

def test_get_worklist_file_sel_corbett_psds():
    session = open_mem_db()
    ie_cfg.import_mode = ImportMode.SEL

    path = os.path.join(base_path, 'main1415 corbett psds')
    fs_source = FsSource.add(
        session, 'c:', path, FsSourceType.FILE, readonly=True, tag_source=None)
    check_worklist_no_fs_folders(
        session, fs_source, ie_cfg.import_mode,
        test_scan_file_sel_corbett_psds_selected_list,
        test_scan_file_sel_corbett_psds_expected_list
    )
    check_worklist_with_fs_folders(
        session, fs_source, ie_cfg.import_mode,
        test_scan_file_sel_corbett_psds_selected_list,
        test_scan_file_sel_corbett_psds_expected_list
    )
    session.commit()

def test_get_worklist_file_set_corbett_tiffs():
    session = open_mem_db()
    ie_cfg.import_mode = ImportMode.SET

    path = os.path.join(base_path, 'corbett drive')
    fs_source = FsSource.add(
        session, 'c:', path, FsSourceType.FILE, readonly=True, tag_source=None)
    check_worklist_no_fs_folders(
        session, fs_source, ie_cfg.import_mode, [path],
        test_scan_file_set_corbett_tiffs_expected_list
    )
    check_worklist_with_fs_folders(
        session, fs_source, ie_cfg.import_mode, [path],
        test_scan_file_set_corbett_tiffs_expected_list
    )
    session.commit()

def test_get_worklist_file_sel_corbett_tiffs():
    session = open_mem_db()
    ie_cfg.import_mode = ImportMode.SEL

    path = os.path.join(base_path, 'corbett drive')
    fs_source = FsSource.add(
        session, 'c:', path, FsSourceType.FILE, readonly=True, tag_source=None)
    check_worklist_no_fs_folders(
        session, fs_source, ie_cfg.import_mode,
        test_scan_file_sel_corbett_tiffs_selected_list,
        test_scan_file_sel_corbett_tiffs_expected_list
    )
    check_worklist_with_fs_folders(
        session, fs_source, ie_cfg.import_mode,
        test_scan_file_sel_corbett_tiffs_selected_list,
        test_scan_file_sel_corbett_tiffs_expected_list
    )
    session.commit()


def _check_item_tags(item_tags, tags, checks):
    for c in checks:

        def find_item_tag(text):
            for item_tag in item_tags:
                if item_tag.text.lower() == text.lower():
                    return item_tag
            else:
                assert False

        def check_item_tag(item_tag):
            type = FsTagType.WORD if c[0][0] == 'w' else FsTagType.TAG
            binding = {
                'u': FsTagBinding.UNBOUND,
                's': FsTagBinding.SUGGESTED,
                'b': FsTagBinding.BOUND
            }[c[0][1]]
            source = {
                'n': FsItemTagSource.NONE,
                't': FsItemTagSource.DBTAG,
                'g': FsItemTagSource.GLOBTS,
                'f': FsItemTagSource.FSTS
            }[c[0][2]]
            assert item_tag.type == type
            if item_tag.binding != binding:
                pass
            assert item_tag.binding == binding
            if item_tag.source != source:
                pass
            assert item_tag.source == source
            if binding != FsTagBinding.UNBOUND:
                if len(c) > 2:
                    if item_tag.db_tag is not tags[c[2]]:
                        pass
                    assert item_tag.db_tag is tags[c[2]]

        if c[0][0] == 't':
            item_tag = find_item_tag(c[1])
            check_item_tag(item_tag)
        else:  # w
            item_tag0 = find_item_tag(c[1][0])
            check_item_tag(item_tag0)
            for x in range(1, len(c[1])):
                item_tag = find_item_tag(c[1][x])
                assert item_tag.idx == item_tag0.idx + x
                assert item_tag.first_idx == item_tag0.idx
                check_item_tag(item_tag)


def _check_image(fs_image, tags, checks):
    _check_item_tags(fs_image.item_tags, tags, checks)


def _check_folder(fs_folder, tags, checks):
    _check_item_tags(fs_folder.item_tags, tags, checks)


def _test_cmd(volume, dir_name, source_type, cfg):
    session = open_mem_db()
    ctx = check_tags.Ctx(session)
    tag_source = ctx.get_tag_source('l')

    if source_type == FsSourceType.WEB:
        path = '//www.pbase.com/' + dir_name
        assert 'sel' not in cfg
        import_mode = ImportMode.SET
        paths = [path.replace('\\', '/')]
    else:
        path = os.path.join(base_path, dir_name)
        if 'sel' in cfg:
            import_mode = ImportMode.SEL
            paths = [util.path_plus_separator(path) + dir for dir in cfg['sel']]
        else:
            import_mode = ImportMode.SET
            paths = [path]

    ctx.run(('+tag', cfg['tags']))
    tags = ctx.tags
    all_tags = session.query(DbTag).all()

    ctx.run(('+mapping', cfg['mappings']))
    all_mappings = session.query(FsTagMapping).all()

    fs_source = FsSource.add(
        session, volume, path, source_type,
        readonly=True, tag_source=tag_source)

    slicer = MockSlicer(suspended=True)
    task = IETask2(
        slicer=slicer, session=session, ie_cfg=ie_cfg, fs_source=fs_source,
        import_mode=import_mode, paths=paths)
    task.start()
    slicer.resume()
    if task.state != TaskState.DONE:
        pass
    assert task.state == TaskState.DONE

    worklist = task.worklist
    session.commit()


    # check the FsItemTags in cfg['checks'], a list of
    # ('folder name', [item-tags]), where item-tag is one of
    #   ('t{usb}{ntgf}', 'tag-text', 'tag-var')(
    #   ('w{usb}{ntgf}', ['word',...], 'tag-var')
    # usb is Unbound | Suggested | Bound
    # ntgfd is None | dbTag | Globts | Fsts
    if 'checks' in cfg:
        for check in cfg['checks']:
            # find the folder (check[0]) in the results
            for wi in worklist:
                if wi.fs_folder.name == check[0]:
                    fs_folder = wi.fs_folder
                    _check_folder(fs_folder, tags, check[1])
                    break
            else:
                assert False

            if len(check) > 2:
                # check the images: check[2] is a list of
                # ('image-name', [item-tags])
                for ic in check[2]:
                    for fs_image in fs_folder.images:
                        if fs_image.name == ic[0]:
                            _check_image(fs_image, tags, ic[1])
                            break
                    else:
                        assert False


def test_my_cmd():
    cfg = {
        'tags': [
            ('scythe',  'band|Scythe'),
            ('repunk',  'venue|Repunknante'),
            ('nt',      'band|Neglected Truth'),
            ('dys',     'band|Dysphoric')
        ],
        'mappings': [
            ('bg',     'band|Neglected Truth', 'nt'),
            ('bf',     'band|Dysphoric',       'dys')
        ],
        'checks': [
            ('171007 virginia', [
                ('tun', 'Cult Mind'),
                ('tun', 'Repunknante'),
                ('tbt', 'Scythe', 'scythe'),
                ('tbg', 'Neglected Truth', 'nt'),
                ('tbf', 'Dysphoric', 'dys')
            ])
        ]
    }
    _test_cmd('c:', 'my format', FsSourceType.DIR, cfg)

def test_main_cmd():
    cfg = {
        'tags': [
            ('bk',      'band|Bikini Kill'),
            ('crimp',   'band|Crimpshrine'),
            ('15',      'band|Fifteen'),
            ('t8',      'band|Tribe 8'),
            ('jb',      'band|Jawbreaker'),
            ('jf',      'person|Jake Filth'),
            ('jo',      'person|Jeff Ott'),
            ('js',      'person|Jake Sales'),
            ('gilman',  'venue|Gilman')
        ],
        'mappings': [
            ('bf',     'band|Bikini Kill', 'bk'),
            ('bf',     'band|Fifteen', '15'),
            ('bf',     'band|Tribe 8', 't8'),
            ('bf',     'band|Jawbreaker', 'jb'),
            ('bg',     'venue|Gilman', 'gilman'),
            ('bf',     'JSALES', None),
            ('bf',     'meta', None)
        ],
        'checks': [
            ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', [
                ('wbf', ['bikini', 'kill'], 'bk'),
                ('wbg', ['gilman'], 'gilman')
            ]),
            ('FIFTEEN_TRIBE_8_JAWBREAKER_GILMAN_11_15&16_91-5605.psd', [
                ('wbf', ['fifteen'], '15'),
                ('wbf', ['tribe', '8'], 't8'),
                ('wbf', ['jawbreaker'], 'jb'),
                ('wbg', ['gilman'], 'gilman')
            ], [
                ('5605', [
                    ('tbt', 'crimpshrine', 'crimp'),
                    ('tbt', 'Jake Filth', 'jf'),
                    ('tbt', 'Jake Sales', 'js'),
                    ('tbt', 'Jeff Ott', 'jo')
                ]),
                ('5631', [])
            ])
        ]
    }
    _test_cmd('main1415', 'main1415 corbett psds', FsSourceType.FILE, cfg)

def test_corbett_cmd():
    cfg = {
        'tags': [
            ('nuisance', 'band|Nuisance'),
            ('mtx', 'band|the Mr T Experience'),
            ('sg', 'band|Soundgarden'),
            ('mh', 'band|Mudhoney'),
            ('phoenix', 'venue|Phoenix Ironworks'),
            ('gilman', 'venue|Gilman'),
            ('ib', 'venue|I-Beam')
        ],
        'mappings': [
            ('bg', 'venue|Gilman', 'gilman'),
            ('bf', 'venue|Phoenix', 'phoenix'),
            ('bf', 'venue|ibeam', 'ib'),
            ('bf', 'band|nuisance', 'nuisance'),
            ('bf', 'band|mtx', 'mtx'),
            ('bf', 'band|soundgarden', 'sg')
        ],
        'checks': [
            ('01_03_92_15_GILMAN-001.tif', [
                ('wbg', ['gilman'], 'gilman')
            ]),
            ('01_11_92_NUISANCE_MTX_PHOENIX-014.tif', [
                ('wbf', ['phoenix'], 'phoenix'),
                ('wbf', ['nuisance'], 'nuisance'),
                ('wbf', ['mtx'], 'mtx')
            ]),
            ('02_13&16_89_SOUNDGARDEN_MUDHONEY_IBEAM&BSQ-001.tif', [
                ('wbf', ['soundgarden'], 'sg')
            ])
        ]
    }
    _test_cmd('j:', 'corbett drive', FsSourceType.FILE, cfg)

def test_web_cmd():
    cfg = {
        'tags': [
            ('e7', 'venue|Empire Seven'),
            ('dys', 'band|Dysphoric'),
            ('ep', 'band|Empty People'),
            ('dp', 'band|Deadpressure'),
            ('cc', 'band|Capitalist Casualties')
        ],
        'mappings': [
            ('bg', 'venue|Empire Seven', 'e7'),
            ('bg', 'band|Dysphoric', 'dys'),
            ('bf', 'band|Empty People', 'ep'),
            ('bg', 'band|Deadpressure', 'dp')
        ],
        'checks': [
            ('170924_empire_seven', [
                ('tbg', 'empire seven', 'e7'),
                ('tbg', 'dysphoric', 'dys'),
                ('tbf', 'Empty People', 'ep')
            ])
        ]
    }
    _test_cmd('http:', 'murraybowles', FsSourceType.WEB, cfg)