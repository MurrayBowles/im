from enum import Enum
import datetime
from kivy.logger import Logger

class ChildNode(object):
    ''' subclasses provide
        _parent_dict()          returns the parent dictionary
        _key()                  returns the dictionary key
        _set_key(new_key)       sets the dictionary key
    '''
    def _ck_dup(self, key):
        d = self._parent_dict()
        if key in d:
            raise KeyError
        return d
    def _add(self):
        k = self._key()
        d = self._ck_dup(k)
        d[k] = self
    def _del(self):
        k = self._key()
        d = self._parent_dict()
        d.pop(k)
    def _rename(self, new_key):
        d = self._ck_dup(new_key)
        d.pop(self._key())
        d._set_key(new_key)
        d[new_key] = new_key
    def delete(self):
        Logger.info('FS: delete %s', str(self))
        self._del()

class DirSetType(Enum):
    Internal = 1
    External = 2
    CD = 3
    Glacier = 4

class DirSet(ChildNode):
    dir_sets = {}       # name -> DirSet
    def _parent_dict(self):
        return DirSet.dir_sets
    def _key(self):
        return self.fs_path
    def __init__(self, type, fs_path):
        self.type = type
        self.description = None
        self.fs_path = fs_path
        self._add()
        self.enabled = False
        self.present = False
        self.last_synched = None
        self.fs_dirs = {}
        Logger.info('FS: new %s', str(self))
    def __str__(self):
        return self.type.name + "'" + self.fs_path + "'"
    def set_fs_path(self, fs_path):
        Logger.info('FS: %s fs_path := %s', str(self), fs_path)
        self.name = name
    def set_enabled(self, enabled):
        Logger.info('FS: %s enabled := %s', str(self), str(enabled))
        self.enabled = enabled
    def set_present(self, present):
        Logger.info('FS: %s present := %s', str(self), str(present))
        self.present = present
    def set_last_synched(self):
        now = datetime.now()
        Logger.info('FS: %s last_synched := %s', str(self), str(now))
        self.last_synched = now

class FsDir(ChildNode):
    def _parent_dict(self):
        return self.parent.children if self.parent else self.dir_set.fs_dirs
    def _key(self):
        return self.name
    def _set_key(self, new_key):
        self.name = new_key
    def __init__(self, dir_set, name, parent = None):
        self.dir_set = dir_set
        self.name = name
        self.parent = parent
        self._add()
        self.children = {}
        self.db_dir = None         # DB directory
        self.last_synched = None
        self.fs_imgs = {}
        Logger.info('FS: new %s', str(self))
    def __str__(self):
        if self.parent:
            return str(self.parent) + '/' + self.name
        else:
            return str(self.dir_set) + ':' + self.name
    def set_db_dir(self, db_dir):
        Logger.info('DB: %s db_dir := %s', str(self), str(db_dir))
        if self.db_dir:
            self.db_dir.del_fs_dir(self)
        db_dir.add_fs_dir(self)
        self.db_dir = db_dir
    def set_last_synched(self):
        now = datetime.now()
        Logger.info('DB: %s last_synched := %s', str(self), str(now))
        self.last_synched = now

class FsImg(ChildNode):
    def _parent_dict(self):
        return self.fs_dir.fs_imgs
    def _key(self):
        return self.fs_img
    def __init__(self, fs_dir, fs_img):
        self.fs_dir = fs_dir
        self.fs_img = fs_img
        self._add()
        self.db_img = None
        Logger.info('FS: new %s', str(self))
    def __str__(self):
        return str(self.fs_dir) + '/' + self.fs_img
    def set_db_img(self, db_img):
        Logger.info('DB: %s db_img := %s', str(self), str(db_img))
        if self.db_img:
            self.db_img.del_fs_img(self)
        db_img.add_fs_img(self)
        self.db_img = db_img

class Tag(ChildNode):
    root = {}   # name -> tag
    def _parent_dict(self):
        return self.parent.children if self.parent else Tag.root
    def _key(self):
        return self.name
    def _set_key(self, key):
        self.name = key
    def __init__(self, name, parent = None):
        self.name = name
        self.parent = parent
        self._add()
        self.children = {}
        self.description = None
        Logger.info('DB: new %s', str(self))
    def __str__(self):
        return self.name + ('|' + str(self.parent) if self.parent else '')
    def set_name(self, name):
        Logger.info('DB: %s name := %s', str(self), name)
        self._rename(name)

class DbDir(ChildNode):
    dirs = {}
    def _parent_dict(self):
        return self.parent.children if self.parent else DbDir.dirs
    def _key(self):
        return self.name
    def __init__(self, name, parent = None):
        self.name = name
        self.parent = parent
        self._add()
        self.children = {}
        self.fs_dirs = []
        self.db_imgs = {}
        self.description = None
        Logger.info('DB: new %s', str(self))
    def __str__(self):
        return self.name + '|' + (self.parent if self.parent else '')
    def set_name(self, name):
        Logger.info('DB: %s name = %s', str(self), name)
        self._rename(name)
    def add_fs_dir(self, fs_dir):
        Logger.info('DB: add %s to %s', str(fs_dir), str(self))
        self.fs_dirs.append(fs_dir)
    def del_fs_dir(self, fs_dir):
        Logger.info('DB: del %s from %s', str(fs_dir), str(self))
        self.fs_dirs.remove(fs_dir)

class DbImg(ChildNode):
    def _parent_dict(self):
        return self.db_dir.db_imgs
    def _key(self):
        return self.name
    def _set_key(self, new_key):
        self.name = new_key
    def __init__(self, db_dir, name):
        self.name = name
        self.db_dir = db_dir
        self._add()
        self.fs_imgs = []
        self.description = None
        Logger.info('DB: new %s', str(self))
    def __str__(self):
        return self.name + '|' + str(self.db_dir)
    def set_name(self, name):
        Logger.info('DB: %s name = %s', str(self), name)
        self._rename(name)
    def add_fs_img(self, fs_img):
        Logger.info('DB: add %s to %s', str(fs_img), str(self))
        self.fs_imgs.append(fs_img)
    def del_fs_img(self, fs_img):
        Logger.info('DB: del %s from %s', str(fs_img), str(self))
        self.fs_img.remove(fs_img)