import pytest

from ie import *
import re

base_path = '\\users\\user\\PycharmProjects\\im\\test\\import-export sources'
# TODO: get PyCharm to provide all but the last directory

def _test_scan_dir_set(dir_set_pathname, test, proc, expected_list):
    # expected_list is sorted

    got_list = scan_dir_set(dir_set_pathname, test, proc)
    assert len(got_list) == len(expected_list)

    for j in range(len(got_list)):
        assert got_list[j].fs_name == expected_list[j]


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
    # pathlist is sorted

    got_list = scan_dir_sel(dir_pathname_list, proc_std_dirname)
    assert len(got_list) == len(expected_list)

    for j in range(len(got_list)):
        assert got_list[j].fs_name == expected_list[j]


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
