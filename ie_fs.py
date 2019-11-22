""" import/export folders/images from/to the file system """

import datetime
from enum import Enum, IntEnum
import io
import json
import logging
import os
from PIL import Image
import re
import subprocess

import util


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

    NO_DATE             = ('IEFolder.date is None', 'ip')
        # (IEFolder)
    FOLDER_ADDED        = ('folder added to imports', 'ip')  # unused
        # (IEWorkItem)
    FOLDER_DELETED      = ('folder deleted from import folder set', 'ip')  # unused
        # (IEWorkItem)
    TAGS_ARE_WORDS      = ('tags need editing', 'i')
        # (IEFolder) [ 'green', 'day', 'ok' ]  TODO should also be IEImage[Inst]
    UNEXPECTED_FILE     = ('unexpected file found', 'ip')
        # (IEFolder)
    EXTRA_INSTS         = ('multiple instances of (image, extension)', 'ip')
        # (IEImage)
    NO_IMAGES           = ('folder contains no images', 'ip')  # unused
        # (IEFolder)
    CANT_FIND_IMAGE     = ("internal error: can't find folder image", 'Ep')  # unused
        # (IEFolder)
    NAME_NEEDS_EDIT     = ('IEFolder.db_name needs editing', 'is')
        # (IEFolder)

class IEMsg(object):

    def __init__(self, type, data, report_list = []):
        self.type = type    # IEMsgType
        self.data = data    # depends on type
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

    @classmethod
    def find(cls, msg_type, msgs):
        for msg in msgs:
            if msg.type == msg_type:
                return msg.data
        else:
            return None


class IETagType(IntEnum):
    AUTO    = 1 # if not found, auto-add <base>|<state>
                # flag tag as auto-added
    BASED   = 2 # if not found, put <base>|<state> in the imported tags
                # flag item as tag-needs-edit
    UNBASED = 3 # if not found, put <state> in the imported tags
                # flag item as tag-needs-edit
    WORD    = 4 # multiple words may need to be concatenated to get a tag
                # flag item as tags-are-words
    NOTE    = 5 # auto-add a 'Facebook Event' note to the item, with url = <url>

    def __repr__(self):
        return '+-?WN'[self.value]

    @classmethod
    def from_code(self, code):
        if code == '+': return IETagType.AUTO
        if code == '-': return IETagType.BASED
        if code == '?': return IETagType.UNBASED
        if code == 'W': return IETagType.WORD
        if code == 'N': return IETagType.NOTE
        raise ValueError


class IETag:

    def __init__(self, type, text=None, bases=None, url=None):
        self.type = type
        self.text = text
        self.bases = bases
        self.url = url

    def pname(self):
        s = self.type.name
        if self.bases is not None:
            s += '(' + self.bases + ')'
        if self.text is not None:
            s += " '" + self.text + "'"
        if self.url is not None:
            s += ' @' + self.url
        return s

    def diff_tup(self):
        # (n|w|t, state, bases)
        if self.type == IETagType.NOTE:
            type = 'n'
            text = self.text
        elif self.type == IETagType.WORD:
            type = 'w'
            text = self.text
        else: # IETagType.TAG
            type = 't'
            text = self.text.replace('/', '|')
            # 'meta/misc/cool' => 'meta|misc|cool'
            # FIXME: this fix is specific to Corbett image tags,
            # so it should be done in ie_fs.py
        return type, text, self.bases

    def __repr__(self):
        return '<IETag %s>' % self.pname()

    def is_tag(self):
        return self.type in {IETagType.AUTO, IETagType.BASED,
                               IETagType.UNBASED}


class IEFolder(object):

    def __init__(self, fs_path, db_date, db_name, mod_datetime):
        self.fs_path = fs_path  # filesystem absolute db_name

        # DbFolder date and db_name suggested by import code
        self.db_date = db_date  # folder date, e.g. 10/07/2017, may be None
        self.db_name = db_name  # the db_name, e.g. 'virginia'

        self.mod_datetime = mod_datetime
        self.images = {}        # IEImage.name -> IEImage
        self.image_insts = {}   # map: IEImageInst.fs_path -> IEImageInst
        self.msgs = []          # list of IEMsg
        self.tags = []          # list of IETag

    def add_image(self, ie_image):
        self.images[ie_image.name] = ie_image

    def add_tag(self, ie_tag):
        self.tags.append(ie_tag)

    def pname(self):
        return '%s %s' % (
            str(self.db_date) if self.db_date is not None else '-',
            self.db_name)

    def __repr__(self):
        return '<IEFolder %s>' % self.pname()

thumbnail_exts = [ '.jpg', '.jpg-hi' ] # TODO: silly PIL doesn't do TIFFs
exif_exts = [ '.tif', '.psd', '.jpg', '.jpg-hi' ]

