from os import *
from kivy.logger import Logger

class TmpDirectorySet(object):

    def __init__(self, pathname=''):
        self.pathname = pathname
        self.dirs = []
        self.acquire()
    def acquire(self):
        if not access(self.pathname, R_OK):
            self.online = False
            print('NX ' + self.pathname)
            return
        self.online = True
        l = listdir(self.pathname)
        for d in l:
            dpath = self.pathname + '/' + d
            if path.isdir(dpath):
                td = TmpDirectory(d, dpath)
                self.dirs.append(td)
                print(td.stats())

class TmpDirectory(object):

    img_extensions = ['.jpg', '.tif', '.psd', '.bmp']
    def __init__(self, name, pathname):
        self.name = name
        self.dirs = []
        self.imgs = {}
        self.doc = []
        self.other = []
        self.acquire(pathname)
    def acquire(self, pathname):
        def acquire_dir(pathname, img_extensions, high_res):
            #print('dir.acquire ' + pathname)
            l = listdir(pathname)
            for i in l:
                ipath = pathname + '/' + i
                name, ext = path.splitext(i)
                name = name.lower()
                ext = ext.lower()
                if path.isdir(ipath):
                    self.dirs.append(ipath)
                    acquire_dir(ipath, img_extensions, name == 'hi')
                elif ext in img_extensions:
                    if high_res:
                        ext += '-hi'
                    if not ext in self.imgs.keys():
                        self.imgs[ext] = [i]
                    else:
                        self.imgs[ext].append(ipath)
                elif name == 'new text document':
                    self.doc.append(ipath)
                elif ext != '.zip':
                    self.other.append(ipath)
        acquire_dir(pathname, ['.jpg', '.tif', '.psd', '.bmp'], high_res = False)
    def stats(self):
        imgs = ''
        for k, l in self.imgs.items():
            imgs += ', ' + str(len(l)) + ' ' + k[1:] + 's'
        return self.name + ': ' + str(len(self.dirs)) + ' dirs' + imgs + ', ' + \
               str(len(self.doc)) + ' doc, ' + str(len(self.other)) + ' other'

class TmpImage(object):

    def __init__(self, name, dir):
        self.name = name
        dir.dirs.append(self) # FIXMEL check for duplicates?

def tmp_test():
    print('hello')
    TmpDirectorySet('q:/photos')
    td = TmpDirectorySet('e:/photos')
    print(td)