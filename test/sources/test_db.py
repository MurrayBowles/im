from datetime import date, datetime
import pytest

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from db import *
session = open_mem_db()


class _Tester(object):
    """ object basic key/relationship tester """

    def __init__(self):
        self.key = None
        self.obj = None
        self.dep_classes = []
        self.dep_testers = []
        self.dep_objs = []

    def mk_key(self):
        """ return a new generated primary key, or None if the key is autogenerated. """
        return None

    def get_key(self, obj):
        """ return obj's primary key """
        return obj.id

    def mk_key2(self):
        """ return a new generated secondary key, or None. """
        return None

    def find(self, key):
        """ lookup primary key and return the object found (or None). """
        raise NotImplementedError

    def _do_find(self, key):
        """ lookup primary key and return the object found (or None). """
        return self.find(key)

    def find2(self, key2):
        """ lookup secondary key and return the object found (or None). """
        raise NotImplementedError

    def _do_find2(self, key2):
        """ lookup secondary key and return the object found (or None). """
        return  self.find2(key2)

    def test_deps(self, obj):
        """ test the dependency linkage. """
        pass

    def create(self, session, key, key2):
        """ create and return a new object(DbTextType.URL)ject.
        key will be None if th eprimary key is autogenerated
        key2 will be None if htere is no secondary key
        """
        raise NotImplementedError

    def add(self):
        for dep_cls in self.dep_classes:
            dep_tester = dep_cls()
            self.dep_testers.append(dep_tester)
            dep_obj = dep_tester.add()
            self.dep_objs.append(dep_obj)
        key = self.mk_key()
        if key is not None:
            assert self._do_find(key) is None
        key2 = self.mk_key2()
        if key2 is not None:
            assert self._do_find2(key2) is None
        if hasattr(self, 'get'):
            obj, new_obj = self.get(session, key, key2)
            assert new_obj
        else:
            obj = self.create(session, key, key2)
        assert obj is not None
        session.commit()
        if hasattr(self, 'get'):
            found_obj2, new_obj = self.get(session, key, key2)
            assert not new_obj
            assert found_obj2 == obj
        key = self.get_key(obj)
        found_obj = self._do_find(key)
        assert found_obj is obj
        if key2 is not None:
            found_obj2 = self._do_find2(key2)
            assert found_obj2 is obj
        self.key = key
        self.key2 = key2
        self.obj = obj
        self.test_deps(obj)
        return obj

    def delete(self):
        found_obj = self._do_find(self.key)
        assert found_obj is self.obj
        session.delete(self.obj)
        assert self._do_find(self.key) is None
        if self.key2 is not None:
            assert self._do_find2(self.key2) is None
        session.commit()
        self.key = None
        self.key2 = None
        self.obj = None
        for dep_tester in self.dep_testers:
            dep_tester.delete()


def _mk_date():
    return date.today()

_name_seq = 0
def _mk_name(base):
    global _name_seq
    _name_seq += 1
    return base + str(_name_seq)


class _DbFolder_Tester(_Tester):

    def mk_key2(self):
        return (_mk_date(), _mk_name('folder'))

    def create(self, session, key, key2):
        return DbFolder.add(session, date=key2[0], name=key2[1])

    def get(self, session, key, key2):
        res = DbFolder.get(session, date=key2[0], name=key2[1])
        return res

    def find(self, key):
        res =  session.query(DbFolder).filter_by(id=key).first()
        return res

    def find2(self, key2):
        return DbFolder.find(session, key2[0], key2[1])


class _DbCollection_Tester(_Tester):

    def mk_key2(self):
        return _mk_name('collection')

    def create(self, session, key, key2):
        collection = DbCollection.add(session, name=key2)
        return collection

    def find(self, key):
        return  session.query(DbCollection).filter_by(id=key).first()

    def find2(self, key):
        return DbCollection.find(session, key)


