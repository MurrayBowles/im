''' test ie_fs (import/export folders/images from/to the file system) '''

import pytest

from ie_fs import *
import re

base_path = '\\users\\user\\PycharmProjects\\im\\test\\import-export sources'
# TODO: get PyCharm/pytest to provide this, up to the last directory

def _check_dir_results(got_list, expected_list):
    assert len(got_list) == len(expected_list)
    for j in range(len(got_list)):
        assert got_list[j].fs_name == expected_list[j][0]

def _test_scan_dir_set(dir_set_pathname, test, proc, expected_list):
    got_list = scan_dir_set(dir_set_pathname, test, proc)
    _check_dir_results(got_list, expected_list)
    for folder in got_list:
        scan_std_dir_files(folder)
        pass

test_scan_dir_set_expected_list = [
    ('171007 virginia',[]),
    ('171020 initial nefs',[]),
    ('171021 initial nefs and tiffs',[]),
    ('830716 eastern front',[]),
    ('840723 cha cha',[]),
    ('850121 i-beam',[]),
    ('850209 mab private outrage tales of terror',[]),
    ('860719 new method sacrilege das damen 7sec beefeater',[])
]

def test_scan_dir_set_my_dirs():
    _test_scan_dir_set(
        os.path.join(base_path, 'my format'),
        is_std_dirname, proc_std_dirname,
        test_scan_dir_set_expected_list)

def _test_scan_dir_sel(dir_pathname_list, expected_list):
    got_list = scan_dir_sel(dir_pathname_list, proc_std_dirname)
    _check_dir_results(got_list, expected_list)
    for folder in got_list:
        scan_std_dir_files(folder)
        pass

test_scan_dir_sel_selected_list = [
    os.path.join(base_path, 'my format', '171007 virginia'),
    os.path.join(base_path, 'my format', 'ayers')
]
test_scan_dir_sel_expected_list = [
    ('171007 virginia',[]),
    ('ayers',[])
]

def test_scan_dir_sel_my_dirs():
    _test_scan_dir_sel(
        test_scan_dir_sel_selected_list,
        test_scan_dir_sel_expected_list)

def _check_file_results(got_list, expected_list):
    assert len(got_list) == len(expected_list)
    for j in range(len(got_list)):
        got_folder = got_list[j]
        expected_folder = expected_list[j]
        assert got_folder.fs_name == expected_folder[0]
        assert len(got_folder.images) == len(expected_folder[1])
        for expected_image in expected_folder[1]:
            assert expected_image in got_folder.images

def _test_scan_file_set(file_set_pathname, test, proc, expected_list):
    got_list = scan_file_set(file_set_pathname, test, proc)
    _check_file_results(got_list, expected_list)

test_scan_file_set_corbett_psds_expected_list = [
    ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', ['9336', '9337']),
    ('BLATZ_15_ASBESTOS_11_03_90-2744.psd', ['2744', '2745']),
    ('FIFTEEN_TRIBE_8_JAWBREAKER_GILMAN_11_15&16_91-5605.psd', ['5605', '5631'])
]

def test_scan_file_set_corbett_psds():
    _test_scan_file_set(
        os.path.join(base_path, 'main1415 corbett psds'),
        lambda x: True, proc_corbett_filename,
        test_scan_file_set_corbett_psds_expected_list)

def _test_scan_file_sel(file_pathname_list, proc, expected_list):
    got_list = scan_file_sel(file_pathname_list, proc)
    _check_file_results(got_list, expected_list)

test_scan_file_sel_corbett_psds_selected_list = [
    os.path.join(base_path, 'main1415 corbett psds',
        'BIKINI_KILL_GILMAN_10_10_92-9336.psd'),
    os.path.join(base_path, 'main1415 corbett psds',
        'BLATZ_15_ASBESTOS_11_03_90-2744.psd'),
    os.path.join(base_path, 'main1415 corbett psds',
        'BLATZ_15_ASBESTOS_11_03_90-2745.psd')
]
test_scan_file_sel_corbett_psds_expected_list = [
    ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', ['9336']),
    ('BLATZ_15_ASBESTOS_11_03_90-2744.psd', ['2744', '2745'])
]

def test_scan_file_sel_corbett_psds():
    _test_scan_file_sel(
        test_scan_file_sel_corbett_psds_selected_list,
        proc_corbett_filename,
        test_scan_file_sel_corbett_psds_expected_list)

