import pytest

from ie import *
import re

base_path = '\\users\\user\\PycharmProjects\\im\\test\\import-export sources'
# TODO: get PyCharm to provide all but the last directory

def _check_dir_results(got_list, expected_list):
    assert len(got_list) == len(expected_list)
    for j in range(len(got_list)):
        assert got_list[j].fs_name == expected_list[j]

def _test_scan_dir_set(dir_set_pathname, test, proc, expected_list):
    got_list = scan_dir_set(dir_set_pathname, test, proc)
    _check_dir_results(got_list, expected_list)


def test_scan_dir_set_my_dirs():
    expected_list = [
        '171007 virginia',
        '171020 initial nefs',
        '171021 initial nefs and tiffs',
        '830716 eastern front',
        '840723 cha cha',
        '850121 i-beam',
        '850209 mab private outrage tales of terror',
        '860719 new method sacrilege das damen 7sec beefeater'
    ]
    _test_scan_dir_set(
        os.path.join(base_path, 'my format'),
        is_std_dirname, proc_std_dirname,
        expected_list)


def _test_scan_dir_sel(dir_pathname_list, expected_list):
    got_list = scan_dir_sel(dir_pathname_list, proc_std_dirname)
    _check_dir_results(got_list, expected_list)


def test_scan_dir_sel_my_dirs():
    selected_list = [
        os.path.join(base_path, 'my format', '171007 virginia'),
        os.path.join(base_path, 'my format', 'ayers')
    ]
    expected_list = [
        '171007 virginia',
        'ayers'
    ]
    _test_scan_dir_sel(selected_list, expected_list)

def _check_file_results(got_list, expected_list):
    assert len(got_list) == len(expected_list)
    for j in range(len(got_list)):
        got_folder = got_list[j]
        expected_folder = expected_list[j]
        assert got_folder.fs_name == expected_folder[0]
        assert len(got_folder.images) == len(expected_folder[1])
        for k in range(len(got_folder.images)):
            assert got_folder.images[k].name == expected_folder[1][k]

def _test_scan_file_set(file_set_pathname, test, proc, expected_list):
    got_list = scan_file_set(file_set_pathname, test, proc)
    _check_file_results(got_list, expected_list)

def test_scan_corbett_psds():
    expected_list = [
        ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', ['9336', '9337']),
        ('BLATZ_15_ASBESTOS_11_03_90-2744.psd', ['2744', '2745']),
        ('FIFTEEN_TRIBE_8_JAWBREAKER_GILMAN_11_15&16_91-5605.psd', ['5605', '5631'])
    ]
    _test_scan_file_set(
        os.path.join(base_path, 'main1415 corbett psds'),
        lambda x: True, proc_corbett_filename,
        expected_list)

def _test_scan_file_sel(file_pathname_list, proc, expected_list):
    got_list = scan_file_sel(file_pathname_list, proc)
    _check_file_results(got_list, expected_list)

def test_scan_corbett_psds():
    selected_list = [
        os.path.join(base_path, 'main1415 corbett psds',
            'BIKINI_KILL_GILMAN_10_10_92-9336.psd'),
        os.path.join(base_path, 'main1415 corbett psds',
            'BLATZ_15_ASBESTOS_11_03_90-2744.psd'),
        os.path.join(base_path, 'main1415 corbett psds',
            'BLATZ_15_ASBESTOS_11_03_90-2745.psd')
    ]
    expected_list = [
        ('BIKINI_KILL_GILMAN_10_10_92-9336.psd', ['9336']),
        ('BLATZ_15_ASBESTOS_11_03_90-2744.psd', ['2744', '2745'])
    ]
    _test_scan_file_sel(selected_list, proc_corbett_filename, expected_list)

