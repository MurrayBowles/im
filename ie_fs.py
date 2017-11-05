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

    # value is (message, severity/format string)
    # the first character of the severity/format string is
    #   i   informational
    #   e   user error
    #   E   internal error
    # followed by 0 or more formatting characters
    #   p   pathname string
    #   s   string
    # based on the number of formatting characters, IEMag.data is
    #   0   None
    #   1   a single object
    #   N   a tuple with N elements

    NO_DATE             = ('folder name contains no date', 'ip')
        # (IEFolder)
    FOLDER_ADDED        = ('folder added to imports', 'ip')
        # (IEWorkItem)
    FOLDER_DELETED      = ('folder deleted from import folder set', 'ip')
        # (IEWorkItem)
    TAGS_ARE_WORDS      = ('tags need editing', 'i')
        # (IEFolder, IEImageInst) [ 'green', 'day', 'ok' ] not [ 'green day', 'ok' ]
    UNEXPECTED_FILE     = ('unexpected file found', 'ip')
        # (IEFolder)
    EXTRA_INSTS         = ('multiple instances of this (image, extension)', 'ip')
        # (IEImage)
    NO_IMAGES           = ('folder contains no images', 'ip')
        # (IEFolder)
    CANT_FIND_IMAGE     = ("internal error: can't find folder image from pathmane", 'Ep')
        # (IEFolder)
    NAME_NEEDS_EDIT     = ('folder name needs exiting', 'is')
        # (IEFolder)

class IEMsg(object):

    def __init__(self, type, data, report_list = []):
        self.type = type    # IEMsgType
        self.data = data    # depends on type
        self.children = []  # TODO: maybe not necessary: worklist is tree-structured
        if report_list is not None:
            report_list.append(self)
        if type.value[1][0] == 'i':
            logging.info(str(self))
        else:
            logging.error(str(self))

    @classmethod
    def fmt_arg(self, fmt_char, data):
        if fmt_char == 'p' or fmt_char == 's':
            return data
        raise ValueError('bad format character')

    def __repr__(self):
        lvl_fmt = self.type.value[1]
        assert len(lvl_fmt) >= 1
        lvl = lvl_fmt[:1]
        fmt = lvl_fmt[1:]
        s = { 'i': '%', 'e': '?', 'E': '!?'}[lvl]
        s += self.type.value[0] # the printable message
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

    @classmethod
    def find(cls, msg_type, msgs):
        for msg in msgs:
            if msg.type == msg_type:
                return msg.data
        else:
            return None


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
        self.image_insts = {}   # map: IEImageInst.fs_path => IEImageInst

    def __repr__(self):
        return '<IEFolder %s>' % self.fs_name

thumbnail_exts = [ '.jpg', '.jpg-hi' ] # TODO: silly PIL doesn't do TIFFs
exif_exts = [ '.tif', '.psd', '.jpg', '.jpg-hi' ]

class IEImage(object):

    def __init__(self, ie_folder, name):

        self.ie_folder = ie_folder
        self.name = name        # just the sequence suffix, e.g. 123
        self.msgs = []          # list of IENote
        self.insts = {}         # extension (e.g. 'jpg-hi') -> list of IEImageInst

        self.newest_inst_with_thumbnail = None  # read by proc_ie_work_item
        self.thumbnail = None                   # set when/if the thumbnail is extracted
        self.tags = None                        # set when/if the tags are extracted

    def __repr__(self):
        return '<IEImage %s|%s>' % (self.ie_folder.fs_name, self.name)

    def set_attrs_from_exiftool_json(self, item):
        if 'ImageSize' in item:
            w, h = item['ImageSize'].split('x')
            self.image_size = (int(w), int(h))
        if 'Subject' in item:
            self.tags = item['Subject']

class IEImageInst(object):

    def __init__(self, ie_image, fs_path, ext, mod_datetime):

        self.ie_image = ie_image
        self.fs_path = fs_path  # filesystem pathname
        self.ext = ext          # key in ie_image.insts, e.g '.jpg', '.jpg-hi'
        self.mod_datetime = mod_datetime
        self.msgs = []          # list of IEMsg

        # add to the IEFolder's pathname => IEImageInst map
        ie_image.ie_folder.image_insts[fs_path] = self

        if ext in thumbnail_exts and (
                ie_image.newest_inst_with_thumbnail is None or
                mod_datetime > ie_image.newest_inst_with_thumbnail.mod_datetime):
            ie_image.newest_inst_with_thumbnail = self

    def __repr__(self):
        return '<IEImageInst %s|%s|%s>' % (
            self.ie_image.ie_folder.fs_name, self.ie_image.name, self.ext)

    def get_thumbnail(self):
        try:
            pimage = Image.open(self.fs_path)
            pimage.thumbnail((200, 200))
            byte_array = io.BytesIO()
            pimage.save(byte_array, format='JPEG')
            bytes = byte_array.getvalue()
            return bytes
        except:
            return None

_exiftool_args = [
    'exiftool', '-S', '-j', '-q',
    '-ImageSize',
    '-XMP-dc:subject',
    '-XMP-lr:hierarchicalSubject'
]