class _DbImage_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_DbFolder_Tester]

    def mk_key2(self):
        return (self.dep_objs[0], _mk_name(''))

    def create(self, session, key, key2):
        return DbImage.add(session, folder=key2[0], name=key2[1])

    def get(selfself, session, key, key2):
        return DbImage.get(session, folder=key2[0], name=key2[1])

    def find(self, key):
        res = session.query(DbImage).filter_by(id=key).first()
        return res

    def find2(self, key):
        return DbImage.find(session, key[0], key[1])


class _DbFolderThumb_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_DbImage_Tester]

    def create(self, session, key, key2):
        folder = DbFolder.add(
            session, date=_mk_date(), name=_mk_name('folder')
        )
        folder.thumbnail = self.dep_objs[0]
        return folder

    def find(self, key):
        return  session.query(DbFolder).filter_by(id=key).first()

    def test_deps(self, obj):
        assert obj.thumbnail is self.dep_objs[0]


class _DbCollectionThumb_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_DbImage_Tester]

    def create(self, session, key, key2):
        collection = DbCollection.add(session, name=_mk_name('collection'))
        collection.thumbnail=self.dep_objs[0]
        return collection

    def find(self, key):
        return  session.query(DbCollection).filter_by(id=key).first()

    def test_deps(self, obj):
        assert obj.thumbnail is self.dep_objs[0]


class _DbCollectionImage_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_DbImage_Tester]

    def create(self, session, key, key2):
        collection = DbCollection.add(session, name=_mk_name('collection'))
        collection.images=[self.dep_objs[0]]
        return collection

    def find(self, key):
        return  session.query(DbCollection).filter_by(id=key).first()

    def test_deps(self, obj):
        image = self.dep_objs[0]
        assert obj.images[0] is image
        assert image.collections[0] is obj


class _DbTag_Tester(_Tester):

    def mk_key2(self):
        return _mk_name('tag')

    def create(self, session, key, key2):
        tag = DbTag.add(session, name=key2)
        return tag

    def get(self, session, key, key2):
        return DbTag.get(session, key2)

    def find(self, key):
        return DbTag.find_id(session, key)

    def find2(self, key2):
        return DbTag.find(session, key2)


class _DbTagLowered_Tester(_DbTag_Tester):

    def mk_key2(self):
        return _mk_name('TAG')

    def get(self, session, key, key2):
        return DbTag.get(session, key2.lower())

    def find2(self, key2):
        return DbTag.find(session, key2.lower())


class _DbTagRaised_Tester(_DbTag_Tester):

    def mk_key2(self):
        return _mk_name('tag')

    def get(self, session, key, key2):
        return DbTag.get(session, key2.upper())

    def find2(self, key2):
        return DbTag.find(session, key2.upper())


class _DbTagParent_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_DbTag_Tester]

    def mk_key2(self):
        return _mk_name('child'), self.dep_objs[0]

    def create(self, session, key, key2):
        tag = DbTag.add(session, parent=key2[1], name=key2[0])
        return tag

    def find(self, key):
        return DbTag.find_id(session, key)

    def find2(self, key2):
        return DbTag.find(session, key2[0], parent=key2[1])

    def test_deps(self, obj):
        assert obj.parent is self.dep_objs[0]
        assert self.dep_objs[0].children[0] is obj
        l = DbTag.find_flat(session, obj.parent.name)
        assert len(l) == 1
        assert l[0] is obj.parent
        l = DbTag.find_flat(session, obj.name)
        assert len(l) == 1
        assert l[0] is obj


class _DbTagExpr_Tester(_Tester):

    def mk_key2(self):
        return 'child', 'parent'

    def create(self, session, key, key2):
        tag = DbTag.get_expr(session, key2[1] + '|' + key2[0])
        return tag

    def find(self, key):
        return DbTag.find_id(session, key)

    def find2(self, key2):
        return DbTag.find_expr(session, key2[1] + '|' + key2[0])

    def test_deps(self, obj):
        assert obj.parent is not None
        assert obj.parent.name == 'parent'
        assert obj.name == 'child'


