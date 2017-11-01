''' import/export folders/images from/to the file system '''

import datetime
from enum import Enum
import io
import logging
import os
import re


class IEError(Enum):
    NO_DATE = 1    # can't extract a date from the filename


class IEFolder(object):

    def __init__(self, fs_name, date, name, mod_datetime, errors=None):
        self.fs_name = fs_name
        self.date = date
        self.name = name
        self.mod_datetime = mod_datetime
        self.images = []
        self.errors = set() if errors is None else errors


class IEImage(object):

    def __init__(self, fs_name, name, mod_datetime, errors=None):
        self.fs_name = fs_name
        self.name = name
        self.mod_datetime = mod_datetime
        self.errors = set() if errors is None else errors


leading_date_space = re.compile(r'^\d{6,6} ')
leading_date = re.compile(r'^\d{6,6}')


def is_std_dirname(dirname):
    ''' return whether dirname is a "standard" directory of image files '''
    return leading_date_space.match(dirname) is not None

def date_from_yymmdd(yymmdd):
    year = int(yymmdd[0:2])
    year += 1900 if year >= 70 else 2000
    month = int(yymmdd[2:4])
    day = int(yymmdd[4:6])
    return datetime.date(year, month, day)

def proc_std_dirname(dir_pathname, dir_name):
    errors = set()
    match = leading_date.match(dir_name)
    if match is None:
        errors.add(IEError.NO_DATE)
        date = None
        name = dir_name
    else:
        yymmdd = match.group()
        date = date_from_yymmdd(yymmdd)
        name = dir_name[match.end():].lstrip(' ')
    stat_mtime = os.path.getmtime(dir_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)
    return IEFolder(dir_name, date, name, mtime, errors=errors)

def scan_dir_set(dir_set_pathname, test, proc):
    ''' return a list of IEFolders for each directory satisfying test
        the result list is sorted by folder name
        test(dir_name) checks whether the directory should be processed
        process(dir_pathname, dir_name) returns an IEFolder for the directory
    '''
    results = []
    for dir in os.listdir(dir_set_pathname):
        dir_path = os.path.join(dir_set_pathname, dir)
        if os.path.isdir(dir_path) and test(dir):
            folder = proc(dir_path, dir)
            if folder is not None:
                results.append(folder)
    results.sort(key=lambda folder: folder.fs_name)
    return results

def scan_dir_sel(dir_pathname_list, proc):
    ''' return a list of (pathname, mod-datetime) for each directory satisfying test
        the result list is sorted by pathname
        pathlist is a list of directory pathnames
    '''

    results = []
    for dir_path in dir_pathname_list:
        if os.path.isdir(dir_path):
            folder = proc(dir_path, os.path.basename(dir_path))
            if folder is not None:
                results.append(folder)
    results.sort(key=lambda folder: folder.fs_name)
    return results



