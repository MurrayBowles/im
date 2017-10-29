''' import/export folders/images from/to the file system '''

from enum import Enum
import io
import logging
import os

#from rawkit.raw import Raw
#from rawphoto.nef import Nef
import exifread
from PIL import Image #pillow
import PIL.ExifTags

from ie_cfg import IECfg, IEReport


class IEFolderSet(object):

    def __init__(self, pathname=''):
        self.pathname = pathname
        self.folders = []
        self.acquire()

    def acquire(self):
        if not os.access(self.pathname, os.R_OK):
            self.online = False
            print('NX ' + self.pathname)
            return
        self.online = True
        l = os.listdir(self.pathname)
        for d in l:
            dpath = self.pathname + '/' + d
            if os.path.isdir(dpath):
                tf = IEFolder(d, dpath)
                self.folders.append(tf)
                logging.debug('acquired folder: %s', tf.stats())


class IEFolder(object):

    def __init__(self, date, name, pathname):
        self.date = date
        self.name = name
        self.dirs = []
        self.imgs = {}
        self.thumbs = {}
        self.doc = []
        self.other = []
        self.acquire(pathname)

    def acquire(self, pathname):
        def acquire_dir(pathname, img_extensions, high_res):
            logging.debug('IEFolder.acquire_dir(%s)', pathname)
            l = os.listdir(pathname)
            for i in l:
                ipath = pathname + '/' + i
                name, ext = os.path.splitext(i)
                name = name.lower()
                ext = ext.lower()
                if os.path.isdir(ipath):
                    self.dirs.append(ipath)
                    acquire_dir(ipath, img_extensions, name == 'hi')
                elif ext in img_extensions:
                    if high_res:
                        ext += '-hi'
                    if not ext in self.imgs.keys():
                        self.imgs[ext] = [ipath]
                    else:
                        self.imgs[ext].append(ipath)
                elif name == 'new text document':
                    self.doc.append(ipath)
                elif ext != '.zip':
                    self.other.append(ipath)
        acquire_dir(pathname, ['.jpg', '.tif', '.psd', '.bmp', '.nef'], high_res = False)

    def get_thumbs(self):
        def get_thumb(ipath):
            i = Image.open(ipath)
            i.thumbnail((200, 200))
            bi = io.BytesIO()
            i.save(bi, format='jpeg')
            return bi.getvalue()
        if '.jpg' in self.imgs:
            for ipath in self.imgs['.jpg']:
                self.thumbs[ipath] = get_thumb(ipath)

    def stats(self):
        imgs = ''
        for k, l in self.imgs.items():
            imgs += ', ' + str(len(l)) + ' ' + k[1:]
        return self.name + ': ' + str(len(self.dirs)) + ' dirs' + imgs + ', ' + \
               str(len(self.doc)) + ' doc, ' + str(len(self.other)) + ' other'


class IEImage(object):

    def __init__(self, name, dir):
        self.name = name
        dir.dirs.append(self) # FIXME: check for duplicates?


def import_export(ie_cfg, progress, db):
    ''' transfers data between directories and image files
        and folder and image objects in the database

        uses .source_type and .paths, and the import/export flags
        from ie_cfg

        calls progress to report progress:
            progress('ie.begun', #items)
            progress('ie.step)
            progress('ie.done')

        accesses the database db's methods (db.py)

        returns an IEReport list
    '''
    reports = []
    return reports

def _ie_test():
    if False:
        print('hello')
        IEFolderSet('q:/photos')
        iefs = IEFolderSet('e:/photos')
        print(iefs)
        print('hello')
    if False:
        ief = IEFolder('tmp', 'E:\\photos\\170902 48th')
        ief.get_thumbs()
        print('hi')
    if False: #rawphoto
        n = Nef(filename='E:\\photos\\170902 48th\\nefs\\DSC_5084.NEF')
        print('hello')
    if False: #exifread
        f = open('E:\\photos\\170902 48th\\lo\\170902-5085.jpg', mode='rb')
        tags = exifread.process_file(f)
        print('ha')
    if False: #pillow
        i = Image.open('E:\\photos\\170902 48th\\lo\\170902-5085.jpg')
        exif = i._getexif()
        exif2 = {
            PIL.ExifTags.TAGS[k]: v
            for k, v in exif.items()
            if k in PIL.ExifTags.TAGS
        }
        si = i.copy()
        si.thumbnail((200, 200))
        bi = io.BytesIO()
        si.save(bi, format='jpeg')
        by = bi.getvalue()
        for segment, content in i.applist:
            marker, body = content.split(b'\x00', 1)
            if segment == 'APP1' and marker == b'http://ns.adobe.com/xap/1.0/':
                # parse the XML string with any method you like
                print('HEY')
        print('ha')


if __name__ == '__main__':
    _ie_test()