class _DbTagReplacement_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_DbTag_Tester]

    def create(self, session, key, key2):
        tag = DbTag.add(
            session, parent=None, name=_mk_name('tag'),
            tag_type=DbTagType.REPLACED_BY, base_tag=self.dep_objs[0])
        return tag

    def find(self, key):
        return session.query(DbTag).filter_by(id=key).first()

    def test_deps(self, obj):
        assert obj.base_tag is self.dep_objs[0]


class _DbNoteType_Tester(_Tester):

    def create(self, session, key, key2):
        note_type = DbNoteType.add(
            session, name=_mk_name('notetype'), text_type=DbTextType.TEXT)
        return note_type

    def find(self, key):
        return DbNoteType.find_id(session, key)


class _FsTagSource_Tester(_Tester):

    def mk_key2(self):
        return _mk_name('desc')

    def create(self, session, key, key2):
        return FsTagSource.add(session, description=key2)

    def get(self, session, key, key2):
        return FsTagSource.get(session, description=key2)

    def find(self, key):
        return  FsTagSource.find_id(session, key)

    def find2(self, key2):
        return FsTagSource.find(session, key2)


class _FsTagMapping_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_FsTagSource_Tester, _DbTag_Tester]

    def mk_key(self):
        return (self.dep_objs[0], _mk_name('text'))

    def get_key(self, obj):
        return (obj.tag_source, obj.text)

    def create(self, session, key, key2):
        return FsTagMapping.add(
            session, tag_source=key[0], text=key[1],
            binding=FsTagBinding.BOUND, db_tag=self.dep_objs[1])

    def find(self, key):
        return FsTagMapping.find(session, key[0], key[1])


class _FsSource_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_FsTagSource_Tester]

    def mk_key2(self):
        return (_mk_name('label'), _mk_name('path'))

    def create(self, session, key, key2):
        source = FsSource.add(
            session,
            volume=key2[0],
            path=key2[1],
            source_type=FsSourceType.DIR,
            readonly=False,
            tag_source=self.dep_objs[0]
        )
        return source

    def find(self, key):
        return FsSource.find_id(session, key)

    def find2(self, key2):
        return FsSource.find(session, key2[0], key2[1])


class _FsFolder_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [
            _FsSource_Tester,
            _DbFolder_Tester
        ]

    def mk_key2(self):
        return (self.dep_objs[0], _mk_name('name'))

    def create(self, session, key, key2):
        source = FsFolder.add(
            session,
            source=key2[0],
            name=key2[1],
            db_folder=self.dep_objs[1]
        )
        return source

    def get(self, session, key, key2):
        source = FsFolder.get(
            session,
            source=key2[0],
            name=key2[1],
            db_folder=self.dep_objs[1]
        )
        return source

    def find(self, key):
        return  session.query(FsFolder).filter_by(id=key).first()

    def find2(self, key2):
        return FsFolder.find(session, source=key2[0], name=key2[1])

    def test_deps(self, obj):
        assert obj.source is self.dep_objs[0]
        assert obj.source.folders[0] is obj
        assert obj.db_folder is self.dep_objs[1]
        assert obj.db_folder.fs_folders[0] is obj


class _FsFolderTag_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [_FsFolder_Tester, _DbTag_Tester]

    def mk_key2(self):
        return (self.dep_objs[0], FsTagType.TAG, _mk_name('text'))

    def create(self, session, key, key2):
        item_tag = FsItemTag.add(
            session,
            item=key2[0], idx=0,idx_range=(0,0),
            type=key2[1], text=key2[2], bases=None,
            binding=FsTagBinding.BOUND, source=FsItemTagSource.FSTS,
            db_tag = self.dep_objs[1]
        )
        return item_tag

    def get_key(self, obj):
        return (obj.item, obj.idx)

    def find(self, key):
        obj = FsItemTag.find_idx(session, item=key[0], idx=key[1])
        return obj

    def find2(self, key2):
        l = FsItemTag.find_text(session, type=key2[1], text=key2[2])
        return l[0] if len(l) == 1 else None

    def test_deps(self, obj):
        assert obj.item is self.dep_objs[0]
        assert self.dep_objs[0].item_tags[0] is obj
        assert obj.db_tag is self.dep_objs[1]