class IEImage(object):

    def __init__(self, ie_folder, name):

        self.ie_folder = ie_folder
        self.name = name        # <seq>[<suffix>] (copied to Fs/DbImage)
        self.msgs = []          # list of IEMsg
        self.insts = {}         # extension -> list of IEImageInst

        self.newest_inst_with_thumbnail = None  # updated by IEImageInst init
        self.thumbnail = None   # set by bg_proc_ie_work_item() > get_ie_image_thumbnails()
        self.tags = []          # list of IETag

    def add_tag(self, ie_tag):
        self.tags.append(ie_tag)

    def pname(self):
        return '%s|%s' % (self.ie_folder.pname(), self.name)

    def __repr__(self):
        return '<IEImage %s>' % self.pname()

    def set_attrs_from_exiftool_json(self, item):
        if 'ImageSize' in item:
            w, h = item['ImageSize'].split('x')
            self.image_size = (int(w), int(h))
        if 'Subject' in item:
            for tag in item['Subject']:
                self.add_tag(
                    IETag(IETagType.UNBASED, text=tag, bases='band,person'))
        else:
            pass
        pass

class IEImageInst(object):

    def __init__(self, ie_image, fs_path, ext, mod_datetime):

        self.ie_image = ie_image
        self.fs_path = fs_path  # filesystem full pathname, key in ie_folder.image_insts
        self.ext = ext          # key in ie_image.insts, e.g '.jpg', '.jpg-hi'
        self.mod_datetime = mod_datetime
        self.msgs = []          # list of IEMsg

        # add to the IEFolder's pathname => IEImageInst map
        ie_image.ie_folder.image_insts[fs_path] = self

        if (ext in thumbnail_exts
        and (
            ie_image.newest_inst_with_thumbnail is None
            or mod_datetime > ie_image.newest_inst_with_thumbnail.mod_datetime
        )):
            ie_image.newest_inst_with_thumbnail = self

    def pname(self):
        return '%s|%s' % (self.ie_image.pname(), self.ext)

    def __repr__(self):
        return '<IEImageInst %s>' % self.pname()

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
    '-FocalLength',
    '-Flash',
    '-ExposureTime',
    '-FNumber',
    '-ISO',
    '-XMP-dc:subject',
    '-XMP-lr:hierarchicalSubject'
]

def _get_exiftool_json(argv):
    """ Run exiftool on <argv> and return a list of dictionariess. """
    try:
        outb = subprocess.check_output(argv)
        #FIXME: diagnostic if no exiftool
    except Exception as ed:
        pass
    outs = str(outb)[2:-5]\
        .replace(r'\n', '').replace(r'\r', '').replace(r"\'", "'")
    try:
        exiftool_json = json.loads(outs)
    except:
        pass
    return exiftool_json

ie_image_set0 = None

def get_ie_image_exifs(ie_image_set, pub):
    """ Get exif data for all the images in <ie_image_set>.

        deletes images from the set as their exifs are processed
    """

    def proc_exiftool_json(ie_image_set, ext_paths, exiftool_json):
        for item in exiftool_json:
            fs_path = item['SourceFile']
            if fs_path in ext_paths:
                ie_image_inst = ext_paths[fs_path]
                ie_image = ie_image_inst.ie_image
                if ie_image in ie_image_set:
                    ie_image_inst.ie_image.set_attrs_from_exiftool_json(item)
                    ie_image_set.remove(ie_image_inst.ie_image)

    # attempt in the order of exif_exts
    global ie_image_set0
    ie_image_set0 = ie_image_set.copy()
    for ext in exif_exts:
        if len(ie_image_set) == 0:
            break
        # collect IEImageInsts and their directories
        dir_insts = {} # map: directory pathname => list of IEImageInst
        ext_paths = {} # map: fs_path => image_inst for images w/ this extension
        for ie_image in ie_image_set:
            if ext in ie_image.insts:
                for ie_image_inst in ie_image.insts[ext]:
                    inst_path = (os.path.abspath(ie_image_inst.fs_path)
                        .replace('\\', '/'))
                    inst_path = os.path.splitdrive(inst_path)[1]
                    ext_paths[inst_path] = ie_image_inst
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
                len0 = len(ie_image_set)
                argv = list(_exiftool_args)
                argv.append(os.path.join(dir_path, '*' + fs_ext))
                exiftool_json = _get_exiftool_json(argv)
                proc_exiftool_json(ie_image_set, ext_paths, exiftool_json)
                pub('ie.sts imported tags', data = len0 - len(ie_image_set))
            else:
                # run exiftools on <file1> <file2> ...
                while len(worklist) > 0:
                    n = min(len(worklist), 30) # up to 30 files per run
                    sublist, worklist = worklist[:n], worklist[n:]
                    len0 = len(ie_image_set)
                    argv = list(_exiftool_args)
                    for ie_image_inst in sublist:
                        argv.append(ie_image_inst.fs_path)
                    exiftool_json = _get_exiftool_json(argv)
                    proc_exiftool_json(ie_image_set, ext_paths, exiftool_json)
                    pub('ie.sts imported tags', data = len0 - len(ie_image_set))

