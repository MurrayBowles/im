''' no longer used '''

from enum import Enum
import datetime
from kivy.logger import Logger

class ChildNode(object):

    def _parent_dict(self):
        raise NotImplementedError()

    def _key(self):
        raise NotImplementedError()

    def _set_key(self, new_key):
        raise NotImplementedError()

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
        Logger.info('mem_db: delete %s', str(self))
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
        Logger.info('mem_db: new %s', str(self))

    def __str__(self):
        return self.type.name + "'" + self.fs_path + "'"

    def set_fs_path(self, fs_path):
        Logger.info('mem_db: %s fs_path := %s', str(self), fs_path)
        self.fs_path = fs_path

    def set_enabled(self, enabled):
        Logger.info('mem_db: %s enabled := %s', str(self), str(enabled))
        self.enabled = enabled

    def set_present(self, present):
        Logger.info('mem_db: %s present := %s', str(self), str(present))
        self.present = present

    def set_last_synched(self):
        now = datetime.datetime.now()
        Logger.info('mem_db: %s last_synched := %s', str(self), str(now))
        self.last_synched = now


class FsDir(ChildNode):

    def _parent_dict(self):
        return self.parent.children if self.parent else self.dir_set.fs_dirs

    def _key(self):
        return self.name

    def _set_key(self, new_key):
        self.name = new_key

    def __init__(self, dir_set, name, parent=None):
        self.dir_set = dir_set
        self.name = name
        self.parent = parent
        self._add()
        self.children = {}
        self.db_dir = None         # DB directory
        self.last_synched = None
        self.fs_imgs = {}
        Logger.info('mem_db: new %s', str(self))

    def __str__(self):
        if self.parent:
            return str(self.parent) + '/' + self.name
        else:
            return str(self.dir_set) + ':' + self.name

    def set_db_dir(self, db_dir):
        Logger.info('mem_db: %s db_dir := %s', str(self), str(db_dir))
        if self.db_dir:
            self.db_dir.del_fs_dir(self)
        db_dir.add_fs_dir(self)
        self.db_dir = db_dir

    def set_last_synched(self):
        now = datetime.datetime.now()
        Logger.info('mem_db: %s last_synched := %s', str(self), str(now))
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
        Logger.info('mem_db: new %s', str(self))

    def __str__(self):
        return str(self.fs_dir) + '/' + self.fs_img

    def set_db_img(self, db_img):
        Logger.info('mem_db: %s db_img := %s', str(self), str(db_img))
        if self.db_img:
            self.db_img.del_fs_img(self)
        db_img.add_fs_img(self)
        self.db_img = db_img


class Tag(object):

    root = {}   # name -> tag

    def _add_to_parent(self, parent):
        if self.name in parent.children:
            raise KeyError
        if parent in self.parents.values():
            raise ValueError
        self.parents[parent.name] = parent
        parent.children[name] = self

    def _del_from_parent(self, parent):
        pass #fixme

    def __init__(self, name, parent=None):
        self.name = name
        self.children = {}  # name -> Tag
        self.parents = {}   # naem -> Tag
        self.db_dirs = set()
        self.db_imgs = set()
        self.description = None
        Logger.info('mem_db: new %s', str(self))

    def __str__(self):
        return self.name + ('|' + str(self.parent) if self.parent else '')

    def set_name(self, name):
        Logger.info('mem_db: %s name := %s', str(self), name)
        self._rename(name)

    @classmethod
    def log(cls, tags=None, pfx='', ind='    '):
        def log0(tags, pfx, ind):
            for t in tags.values():
                Logger.info('mem_db: %s', pfx + str(t))
                log0(t.children, pfx=pfx + ind, ind=ind)
                for d in t.db_dirs:
                    Logger.info('mem_db: %sD %s', pfx + ind, str(d))
                for i in t.db_imgs:
                    Logger.info('%mem_db: sI %s', pfx + ind, str(i))
        if not tags:
            tags = cls.root
        log0(tags, pfx, ind)


class DbDir(ChildNode):
    dirs = {}
    root_tag = Tag('$')

    def _parent_dict(self):
        return self.parent.children if self.parent else DbDir.dirs

    def _key(self):
        return self.name

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self._add()
        self.children = {}
        self.fs_dirs = []
        self.db_imgs = {}
        self.description = None
        self.db_tag = Tag(name, parent.db_tag if parent else DbDir.root_tag)
        Logger.info('mem_db: new %s', str(self))

    def delete(self):
        self.db_tag.delete()
        ChildNode.delete(self)

    def __str__(self):
        return self.name + ('|' + self.parent if self.parent else '|$')

    def set_name(self, name):
        Logger.info('mem_db: %s name = %s', str(self), name)
        self._rename(name)

    def add_fs_dir(self, fs_dir):
        Logger.info('mem_db: add %s to %s', str(fs_dir), str(self))
        self.fs_dirs.append(fs_dir)

    def del_fs_dir(self, fs_dir):
        Logger.info('mem_db: del %s from %s', str(fs_dir), str(self))
        self.fs_dirs.remove(fs_dir)

    def add_tag(self, tag):
        Logger.info('mem_db: add tag %s to %s', str(tag), str(self))
        tag.db_dirs.add(self)

    def del_tag(self, tag):
        Logger.info('mem_db: del tag %s from %s', str(tag), str(self))
        tag.db_dirs.remove(self)


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
        Logger.info('mem_db: new %s', str(self))

    def __str__(self):
        return self.name + '|' + str(self.db_dir)

    def set_name(self, name):
        Logger.info('mem_db: %s name = %s', str(self), name)
        self._rename(name)

    def add_fs_img(self, fs_img):
        Logger.info('mem_db: add %s to %s', str(fs_img), str(self))
        self.fs_imgs.append(fs_img)

    def del_fs_img(self, fs_img):
        Logger.info('mem_db: del %s from %s', str(fs_img), str(self))
        self.fs_imgs.remove(fs_img)


def mem_db_test():
    ds = DirSet(DirSetType.Internal, 'e:/photos')
    d = FsDir(ds, 'foo')
    dc = FsDir(ds, '1', d)
    i = FsImg(dc, '120344-1234')
    for x in dc.fs_imgs.values():
        Logger.info('mem_db: %s', str(x))
    i.delete()
    for x in dc.fs_imgs.values():
        Logger.info('mem_db: %s', str(x))
    t = Tag('venues')
    gt = Tag('gilman', t)
    Tag.log(pfx='tags: ')
    ddc = DbDir('foo-1')
    dc.set_db_dir(ddc)
    ddc.add_tag(gt)
    Tag.log(pfx='tags2:  ')
    for x in ddc.fs_dirs:
        Logger.info('mem_db: %s', str(x))
    di = DbImg(ddc, '120344-1234')
    i.set_db_img(di)