def _get_exiftool_json(argv):
    ''' runs exiftool on <argv> and returns a list of dictionaries containing the results '''
    outb = subprocess.check_output(argv)
    outs = str(outb)[2:-5].replace(r'\n', '').replace(r'\r', '')
    exiftool_json = json.loads(outs)
    return exiftool_json

def get_ie_image_exifs(ie_image_set, pub):
    ''' get exif data for all the images in <ie_image_set>
        deletes images from the set as their exifs are processed
    '''

    def proc_exiftool_json(ie_image_set, inst_paths, exiftool_json):
        for item in exiftool_json:
            fs_path = os.path.abspath(item['SourceFile'])
            drive, fs_path = os.path.splitdrive(fs_path)
            if fs_path in inst_paths:
                ie_image_inst = inst_paths[fs_path]
                ie_image_inst.ie_image.set_attrs_from_exiftool_json(item)
                ie_image_set.remove(ie_image_inst.ie_image)
            else:
                logging.error("can't find ie_image_inst inf ie_folders map: %s", fs_path)

    # attempt in the order of exif_exts
    for ext in exif_exts:
        if len(ie_image_set) == 0:
            break
        # collect IEImageInsts and their directories
        dir_insts = {} # map: directory pathname => list of IEImageInst
        inst_paths = {} # map: fs_path => image_inst
        for ie_image in ie_image_set:
            if ext in ie_image.insts:
                for ie_image_inst in ie_image.insts[ext]:
                    inst_path = ie_image_inst.fs_path
                    inst_paths[inst_path] = ie_image_inst
                    dir_path = os.path.dirname(inst_path)
                    if dir_path in dir_insts:
                        dir_insts[dir_path].append(ie_image_inst)
                    else:
                        dir_insts[dir_path] = [ie_image_inst]
        if len(dir_insts) == 0:
            continue # no image files with this extenstion
        fs_ext = ext[0:-3] if ext.endswith('-hi') else ext # .jpg-hi => .jpg
        for dir_path, worklist in dir_insts.items():
            num_dir_files = len(os.listdir(dir_path))
            if len(worklist) > num_dir_files / 2:
                # run exiftools on <dir>/*.<ext>
                argv = list(_exiftool_args)
                argv.append(os.path.join(dir_path, '*' + fs_ext))
                exiftool_json = _get_exiftool_json(argv)
                proc_exiftool_json(ie_image_set, inst_paths, exiftool_json)
            else:
                # run exiftools on <file1> <file2> ...
                while len(worklist) > 0:
                    n = min(len(worklist), 10) # up to 10 files per run
                    sublist, worklist = worklist[:n], worklist[n:]
                    argv = list(_exiftool_args)
                    for ie_image_inst in sublist:
                        argv.append(ie_image_inst.fs_path)
                    exiftool_json = _get_exiftool_json(argv)
                    proc_exiftool_json(ie_image_set, inst_paths, exiftool_json)
            pub('ie.imported_tags', len(exiftool_json))

def get_ie_image_thumbnails(ie_image_set, pub):
    ''' extract thumbnails for the images in <ie_image_set>
        deletes images from the set as their thumbnails are proecesed
    '''
    for ie_image in ie_image_set:
        ie_image_inst = ie_image.newest_inst_with_thumbnail
        assert ie_image_inst is not None
        ie_image.thumbnail = ie_image_inst.get_thumbnail()
        pub('ie.imported thumbnail', 1)
    # clear(ie_image_set) FIXME: why does this fail?

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
        got_folder_tags = False
        if file_name == 'New Text Document.txt':
            got_folder_tags = True
            tag_lines = open(file_path, 'r').readlines()
            for tag_line in tag_lines:
                ie_folder.tags.extend([l.lstrip(' ') for l in tag_line.split(',')])
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
        return got_folder_tags

    def acquire_dir(pathname, high_res):
        # TODO: detect high_res from exif dimensions
        logging.debug('scan_std_dir_images(%s)', pathname)
        got_folder_tags = False
        file_name_list = os.listdir(pathname)
        for file_name in file_name_list:
            file_path = os.path.join(pathname, file_name)
            if os.path.isdir(file_path):
                if file_name not in ignored_subdirectories:
                    acquire_dir(file_path, file_name == 'hi')
            else:
                got_folder_tags |= acquire_file(file_path, file_name, high_res)
        return got_folder_tags

    got_folder_tags = acquire_dir(ie_folder.fs_path, high_res=False)
    if not got_folder_tags:
        ie_folder.msgs.append(IEMsg(IEMsgType.NAME_NEEDS_EDIT, ie_folder.name))
    # TODO: adjust seq numbers for Nikon 9999 rollover

trailing_date = re.compile(r'_[0-9]+_[0-9]+(&[0-9]+)?_[0-9]+')
amper_date = re.compile(r'&[0-9]+')

def proc_corbett_filename(file_pathname, file_name, folders):
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
        ie_folder.tags = words
        ie_folder.msgs.append(IEMsg(IEMsgType.TAGS_ARE_WORDS, file_pathname))
        ie_folder.msgs.append(IEMsg(IEMsgType.NAME_NEEDS_EDIT, name))
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
