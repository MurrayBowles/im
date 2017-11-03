''' import/export folders/images from/to the file system '''

import datetime
from enum import Enum
import io
import logging
import os
import re
import weakref


class IENote(Enum):
    NO_DATE         = 1     # (IEFolder) can't extract a date from the filename
    FOLDER_ADDED    = 2     # (IEWorkItem) no FsFolder was found for this IEFolder
    FOLDER_DELETED  = 3     # (IEWorkItem) no IEFolder was found for this FsFolder
    TAGS_ARE_WORDS  = 4     # (IEFolder, IEImageInst)
                            # [ 'green', 'day', 'ok' ] not [ 'green day', 'ok' ]
    UNEXPECTED_FILES = 5    # (IEFolder) unexpected files were found in the directory(s)
    EXTRA_INSTS     = 6     # (IEImage) multiple IEImageInsts for the same extension

class IEFolder(object):

    def __init__(self, fs_path, fs_name, date, name, mod_datetime):
        self.fs_path = fs_path  # filesystem pathname
        self.fs_name = fs_name  # filename, e.g. '171007 virginia'
        self.date = date        # the folder date, e.g. 10/07/2017
        self.name = name        # just the name, e.g. 'virginia'
        self.mod_datetime = mod_datetime
        self.images = {}        # IEImage.name -> IEImage
        self.notes = set()      # set of IENote
        self.tags = []          # list of tag strings

    def __repr__(self):
        return '<IEFolder %s' % self.fs_name


class IEImage(object):

    def __init__(self, ie_folder, name):

        self.ie_folder = weakref.ref(ie_folder)
        self.name = name        # just the sequence suffix, e.g. 123
        self.notes = set()      # set of IENote
        self.insts = {}         # extension (e.g. 'jpg-hi') -> list of IEImageInst

    def __repr__(self):
        return '<IEImage %s/%s>' % (self.ie_folder.fs_name, self.name)


class IEImageInst(object):

    def __init__(self, ie_image, fs_path, mod_datetime):

        self.ie_image = weakref.ref(ie_image)
        self.fs_path = fs_path  # filesystem pathname
        self.mod_datetime = mod_datetime
        self.notes = set()      # set of IENotes
        self.tags = []          # list of tag strings

    def __repr__(self):
        return '<IEImageInst %s/%s.%s>' % (
            self.ie_image.ie_folder.fs_name, self.ie_image.name,
            os.path.splitext(self.fs_path)[1][1:])

# a std_dirname has the form 'yymmdd name'
leading_date_space = re.compile(r'^\d{6,6} ')
leading_date = re.compile(r'^\d{6,6}')

def is_std_dirname(dirname):
    ''' return whether dirname is a "standard" directory of image files '''
    return leading_date_space.match(dirname) is not None

def date_from_yymmdd(yymmdd):
    ''' return a datetime.date from a 'yymmdd' string '''
    year = int(yymmdd[0:2])
    year += 1900 if year >= 70 else 2000
    month = int(yymmdd[2:4])
    day = int(yymmdd[4:6])
    return datetime.date(year, month, day)

def proc_std_dirname(dir_pathname, dir_name):
    match = leading_date.match(dir_name)
    if match is None:
        date = None
        name = dir_name
    else:
        yymmdd = match.group()
        date = date_from_yymmdd(yymmdd)
        name = dir_name[match.end():].lstrip(' ')
    stat_mtime = os.path.getmtime(dir_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)
    folder = IEFolder(dir_pathname, dir_name, date, name, mtime)
    if date is None:
        folder.notes.add(IENote.NO_DATE)
    return folder

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

# recognized image file extensions
img_extensions = [ '.nef', '.tif', '.psd', '.jpg' ]
ignored_extensions = [ '.zip' ]
# the filename 'New Text Document.txt'(!) is recognized as a source of folder tags

def scan_std_dir_files(ie_folder):
    def acquire_file(file_path, file_name):
        if file_name == 'New Text Document.txt':
            tag_lines = open(file_path, 'r').readline()
            for tag_line in tag_lines:
                fs_folder.tags.extend(tag_line.split(','))
        else:
            base_name, ext = os.path.splitext(file_name)
            if ext in img_extensions:
                base_name = base_name.lower()
                base, seq = base_name.split('-')
                stat_mtime = os.path.getmtime(file_pathname)
                mtime = datetime.datetime.fromtimestamp(stat_mtime)
                if seq in ie_folder.images:
                    ie_image = ie_folder.images[seq]
                else:
                    ie_image = IEImage(ie_folder, seq)
                    folder.images[seq] = ie_image
                ie_image_inst = IEImageInst(ie_image, file_path, mtime)
                if len(ie_image.insts[ext]) == 0:
                    ie_image.insts[ext] = [ie_image_inst]
                else:
                    logging.error('multiple insts for %s', str(ie_image_inst))
                    ie_image.notes.add(IENote.EXTRA_INSTS)
                    ie_image.insts[ext].append(ie_image_inst)
            else:
                logging.error('unexpected file %s', file_name)
                folder.notes.add(IENote, UNEXPECTED_FILES)

    def acquire_dir(pathname, high_res):
        # TODO: detect high_res from exif dimensions
        logging.debug('scan_std_dir_images(%s)', pathname)
        file_name_list = os.listdir(pathname)
        for file_name in file_name_list:
            file_path = os.path.join(pathname, file_name)
            if os.path.isdir(file_path):
                acquire_dir(file_path, file_name == 'hi')
            else:
                acquire_file(file_path, file_name)

    acquire_dir(ie_folder.pathname, high_res=False)

trailing_date = re.compile(r'_[0-9]+_[0-9]+(&[0-9]+)?_[0-9]+')
amper_date = re.compile(r'&[0-9]+')

def proc_corbett_filename(file_pathname, file_name, folders):
    notes = set([IENote.TAGS_ARE_WORDS])
    base_name, ext = os.path.splitext(file_name)

    base_name = base_name.lower()
    base, seq = base_name.split('-')
    stat_mtime = os.path.getmtime(file_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)

    if len(folders) == 0 or base != folders[-1].fs_name.split('-')[0].lower():
        # start a new IEFolder
        match = trailing_date.search(base)
        if match is None:
            errors.add(IENote.NO_DATE)
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
        ie_folder = IEFolder(file_pathname, file_name, date, name, mtime)
        ie_folder.notes = notes
        ie_folder.tags = words
        folders.append(ie_folder)
    else:
        ie_folder = folders[-1]
        if mtime > ie_folder.mod_datetime:
            # folder.mod_datetime is the newest instance's
            ie_folder.mod_datetime = mtime
    if seq in ie_folder.images:
        ie_image = ie_folder.images[seq]
    else:
        ie_image = IEImage(ie_folder, seq)
        ie_folder.images[seq] = ie_image
    ie_image_inst = IEImageInst(ie_image, file_pathname, mtime)
    ie_image.insts[ext] = [ie_image_inst]
    folders[-1].images[seq] = ie_image
    return ie_image_inst

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
