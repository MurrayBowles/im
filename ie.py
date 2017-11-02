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

    def __init__(self, fs_name, date, name, mod_datetime, errors=None, words=None):
        self.fs_name = fs_name
        self.date = date
        self.name = name
        self.mod_datetime = mod_datetime
        self.images = {}    # IEImage.name -> IEImage
        self.errors = set() if errors is None else errors
        self.words = words


class IEImage(object):

    def __init__(self, name):

        self.name = name
        self.errors = set()
        self.insts = []


class IEImageInst(object):

    def __init__(self, image, fs_name, mod_datetime, errors=None):
        self.fs_name = fs_name
        self.image = image
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
    ''' return a list of IEFolders representing each directory satisfying test
        the list is sorted by folder fs_name
        test(dir_name) checks whether the directory should be processed
        proc(dir_pathname, dir_name) returns an IEFolder for the directory
    '''
    folders = []
    for dir in os.listdir(dir_set_pathname):
        dir_path = os.path.join(dir_set_pathname, dir)
        if os.path.isdir(dir_path) and test(dir):
            folder = proc(dir_path, dir)
            if folder is not None:
                folders.append(folder)
    folders.sort(key=lambda folder: folder.fs_name)
    return folders

def scan_dir_sel(dir_pathname_list, proc):
    ''' return a list of IEFolders representing each directory satisfying test
        the list is sorted by fs_name
        proc(dir_pathname, dir_name) returns an IEFolder for the directory
    '''

    folders = []
    for dir_path in dir_pathname_list:
        if os.path.isdir(dir_path):
            folder = proc(dir_path, os.path.basename(dir_path))
            if folder is not None:
                folders.append(folder)
    folders.sort(key=lambda folder: folder.fs_name)
    return folders

trailing_date = re.compile(r'_[0-9]+_[0-9]+(&[0-9]+)?_[0-9]+')
amper_date = re.compile(r'&[0-9]+')

def proc_corbett_filename(file_pathname, file_name, folders):
    errors = set()
    base_name = os.path.splitext(file_name)[0]
    base, seq = base_name.split('-')
    stat_mtime = os.path.getmtime(file_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)
    if len(folders) == 0 or base != folders[-1].fs_name.split('-')[0]:
        # start a new IEFolder
        match = trailing_date.search(base)
        if match is None:
            errors.add(IEError.NO_DATE)
            date = None
            name = base
        else:
            date_str = match.group()[1:] # drop the leading underscore
            date_str = amper_date.sub('', date_str)
            month_str, day_str, year_str = date_str.split('_')
            year = int(year_str)
            year += 1900 if year >= 70 else 2000
            month = int(month_str)
            day = int(day_str)
            date = datetime.date(year, month, day)
            name = base_name[0:match.start()]
        words = name.split('_')
        folder = IEFolder(file_name, date, name, mtime, errors=errors, words=words)
        folders.append(folder)
    else:
        folder = folders[-1]
        if mtime > folder.mod_datetime:
            # folder.mod_datetime is the newest instance's
            folder.mod_datetime = mtime
    if seq in folder.images:
        image = folder.images[seq]
    else:
        image = IEImage(seq)
        folder.images[seq] = image
    image_inst = IEImageInst(image, file_name, mtime)
    image.insts.append(image_inst)
    folders[-1].images[seq] = image
    return image

def scan_file_set(file_set_pathname, test, proc):
    ''' return a list of IEFolders (each containing IEImages)
        representing the folders and images found in file_set_pathname
        the list is sorted by folder fs_name
        test(file_name) checks whether the directory should be processed
        proc(file_pathname, file_name, folders) returns an IEImage for the file, and,
        if the filename has a new prefix, adds a new IEFolder to folders
    '''
    folders = []
    for file in os.listdir(file_set_pathname):
        file_path = os.path.join(file_set_pathname, file)
        if os.path.isfile(file_path) and test(file):
            proc(file_path, file, folders)
    folders.sort(key=lambda folder: folder.fs_name)
    for folder in folders:
        folder.images.sort(key=lambda x: x.name)

    return folders

def scan_file_sel(file_pathname_list, proc):
    ''' return a list of IEFolders (each containing IEImages)
        representing the folders and images found in file_pathname_list
        the list is sorted by folder fs_name
        test(file_name) checks whether the directory should be processed
        proc(file_pathname, file_name, folders) returns an IEImage for the file, and,
        if the filename has a new prefix, adds a new IEFolder to folders
    '''
    folders = []
    for file_path in file_pathname_list:
        if os.path.isfile(file_path):
            proc(file_path, os.path.basename(file_path), folders)
    folders.sort(key=lambda folder: folder.fs_name)
    return folders