def get_ie_image_thumbnails(ie_image_set, pub):
    """ extract thumbnails for the images in <ie_image_set>
        deletes images from the set as their thumbnails are proecesed
    """
    pub('ie.sts.import thumbnails', data=len(ie_image_set))
    for ie_image in ie_image_set:
        ie_image_inst = ie_image.newest_inst_with_thumbnail
        assert ie_image_inst is not None
        ie_image.thumbnail = ie_image_inst.get_thumbnail()
        pub('ie.sts imported thumbnails', data=1)
    # clear(ie_image_set) FIXME: why does this fail?

# a std_dirname has the form 'yymmdd db_name'
leading_date_space = re.compile(r'^\d{6,6} ')
leading_date_underscore = re.compile(r'^\d{6,6}_')
leading_date = re.compile(r'^\d{6,6}')

def is_std_dirname(dirname):
    """ return whether dirname is a "standard" directory of image files """
    return True
    # TODO: return leading_date_space.match(dirname) is not None

def proc_std_dirname(dir_pathname, dir_name):
    match = leading_date.match(dir_name)
    if match is None:
        db_date = None
        db_name = dir_name
    else:
        yymmdd = match.group()
        db_date = util.date_from_yymmdd(yymmdd)
        db_name = dir_name[match.end():].lstrip(' ')
    stat_mtime = os.path.getmtime(dir_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)
    folder = IEFolder(dir_pathname, db_date, db_name, mtime)
    if db_date is None:
        folder.msgs.append(IEMsg(IEMsgType.NO_DATE, dir_pathname))
    return folder

def scan_dir_set(dir_set_pathname, test, proc):
    """ return a list of IEFolders representing each directory satisfying test
        the list is sorted by folder fs_name
        test(dir_name) checks whether the directory should be processed
        proc(dir_pathname, dir_name) returns an IEFolder for the directory
    """
    folders = []
    for dir in os.listdir(dir_set_pathname):
        dir_path = os.path.join(dir_set_pathname, dir)
        if os.path.isdir(dir_path) and test(dir):
            folder = proc(dir_path, dir)
            if folder is not None:
                folders.append(folder)
    folders.sort(key=lambda folder: folder.fs_path)
    return folders

def scan_dir_sel(dir_pathname_list, proc):
    """ return a list of IEFolders representing each directory satisfying test
        the list is sorted by fs_name
        proc(dir_pathname, dir_name) returns an IEFolder for the directory
    """

    folders = []
    for dir_path in dir_pathname_list:
        if os.path.isdir(dir_path):
            folder = proc(dir_path, os.path.basename(dir_path))
            if folder is not None:
                folders.append(folder)
    folders.sort(key=lambda folder: folder.fs_path)
    return folders

# recognized image file extensions
img_extensions = [ '.nef', '.tif', '.psd', '.jpg' ]
raw_prefixes = [ 'img_', 'dsc_' ]
ignored_extensions = [ '.zip' ]
ignored_subdirectories = [ 'del' ]
# 'New Text Document.txt'(!) is recognized as a source of folder tags

def add_ie_folder_image_inst(ie_folder, file_path, file_name, high_res, mtime):
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
        if seq in ie_folder.images:
            ie_image = ie_folder.images[seq]
        else:
            ie_image = IEImage(ie_folder, seq)
            ie_folder.images[seq] = ie_image
        ie_image_inst = IEImageInst(ie_image, file_path, ext, mtime)
        if ext not in ie_image.insts:
            ie_image.insts[ext] = [ie_image_inst]
        else:
            ie_image.msgs.append(IEMsg(IEMsgType.EXTRA_INSTS, file_path))
            ie_image.insts[ext].append(ie_image_inst)
    else:
        ie_folder.msgs.append(IEMsg(IEMsgType.UNEXPECTED_FILE, 'file_path'))

def add_ie_folder_name_word_tags(ie_folder, bases):
    """ add tags based on th ewords of the folder's db_name """
    for word in ie_folder.db_name.split(' '):
        ie_folder.add_tag(
            IETag(IETagType.WORD, text=word, bases=bases))

def add_ie_folder_name_tag(ie_folder, bases):
    """ add a tag based on the folder's db_name """
    ie_folder.add_tag(IETag(
        IETagType.BASED, text=ie_folder.db_name, bases=bases))

