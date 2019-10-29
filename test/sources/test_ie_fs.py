""" test ie_fs (import/export folders/images from/to the file system) """

from pathlib import Path
import pytest

from base_path import base_path
from ie_fs import *

def touch_file(path):
    """ update the modification date of the file at <db_name> """
    Path(path).touch()

_ext_map = {
    'n': '.nef',
    'p': '.psd',
    't': '.tif',
    'j': '.jpg',
    'J': '.jpg-hi'
}

def _check_image_results(got_folder, expected):
    assert len(got_folder.images) == len(expected[1])
    for expected_image_str in expected[1]:
        exp_image, exp_exts = expected_image_str.split('-')
        assert exp_image in got_folder.images
        got_image = got_folder.images[exp_image]
        if exp_exts[0] == 'X':
            # X used by ie_test_db
            exp_exts = exp_exts[1:]
        assert len(exp_exts) == len(got_image.insts)
        for c in exp_exts:
            ext = _ext_map[c]
            assert ext in got_image.insts

def _check_dir_results(got_list, expected_list):
    assert len(got_list) == len(expected_list)
    for j in range(len(got_list)):
        ie_folder = got_list[j]
        assert os.path.basename(ie_folder.fs_path) == expected_list[j][0]
        _check_image_results(ie_folder, expected_list[j])

def _test_scan_dir_set(dir_set_pathname, test, proc, expected_list):
    got_list = scan_dir_set(dir_set_pathname, test, proc)
    for folder in got_list:
        scan_std_dir_files(folder)
    _check_dir_results(got_list, expected_list)


test_scan_dir_set_expected_list = [
    ('171007 virginia',[
        '8963-n', '8965-npJj', '8969-npj', '8970-npJj'
    ]),
    ('171020 initial nefs',[
        '9572-n', '9573-n', '9574-n'
    ]),
    ('171021 initial nefs and tiffs',[
        '9575-nt', '9576-nt', '9577-nt'
    ]),
    ('830716 eastern front',[]),
    ('840723 cha cha',[
        '0001-t', '0002-pt', '0102-j'
    ]),
    ('850121 i-beam',[
        '0017-pj', '0018-pj', '0019-pj'
    ]),
    ('850209 mab private outrage tales of terror',[
        '008-pj', '009-pjJ', '010-pj'
    ]),
    ('860719 new method sacrilege das damen 7sec beefeater',[
        '005-pj', '025-pj'
    ]),
    ('ayers',[
        'dks-jp', 'insaints-j', 'offspring-j'
    ])
]

# my format
def test_scan_dir_set_my_dirs():
    _test_scan_dir_set(
        os.path.join(base_path, 'my format'),
        is_std_dirname, proc_std_dirname,
        test_scan_dir_set_expected_list)

def _test_scan_dir_sel(dir_pathname_list, expected_list):
    got_list = scan_dir_sel(dir_pathname_list, proc_std_dirname)
    for folder in got_list:
        scan_std_dir_files(folder)
    _check_dir_results(got_list, expected_list)

test_scan_dir_sel_selected_list = [
    os.path.join(base_path, 'my format', '171007 virginia'),
    os.path.join(base_path, 'my format', 'ayers')
]
test_scan_dir_sel_expected_list = [
    ('171007 virginia',[
        '8963-n', '8965-npJj', '8969-npj', '8970-npJj'
    ]),
    ('ayers',[
        'dks-jp', 'insaints-j', 'offspring-j'
    ])
]

# my format
def test_scan_dir_sel_my_dirs():
    _test_scan_dir_sel(
        test_scan_dir_sel_selected_list,
        test_scan_dir_sel_expected_list)

def _check_file_results(got_list, expected_list):
    assert len(got_list) == len(expected_list)
    for j in range(len(got_list)):
        got_folder = got_list[j]
        expected_folder = expected_list[j]
        assert os.path.basename(got_folder.fs_path) == expected_folder[0]
        _check_image_results(got_folder, expected_folder)