class _FsImage_Tester(_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [
            _FsFolder_Tester,
            _DbImage_Tester
        ]

    def mk_key2(self):
        return (self.dep_objs[0], _mk_name(''))

    def create(self, session, key, key2):
        return FsImage.add(
            session,
            folder=key2[0],
            name=key2[1],
            db_image=self.dep_objs[1]
        )

    def get(self, session, key, key2):
        return FsImage.get(
            session,
            folder=key2[0],
            name=key2[1],
            db_image=self.dep_objs[1]
        )

    def find(self, key):
        return  session.query(FsImage).filter_by(id=key).first()

    def find2(self, key2):
        return FsImage.find(session, key2[0], key2[1])

    def test_deps(self, obj):
        assert obj.folder is self.dep_objs[0]
        assert obj.folder.images[0] is obj
        assert obj.db_image is self.dep_objs[1]
        assert obj.db_image.fs_images[0] is obj


class _FsImageTag_Tester(_FsFolderTag_Tester):

    def __init__(self):
        _Tester.__init__(self)
        self.dep_classes = [
            _FsImage_Tester
        ]

def test_classes():
    classes = _Tester.__subclasses__()
    # classes = [ _FsFolder_Tester ]
    for cls in classes:
        test_obj = cls()
        # print(str(cls))
        obj = test_obj.add()
        test_obj.delete()
        pass

def _test_association(tester_classes, list_names):
    testers = []
    objs = []
    for tester_cls in tester_classes:
        # create a _Tester for the class
        tester = tester_cls()
        testers.append(tester)
        # call its add function
        objs.append(tester.add())
    for j in range(2):
        # check here vs there (j == 0) and there vs here (j == 1)
        here = objs[j]
        here_list = getattr(here, list_names[j])
        there = objs[1 - j]
        there_list = getattr(there, list_names[1 - j])
        assert len(here_list) == 0
        assert len(there_list) == 0
        here_list.append(there)
        assert there_list[0] is here
        here_list.pop()
        assert len(here_list) == 0
        assert len(there_list) == 0
    for tester in testers:
        # clean up
        tester.delete()

def test_associations():
    _test_association(
        [_DbImage_Tester, _DbCollection_Tester],
        ['collections', 'images']
    )

def test_notes():
    adds = [
        ([-1], [0]),
        ([-1, 0], [1, 0]),
        ([-1, -1], [0, 1]),
        ([-1, 0, 0], [2, 1, 0])
    ]
    type = DbNoteType.add(session, _mk_name('type'), DbTextType.TEXT)
    assert type is not None
    for add in adds:
        # FIXME: this test doesn't work when the folder create i smoved out of the loop
        # (but it DOES work when single-stepped in the debugger!)
        folder = DbFolder.add(session, _mk_date(), _mk_name('folder'))
        assert folder is not None

        notes = []
        for idx in add[0]:
            notes.append(folder.add_note(session, idx, type))
        session.commit()
        for notes_idx, tbl_idx in zip(range(len(add[0])), add[1]):
            assert folder.notes[tbl_idx] is notes[notes_idx]
        while len(folder.notes) > 0:
            folder.del_note(session, 0)
        session.commit()
    pass


def test_tag_change():
    change_texts = [
        'band|Green Day',
        'fred',
        'topic|boredom'
    ]
    changes = []
    time = datetime.datetime.now()
    for ct in change_texts:
        changes.append(TagChange.add(session, ct))
    session.flush()
    for ct in change_texts:
        c = TagChange.first(session)
        assert c is not None
        assert c.text == ct
        assert c.timestamp >= time
        c.delete(session)
        time = c.timestamp
    c = TagChange.first(session)
    assert c is None

