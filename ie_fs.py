''' import/export folders/images from/to the file system '''

import datetime
from enum import Enum
import io
import json
import logging
import os
from PIL import Image
import re
import subprocess


class IEMsgType(Enum):

    # value is (printable message, format string for IEMsg.data)
    # based on the format string's length, IEMag.data is
    #   0   None
    #   1   a single object
    #   N   a tuple with N elements
    # format string:
    #   p   pathname string

    NO_DATE             = ('folder name contains no date', 'p')
        # (IEFolder)
    FOLDER_ADDED        = ('new folder in imports', 'p')
        # (IEWorkItem)
    FOLDER_DELETED      = ('folder deleted from import folder set', 'p')
        # (IEWorkItem)
    TAGS_ARE_WORDS      = ('need to identify multi-word tags', '')
        # (IEFolder, IEImageInst) [ 'green', 'day', 'ok' ] not [ 'green day', 'ok' ]
    UNEXPECTED_FILE     = ('an unexpected file was found', 'p')
        # (IEFolder)
    EXTRA_INSTS         = ('multiple instances of this image x extension', 'p')
        # (IEImage)


class IEMsg(object):

    def __init__(self, type, data, report_list = []):
        self.type = type    # IEMsgType
        self.data = data    # depends on type
        self.children = []  # TODO: maybe not necessary: worklist is tree-structured
        if report_list is not None:
            report_list.append(self)
        logging.info(str(self))

    @classmethod
    def fmt_arg(self, fmt_char, data):
        if fmt_char == 'p':
            return data
        raise ValueError('bad format character')

    def __repr__(self):
        s = self.type.value[0] # the printable message
        fmt = self.type.value[1]
        if len(fmt) == 1:
            s += ': ' + IEMsg.fmt_arg(fmt[0], self.data)
        else:
            sep = ': '
            for fmt_char, data in zip(fmt, self.data):
                s += IEMsg.fmt_arg(fmt_char, data)
                sep = ', '
        return s

    def map_lines(self, fn, pfx = ''):
        fn(pfx + self.fmt_line())
        for child in self.children:
            self.map_lines(child, fn, '  ' + pfx)


class IEFolder(object):

    def __init__(self, fs_path, fs_name, date, name, mod_datetime):
        self.fs_path = fs_path  # filesystem pathname
        self.fs_name = fs_name  # filename, e.g. '171007 virginia'
        self.date = date        # the folder date, e.g. 10/07/2017
        self.name = name        # just the name, e.g. 'virginia'
        self.mod_datetime = mod_datetime
        self.images = {}        # IEImage.name -> IEImage
        self.msgs = []          # list of IENote
        self.tags = []          # list of tag strings

    def __repr__(self):
        return '<IEFolder %s>' % self.fs_name


class IEImage(object):

    def __init__(self, ie_folder, name):

        self.ie_folder = ie_folder
        self.name = name        # just the sequence suffix, e.g. 123
        self.msgs = []          # list of IENote
        self.insts = {}         # extension (e.g. 'jpg-hi') -> list of IEImageInst


    def __repr__(self):
        return '<IEImage %s|%s>' % (self.ie_folder.fs_name, self.name)

thumbnail_exts = [ '.jpg', '.jpg-hi' ] # TODO: silly PIL doesn't do TIFFs


class IEImageInst(object):

    def __init__(self, ie_image, fs_path, ext, mod_datetime):

        self.ie_image = ie_image
        self.fs_path = fs_path  # filesystem pathname
        self.ext = ext          # key in ie_image.insts, e.g '.jpg', '.jpg-hi'
        self.mod_datetime = mod_datetime
        self.msgs = []          # list of IEMsg
        self.tags = []          # list of tag strings
        self.ed = self.exif()

    def __repr__(self):
        return '<IEImageInst %s|%s|%s>' % (
            self.ie_image.ie_folder.fs_name, self.ie_image.name, self.ext)

    def thumbnail(self):
        try:
            pimage = Image.open(self.fs_path)
            pimage.thumbnail((200, 200))
            byte_array = io.BytesIO()
            pimage.save(byte_array, format='JPEG')
            bytes = byte_array.getvalue()
            return bytes
        except:
            return None

    def exif(self):
        #outb = exec("exiftool -j -common -XMP-dc:subject -XMP-lr:hierarchicalSubject %s" % self.fs_path)
        outb = subprocess.check_output([
            'exiftool', '-S', '-j', '-ImageSize', '-XMP-dc:subject', '-XMP-lr:hierarchicalSubject',
            self.fs_path])
        #outb = subprocess.check_output(['exiftool', '-j', '-common', self.fs_path])
        outs = str(outb)[2:-5]
        outs = outs.replace(r'\n', '')
        outs = outs.replace(r'\r', '')
        outo = json.loads(outs)
        # it took me two hours to make this work at all, so I'm not touching it!
        return outo