def _test_scan_file_set(file_set_pathname, test, proc, expected_list):
    got_list = scan_file_set(file_set_pathname, test, proc)
    _check_file_results(got_list, expected_list)

def _test_scan_file_sel(file_pathname_list, proc, expected_list):
    got_list = scan_file_sel(file_pathname_list, proc)
    _check_file_results(got_list, expected_list)


# main1415

test_scan_file_set_corbett_psds_expected_list = [
    ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', [
        '9336-p', '9337-p'
    ]),
    ('BLATZ_15_ASBESTOS_11_03_90-2744.psd', [
        '2744-Xp', '2745-p'
    ]),
    ('FIFTEEN_TRIBE_8_JAWBREAKER_GILMAN_11_15&16_91-5605.psd', [
        '5605-Xp', '5631-Xp'
    ])
]

def test_scan_file_set_corbett_psds():
    _test_scan_file_set(
        os.path.join(base_path, 'main1415 corbett psds'),
        lambda x: True, proc_corbett_filename,
        test_scan_file_set_corbett_psds_expected_list)

test_scan_file_sel_corbett_psds_selected_list = [
    os.path.join(base_path, 'main1415 corbett psds',
        'BIKINI_KILL_GILMAN_10_10_92-9336.psd'),
    os.path.join(base_path, 'main1415 corbett psds',
        'BLATZ_15_ASBESTOS_11_03_90-2744.psd'),
    os.path.join(base_path, 'main1415 corbett psds',
        'BLATZ_15_ASBESTOS_11_03_90-2745.psd')
]
test_scan_file_sel_corbett_psds_expected_list = [
    ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', [
        '9336-p'
    ]),
    ('BLATZ_15_ASBESTOS_11_03_90-2744.psd', [
        '2744-Xp', '2745-p'
    ])
]

def test_scan_file_sel_corbett_psds():
    _test_scan_file_sel(
        test_scan_file_sel_corbett_psds_selected_list,
        proc_corbett_filename,
        test_scan_file_sel_corbett_psds_expected_list)


# corbett drive


test_scan_file_set_corbett_tiffs_expected_list = [
    ('01_03_92_15_GILMAN-001.tif', [
        '001-Xt', '002-Xt'
    ]),
    ('01_11_92_NUISANCE_MTX_PHOENIX-014.tif', [
        '014-Xt', '015-Xt'
    ]),
    ('02_13&16_89_SOUNDGARDEN_MUDHONEY_IBEAM&BSQ-001.tif', [
        '001-Xt', '002-Xt'
    ])
]

def test_scan_file_set_corbett_tiffs():
    _test_scan_file_set(
        os.path.join(base_path, 'corbett drive'),
        lambda x: True, proc_corbett_filename,
        test_scan_file_set_corbett_tiffs_expected_list)

test_scan_file_sel_corbett_tiffs_selected_list = [
    os.path.join(base_path, 'corbett drive',
        '01_11_92_NUISANCE_MTX_PHOENIX-014.tif'),
    os.path.join(base_path, 'corbett drive',
        '01_11_92_NUISANCE_MTX_PHOENIX-015.tif'),
    os.path.join(base_path, 'corbett drive',
        '02_13&16_89_SOUNDGARDEN_MUDHONEY_IBEAM&BSQ-001.tif'),
    os.path.join(base_path, 'corbett drive',
        '02_13&16_89_SOUNDGARDEN_MUDHONEY_IBEAM&BSQ-002.tif')
]
test_scan_file_sel_corbett_tiffs_expected_list = [
    ('01_11_92_NUISANCE_MTX_PHOENIX-014.tif', [
        '014-Xt', '015-Xt'
    ]),
    ('02_13&16_89_SOUNDGARDEN_MUDHONEY_IBEAM&BSQ-001.tif', [
        '001-Xt', '002-Xt'
    ])
]

def test_scan_file_sel_corbett_tiffs():
    _test_scan_file_sel(
        test_scan_file_sel_corbett_tiffs_selected_list,
        proc_corbett_filename,
        test_scan_file_sel_corbett_tiffs_expected_list)