def scan_std_dir_files(ie_folder):

    def acquire_file(file_path, file_name, high_res):
        got_folder_tags = False
        if file_name == 'New Text Document.txt':
            got_folder_tags = True
            tag_lines = open(file_path, 'r').readlines()
            for tag_line in tag_lines:
                tags = [l.strip(' \n\r') for l in tag_line.split(',')]
                for tag in tags:
                    ie_folder.add_tag(IETag(
                        IETagType.BASED, text=tag, bases='band'))
        elif os.path.isfile(file_path):
            stat_mtime = os.path.getmtime(file_path)
            mtime = datetime.datetime.fromtimestamp(stat_mtime)
            add_ie_folder_image_inst(
                ie_folder, file_path, file_name, high_res, mtime)
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

    assert ie_folder is not None
    got_folder_tags = acquire_dir(ie_folder.fs_path, high_res=False)
    if got_folder_tags:
        # the standard case, where there's a state file with band names
        # and the folder db_name is the venue
        add_ie_folder_name_tag(ie_folder, 'venue')
    else:
        # who knows?
        add_ie_folder_name_word_tags(ie_folder, 'band, venue, place, event')
        ie_folder.msgs.append(
            IEMsg(IEMsgType.NAME_NEEDS_EDIT, ie_folder.db_name))
    # TODO: adjust seq numbers for Nikon 9999 rollover:
    # 0001, 9999 => 10001, 09999

corbett_date = re.compile(r'[0-9]{2,2}_[0-9]{2,2}(&[0-9]{2,2})?_[0-9]{2,2}')
corbett_trailing_date = re.compile(
    r'[0-9]{2,2}_[0-9]{2,2}(&[0-9]{2,2})?_[0-9]{2,2}$')
amper_date = re.compile(r'&[0-9]+')

def proc_corbett_filename(file_pathname, file_name, folders):
    base_name, ext = os.path.splitext(file_name)

    base_name = base_name.lower()
    base, seq = base_name.split('-')
    stat_mtime = os.path.getmtime(file_pathname)
    mtime = datetime.datetime.fromtimestamp(stat_mtime)

    if (len(folders) == 0 or
        base != os.path.basename(folders[-1].fs_path).split('-')[0].lower()
    ):
        # start a new IEFolder
        match = corbett_date.search(base)
        tmatch = corbett_trailing_date.search(base)
        if match is None and tmatch is None:
            db_date = None
            db_name = base.replace('_', ' ')
        else:
            if tmatch is not None:
                date_str = tmatch.group()
                name_str = base[0:tmatch.start()]
            else:
                date_str = match.group()
                s, e = match.start(), match.end()
                if s != 0:
                    pass # does this case happen?
                name_str = base[0:s] + base[e:]
            date_str = amper_date.sub('', date_str)
            month_str, day_str, year_str = date_str.split('_')
            year = int(year_str)
            year += 1900 if year >= 70 else 2000
            month = int(month_str)
            day = int(day_str)
            try:
                db_date = datetime.date(year, month, day)
            except:
                db_date = datetime.date(1941, 12, 7)
                pass
            db_name_words = name_str.split('_')
            db_name = ' '.join(db_name_words).strip(' ')
        ie_folder = IEFolder(file_pathname, db_date, db_name, mtime)
        add_ie_folder_name_word_tags(ie_folder, 'venue, band')
        ie_folder.msgs.append(IEMsg(IEMsgType.TAGS_ARE_WORDS, file_pathname))
        ie_folder.msgs.append(IEMsg(IEMsgType.NAME_NEEDS_EDIT, db_name))
        if db_date is None:
            ie_folder.msgs.append(IEMsg(IEMsgType.NO_DATE, file_pathname))
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
    """ Return a list of IEFolders (each containing IEImages).

        the IEFolders/Images represent the folders and images
            found in file_set_pathname
        the list is sorted by folder.fs_path
        test(file_name)
            checks whether the directory should be processed
        proc(file_pathname, file_name, folders)
            returns an IEImage for the file, and,
        if the filename has a new prefix, adds a new IEFolder to folders
    """
    folders = []
    try:
        os.listdir(file_set_pathname)
    except:
        pass
    for file in os.listdir(file_set_pathname):
        file_path = os.path.join(file_set_pathname, file)
        if os.path.isfile(file_path) and test(file):
            proc(file_path, file, folders)
    folders.sort(key=lambda folder: folder.fs_path)

    return folders

def scan_file_sel(file_pathname_list, proc):
    """ return a list of IEFolders (each containing IEImages)
        representing the folders and images found in file_pathname_list
        the list is sorted by folder fs_path
        test(file_name)
            checks whether the directory should be processed
        proc(file_pathname, file_name, folders)
            returns an IEImage for the file, and,
        if the filename has a new prefix, adds a new IEFolder to folders
    """
    folders = []
    for file_path in file_pathname_list:
        if os.path.isfile(file_path):
            proc(file_path, os.path.basename(file_path), folders)
    folders.sort(key=lambda folder: folder.fs_path)
    return folders