# a std_dirname has the form 'yymmdd name'
leading_date_space = re.compile(r'^\d{6,6} ')
leading_date = re.compile(r'^\d{6,6}')

def is_std_dirname(dirname):
    ''' return whether dirname is a "standard" directory of image files '''
    return True
    # TODO: return leading_date_space.match(dirname) is not None

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
        folder.msgs.append(IEMsg(IEMsgType.NO_DATE, dir_pathname))
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
raw_prefixes = [ 'img_', 'dsc_' ]
ignored_extensions = [ '.zip' ]
ignored_subdirectories = [ 'del' ]
# the filename 'New Text Document.txt'(!) is recognized as a source of folder tags

def scan_std_dir_files(ie_folder):
    def acquire_file(file_path, file_name, high_res):
        if file_name == 'New Text Document.txt':
            tag_lines = open(file_path, 'r').readline()
            for tag_line in tag_lines:
                ie_folder.tags.extend(tag_line.split(','))
        elif os.path.isfile(file_path):
            base_name, ext = os.path.splitext(file_name)
            base_name = base_name.lower()
            ext = ext.lower()
            if ext in img_extensions:
                if high_res:
                    ext += '-hi'
                if base_name.find('-') != -1:
                    seq = base_name.split('-')[1]
                elif any(base_name.startswith(pfx) for pfx in raw_prefixes):
                    # FIXME: prefixes w/ length other than 4
                    seq = base_name[4:]
                else:
                    # e.g. simple named files, as in 'my format/ayers/dks.psd
                    base = ''
                    seq = base_name
                stat_mtime = os.path.getmtime(file_path)
                mtime = datetime.datetime.fromtimestamp(stat_mtime)
                if seq in ie_folder.images:
                    ie_image = ie_folder.images[seq]
                else:
                    ie_image = IEImage(ie_folder, seq)
                    ie_folder.images[seq] = ie_image
                ie_image_inst = IEImageInst(ie_image, file_path, ext, mtime)
                if ext not in ie_image.insts:
                    ie_image.insts[ext] = [ie_image_inst]
                else:
                    logging.error('multiple insts for %s', str(ie_image_inst))
                    ie_image.msgs.add(IEMsg(IEMsgType.EXTRA_INSTS, file_path))
                    ie_image.insts[ext].append(ie_image_inst)
            else:
                logging.error('unexpected file %s', file_name)
                ie_folder.msgs.append(IEMsg(IEMsgType.UNEXPECTED_FILE, 'file_path'))
        else:
            # special file -- ignore
            pass

    def acquire_dir(pathname, high_res):
        # TODO: detect high_res from exif dimensions
        logging.debug('scan_std_dir_images(%s)', pathname)
        file_name_list = os.listdir(pathname)
        for file_name in file_name_list:
            file_path = os.path.join(pathname, file_name)
            if os.path.isdir(file_path):
                if file_name not in ignored_subdirectories:
                    acquire_dir(file_path, file_name == 'hi')
            else:
                acquire_file(file_path, file_name, high_res)

    acquire_dir(ie_folder.fs_path, high_res=False)
    # TODO: adjust seq numbers for Nikon 9999 rollover

trailing_date = re.compile(r'_[0-9]+_[0-9]+(&[0-9]+)?_[0-9]+')
amper_date = re.compile(r'&[0-9]+')

def proc_corbett_filename(file_pathname, file_name, folders):
    msgs = [IEMsg(IEMsgType.TAGS_ARE_WORDS, file_pathname)]
    base_name, ext = os.path.splitext(file_name)

    base_name = base_name.lower()
    base, seq = base_name.split('-')
    stat_mtime = os.path.getmtime(file_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)

    if len(folders) == 0 or base != folders[-1].fs_name.split('-')[0].lower():
        # start a new IEFolder
        match = trailing_date.search(base)
        if match is None:
            errors.add(IEMsg(IEMsgType.NO_DATE))
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
        ie_folder.msgs = msgs
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
    ie_image_inst = IEImageInst(ie_image, file_pathname, ext, mtime)
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
