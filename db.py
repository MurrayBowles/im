""" database classes """

from enum import IntEnum as PyIntEnum
import datetime
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy.ext.orderinglist import ordering_list

from sqlalchemy import Boolean, Column, Date, DateTime, Enum
from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy import LargeBinary, String, Table, Text
from sqlalchemy.orm import backref, relationship

from tags import on_db_tag_added, on_db_tag_removed
from tags import on_fs_tag_mapping_added, on_fs_tag_mapping_removed
import util


# DbXxx: the database's representation of folders/images/tags/notes


class TagFlags(PyIntEnum):
    """ flags describing the relationshop between an DbTag and its Item """

    NONE        = 0
    DIRECT      = 1 # this tag was applied directly by the user
    EXTERNAL    = 2 # some FsItem has this tag
    BLOCKED     = 4 # this EXTERNAL tag is blocked by the user
    # shortcuts
    B           = BLOCKED
    BD          = BLOCKED | DIRECT
    D           = DIRECT
    DE          = DIRECT | EXTERNAL
    DEB         = DIRECT | EXTERNAL | BLOCKED
    E           = EXTERNAL
    EB          = EXTERNAL | BLOCKED

    def __repr__(self):
        if self.value == 0: return TagFlags.NONE
        s = ''
        if TagFlags.DIRECT in self.value: s += 'D'
        if TagFlags.EXTERNAL in self.value: s += 'E'
        if TagFlags.BLOCKED in self.value: s += 'B'
        return s


class ItemTag(Base):
    """ Item <<->> DbTag association table """

    __tablename__ = 'item-tags'

    id = Column(Integer, primary_key=True)
    tag_id = Column(Integer, ForeignKey('db-tag.id'))
    item_id = Column(Integer, ForeignKey('item.id'))
    flags = Column(Enum(TagFlags))


# DbImage <<->> DbCollection
image_collections = Table('image-collections', Base.metadata,
    Column('image_id', Integer, ForeignKey('db-image.id')),
    Column('collection_id', Integer, ForeignKey('db-collection.id'))
)


class Item(Base):
    """ something which has a name and can be tagged:
        a Folder, Collection, Image, or Tag
    """
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)

    type = Column(String(12))
        # 'DbCollection' | 'DbFolder' | 'DbImage' | 'FsFolder'
    __mapper_args__ = {'polymorphic_identity': 'Item', 'polymorphic_on': type}

    name = Column(String(100))

    # Item <<->> DbTag
    tags = relationship(
        'ItemTag', backref='item', primaryjoin = id == ItemTag.item_id)

    # Item ->> DbNotes
    notes = relationship(
        'DbNote', order_by='DbNote.idx', collection_class=ordering_list('idx'))

    @classmethod
    def find_id(cls, session, id):
        return session.query(Item).filter_by(id=id).first()

    def add_note(self, session, idx, note_type):
        """ add a note at self.notes[idx] and return it """
        note = DbNote(item=self, type=note_type)
        if idx == -1:
            self.notes.append(note)
        else:
            self.notes.insert(idx, note)
        session.add(note)
        return note

    def del_note(self, session, idx):
        """ delete the note at self.notes[idx] """
        if idx == -1:
            note = self.notes.pop()
        else:
            note = self.notes.pop(idx)
        session.delete(note)
        pass

    def move_note(self, session, old_idx, new_idx):
        """ move the note at old_idx to new_idx """
        self.notes[old_idx], self.notes[new_idx] = \
            self.notes[new_idx], self.notes[old_idx]

    def find_item_tag(self, session, db_tag):
        return session.query(ItemTag).filter_by(
            item=self, tag=db_tag).first()

    def mod_tag_flags(self, session, db_tag, add_flags=0, del_flags=0):
        # TODD: mod_item_tag_flags?
        def mod_flags(old_flags):
            return (old_flags | add_flags) & ~del_flags
        item_tag = self.find_item_tag(session, db_tag)
        if item_tag is not None:
            item_tag.flags = mod_flags(item_tag.flags)
            if item_tag.flags == 0:
                session.delete(item_tag)
        else:
            flags = mod_flags(0)
            if flags != 0:
                session.add(ItemTag(item=self, tag=db_tag, flags=flags))

    def get_tags(self, session):
        return session.query(ItemTag).filter_by(item=self).all()

    def __repr__(self):
        # this should always be overloaded
        return "<%s %s>" % (self.type, self.name)


class DbFolder(Item):
    """ represents a single photo-shooting session """
    __tablename__ = 'db-folder'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbFolder'}

    date = Column(Date)

    # DbFolder <->> DbImage
    images = relationship(
        'DbImage', foreign_keys='[DbImage.folder_id]', back_populates='folder')

    # DbFolder <->> FsFolder
    fs_folders = relationship(
        'FsFolder', foreign_keys='[FsFolder.db_folder_id]',
        back_populates='db_folder')

    # DbFolder -> thumbnail DbImage
    thumbnail_id = Column(Integer, ForeignKey('db-image.id'))
    thumbnail = relationship('DbImage', foreign_keys='[DbFolder.thumbnail_id]')

    Index('db-folder-index', 'date', 'name', unique=True)

    @classmethod
    def add(cls, session, date, name):
        obj = cls(date=date, name=name)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, date, name):
        return session.query(DbFolder).filter_by(date=date, name=name).first()

    @classmethod
    def get(cls, session, date, name):
        """ find or create a DbFolder: return db_folder, is_new"""
        db_folder = cls.find(session, date, name)
        if db_folder is None:
            return cls.add(session, date, name), True
        else:
            return db_folder, False

    def __repr__(self):
        return '<DbFolder %s %s>' % (str(self.date), self.name)


class DbCollection(Item):
    """ a collection of images from multiple folders """
    __tablename__ = 'db-collection'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbCollection'}

    # DbCollection <<->> DbImage
    images = relationship(
        'DbImage', secondary=image_collections, back_populates='collections')

    # DbCollection -> thumbnail DbImage
    thumbnail_id = Column(Integer, ForeignKey('db-image.id'))
    thumbnail = relationship(
        "DbImage", foreign_keys='[DbCollection.thumbnail_id]')

    Index('db-collection-index', 'name', unique=True)

    @classmethod
    def add(cls, session, name):
        obj = cls(name=name)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session,  name):
        return session.query(DbCollection).filter_by(name=name).first()

    def __repr__(self):
        return '<Collection %s>' % self.name


class DbImage(Item):
    """ a single image (usually with multiple files: NEF/TIFF/PSD/JPEG) """
    __tablename__ = 'db-image'

    # isa Item (name is <seq>[<suffix>], as with FsImage and IEImage)
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbImage'}

    thumbnail = Column(LargeBinary())
    thumbnail_timestamp = Column(DateTime)

    # DbImage <<-> DbFolder
    folder_id = Column(Integer, ForeignKey('db-folder.id'))
    folder = relationship(
        'DbFolder', foreign_keys=[folder_id], back_populates='images')

    # DbImage <<->> DbCollection
    collections = relationship(
        'DbCollection', secondary=image_collections, back_populates='images')

    # DbImage <->> FsImage
    fs_images = relationship(
        'FsImage', foreign_keys='[FsImage.db_image_id]',
        back_populates='db_image')

    Index('db-folder-image-index', 'folder_id', 'name', unique=True)
    Index('db-date-image-index', 'folder.date', 'name')

    @classmethod
    def add(cls, session, folder, name):
        obj = cls(folder=folder, name=name)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, db_folder,  name):
        return session.query(DbImage).filter_by(
            folder_id=db_folder.id, name=name).first()
    # TODO: find_in_date vs find_in_folder

    @classmethod
    def get(cls, session, folder, name):
        db_image = cls.find(session, folder, name)
        if db_image is None:
            return cls.add(session, folder, name), True
        else:
            return db_image, False

    def __repr__(self):
        return '<Image %s-%s>' % (
            util.yymmdd_from_date(self.folder.date), self.name)


class DbTagType(PyIntEnum):
    """ the relation between a tag and its .base_tag """

    BASE = 1        # normal (base) tag; .base_tag is None
    IDENTITY_IS = 2 # tag refers to the thing represented by .base_tag
    REPLACED_BY = 3 # tag has been replaced by .base_tag
    DEPRECATED = 4  # tag has been deprecated; .base_tag is None


class DbTag(Item):
    """ a hierarchical tag on a Item """
    __tablename__ = 'db-tag'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbTag'}

    # DbTag tree
    parent_id = Column(Integer, ForeignKey('db-tag.id'), nullable=True)
    parent = relationship('DbTag', remote_side=[id], foreign_keys=[parent_id])
    children = relationship(
        'DbTag', foreign_keys='[DbTag.parent_id]', back_populates='parent')

    # DbTag <<->> Item
    items = relationship(
        'ItemTag', backref='tag', primaryjoin = id == ItemTag.tag_id)

    # DbTag -> replacement or identity DbTag
    tag_type = Column(Integer)  # DbTagType
    base_tag_id = Column(Integer, ForeignKey('db-tag.id'), nullable=True)
    base_tag = relationship(
        'DbTag', remote_side=[id], foreign_keys=[base_tag_id])

    lower_name = Column(String) # TODO: this extra column shouldn't be necessary
    Index('db-tag', lower_name, 'parent')

    def base(self):
        return {
            DbTagType.BASE: self,
            DbTagType.IDENTITY_IS: self,
            DbTagType.REPLACED_BY: self.base_tag,
            DbTagType.DEPRECATED: None
        }[self.type.value]

    @classmethod
    def add(cls, session, name,
        parent=None, tag_type=DbTagType.BASE, base_tag=None
    ):
        obj = cls(
            parent=parent, name=name, lower_name=name.lower(),
            tag_type=tag_type.value, base_tag=base_tag)
        if obj is not None: session.add(obj)
        if tag_type != DbTagType.DEPRECATED:
            on_db_tag_added(session, obj)
        return obj

    @classmethod
    def find(cls, session, name, parent=None):
        return session.query(DbTag).filter_by(
            lower_name=name.lower(), parent=parent).first()

    @classmethod
    def find_flat(cls, session, name):
        return session.query(DbTag).filter_by(
            lower_name=name.lower()).all()

    @classmethod
    def get(cls, session, name,
        parent=None, tag_type=DbTagType.BASE, base_tag=None
    ):
        tag = cls.find(session, name, parent)
        if tag is None:
            return cls.add(session, name, parent, tag_type, base_tag), True
        else:
            return tag, False

    @classmethod
    def get_expr(cls, session, expr, tag_type=DbTagType.BASE, base_tag=None):
        # <expr> is parent|child
        # NOTE: does NOT return an (xxx, is-new) tuple
        list = expr.split('|')
        assert len(list) > 0
        parent = None
        tag = None # make lint shut up
        for elt in list:
            tag = cls.get(session, elt, parent, tag_type, base_tag)[0]
            parent = tag
        return tag

    @classmethod
    def find_expr(cls, session, expr):
        # <expr> is parent|child
        list = expr.split('|')
        tag = None
        for elt in list:
            tag = cls.find(session, elt, parent=tag)
            if tag is None:
                break
        return tag
    # TODO test

    @classmethod
    def find_id(cls, session, id):
        return session.query(DbTag).filter_by(id=id).first()
    
    def set_type(self, session, new_type):
        if new_type != self.tag_type:
            if new_type == DbTagType.DEPRECATED:
                on_db_tag_removed(session, self)
            old_type = self.tag_type
            self.tag_type = new_type
            if old_type == DbTagType.DEPRECATED:
                on_db_tag_added(session, self)
                
    def set_name(self, session, new_name):
        # TODO: change parent too, or just name?
        if new_name != self.name:
            on_db_tag_removed(session, self)
            self.name = new_name
            on_db_tag_added(session, self)
    
    def pname(self):
        tag = self
        str = tag.name
        while tag.parent is not None:
            tag = tag.parent
            str = tag.name + '|' + str
        return str

    def __repr__(self):
        return "<DbTag %s>" % self.pname()

    def __cmp__(self, other):
        return self.pname().__cmp__(other.pname())


class DbTextType(PyIntEnum):
    """ the syntax of a DbNote's text """
    TEXT = 1        # simple text
    URL = 2         # a URL


class DbNoteType(Base):
    """ the type of a DbNote (e.g. name, location, PBase page,...) """
    __tablename__ = 'db-note-type'
    id = Column(Integer, primary_key=True)

    name = Column(String(30))
    text_type = Column(Integer)  # DbNoteType enumeration

    @classmethod
    def add(cls, session, name, text_type):
        obj = cls(name=name, text_type=text_type.value)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find_id(cls, session, id):
        return session.query(DbNoteType).filter_by(id=id).first()

    def __repr__(self):
        return '<NoteType %s: %s>' % (
            self.name, DbTextType(self.text_type).name)

class DbNote(Base):
    """ a text note on a Item
        DbNotes are added/accessed/deleted by calling <Item>.add/get/del_note
    """
    __tablename__ = 'db-note'
    id = Column(Integer, primary_key=True)

    idx = Column(Integer) # index in .item.notes
    text = Column(String(100))

    # DbNote -> DbNoteType
    type_id = Column(Integer, ForeignKey('db-note-type.id'))
    type = relationship("DbNoteType", backref=backref("db-note", uselist=False))
    #type = relationship('DbNoteType', foreign_keys='[DbNote.tyoe_id]')

    # DbNote -> Item
    item_id = Column(Integer, ForeignKey('item.id'))
    item = relationship("Item", backref=backref("db-note", uselist=False))
    #item = relationship('Item', foreign_keys='[DbNote.item_id]')

    def __repr__(self):
        return '<Note %s[%s:%s:%s]>' % (
            str(self.item), self.type.name, str(self.idx), str(id(self)))


""" FsXxx: an inventory of what's been imported from the filesystem """


class FsTagSource(Base):
    """ who tagged these FsFolders/Images """
    __tablename__ = 'fs-tag-source'

    id = Column(Integer, primary_key=True)
    description = Column(String(100))

    @classmethod
    def add(cls, session, description=''):
        obj = cls(description=description)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, description):
        return session.query(FsTagSource).filter_by(
            description=description).first()

    def mappings(self, session):
        """ Return all the FsTagMappings in this FsTagSource. """
        return session.query(FsTagMapping).filter_by(
            tag_source=self).all()

    @classmethod
    def get(cls, session, description):
        tag_source = cls.find(session, description)
        if tag_source is None:
            return cls.add(session, description), True
        else:
            return tag_source, False

    @classmethod
    def find_id(cls, session, id):
        return session.query(FsTagSource).filter_by(id=id).first()

    def __repr__(self):
        return '<FsTagSource %s>' % self.description


class FsSourceType(PyIntEnum):
    DIR     = 1 # a directory of image directories
    FILE    = 2 # a directory of image files
    WEB     = 3 # a web site to be scraped


class FsSource(Item):
    """ external source from which a set of FsFolders/Images was imported """
    __tablename__ = 'fs-source'

    # isa Item (.name is the user-assigned name, or None)
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsSource'}

    # secondary key (TODO index? enforce uniqueness?)
    volume = Column(String(32))
        # source volume: '<volume letter>:' or '<volume label>'
    path = Column(String(260))
        # source pathname
        # for WEB, volume is 'http[s]:' and path is the rest of the URL

    source_type = Column(Enum(FsSourceType))
    readonly = Column(Boolean)

    # FsSource -> FsTagSourceId
    tag_source_id = Column(Integer, ForeignKey('fs-tag-source.id'))
    tag_source = relationship(
        'FsTagSource', backref=backref('fs-tag-source', uselist=False))

    # FsSource <->> FsFolder
    folders = relationship(
        'FsFolder', foreign_keys='[FsFolder.source_id]',
        back_populates='source')

    @classmethod
    def add(cls, session, volume, path, source_type, readonly, tag_source):
        obj = cls(
            volume=volume, path=path, source_type=source_type.value,
            readonly=readonly, tag_source=tag_source
        )
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def all(cls, session):
        return session.query(FsSource).all() # TODO: test

    @classmethod
    def find_id(cls, session, id):
        return session.query(FsSource).filter_by(id=id).first()

    @classmethod
    def find(cls, session, volume, path):
        return session.query(FsSource).filter_by(
            volume=volume, path=path).first()

    def label(self):
        return (
            self.volume
            if self.volume is not None and not self.volume.endswith(':')
            else None)

    def win_path(self):
        return (
            self.path if self.source_type == FsSourceType.WEB else
            util.win_path(self.volume, self.path))

    def rel_path(self, child_path):
        if self.source_type == FsSourceType.WEB:
            if child_path == self.path:
                return ''
            prefix = self.path + '/'
        else:
            drive, child_path = os.path.splitdrive(child_path)
            prefix = util.path_plus_separator(self.path)
        if not child_path.startswith(prefix):
            pass
        assert child_path.startswith(prefix)
        rel_path = child_path[len(prefix):]
        return rel_path

    def pname(self):
        s = ''
        if self.name is not None:
            s += '%s = ' % (self.name)
        if self.volume.endswith(':'):
            s += self.volume
        else:
            s += '[%s]' % (self.volume)
        s += self.path
        return s

    def live_text(self):
        s = ''
        if self.name is not None:
            s += '%s = ' % (self.name)
        if not self.volume.endswith(':'):
            s += '[' + self.volume + ']'
        if self.accessible():
            s += self.win_path()
        else:
            s += self.path
        return s

    def accessible(self):
        return (
            self.source_type == FsSourceType.WEB
            or (self.win_path() is not None))

    def __repr__(self):
        return '<FsSource %s>' % (self.pname())


class FsItem(Item):
    """ FsFolder | FsImage """
    __tablename__ = 'fs-item'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsItem'}

    # FsItem ->> FsItemTag
    item_tags = relationship(
        'FsItemTag', foreign_keys='[FsItemTag.item_id, FsItemTag.idx]')

    def db_item(self):
        raise NotImplementedError

    def db_tag_set(self):
        """ Return the set of DbTags currently bound to self.item_tags. """
        res = set() # of DbTag
        for item_tag in self.item_tags:
            if item_tag.binding == FsTagBinding.BOUND:
                res.add(item_tag.db_tag)
        return res


class FsTagType(PyIntEnum):
    """ tag word(s) vs tag """
    WORD        = 1
    TAG         = 2


class FsTagBinding(PyIntEnum):
    UNBOUND     = 0 # not bound (this external tag is being ignored)
    SUGGESTED   = 1 # .db_tag is a suggested tag
    BOUND       = 2 # .db_tag will be bound to the external tag or word(s)

    def is_bound(self):
        return self == FsTagBinding.BOUND

    def has_db_tag(self):
        return self >= FsTagBinding.SUGGESTED


class FsItemTagSource(PyIntEnum):

    NONE        = 0 # no tag
    DBTAG       = 1 # tag/word(s) found in DbTags
    GLOBTS      = 2 # tag/word(s) found in global_tag_source
    FSTS        = 3 # tag/word(s) found in FsSource.tag_source
    DIRECT      = 4 # directly tagged by the user on this FsFolder/Image


class FsItemTag(Base):
    """ an external tag (or a possible word of a tag) for an FsItem """
    __tablename__ = 'fs-item-tag'

    # primary key

    item_id = Column(Integer, ForeignKey('fs-item.id'), primary_key=True)
    item = relationship(
        'FsItem', foreign_keys=[item_id], back_populates='item_tags')
    idx = Column(Integer, primary_key=True)

    # secondary key

    type = Column(Enum(FsTagType))
    text = Column(String(collation='NOCASE'))

    # value
    first_idx = Column(Integer) # index of the first FsItemTag in the binding
    last_idx =  Column(Integer) # index of the last FsItemTag in the binding
        # first_idx <= idx <= last_idx
        # when type == TAG, first_idx == last_idx

    bases = Column(String)
        # ,-separated list of suggested tag bases,
        #   e.g. 'band' or 'venue' or 'band, venue'
        # FIXME: this should just be an integer enum:
        # the possible lists are fixed by the code

    binding = Column(Enum(FsTagBinding))
    source = Column(Enum(FsItemTagSource))

    # if .binding.has_db_tag()
    db_tag_id = Column(Integer,ForeignKey('db-tag.id'))
    db_tag = relationship('DbTag', foreign_keys=[db_tag_id], uselist=False)

    Index('fs-item-tag', 'type', 'text', unique=False)

    @classmethod
    def add(cls, session, item, idx, idx_range,
        type, text, bases,
        binding, source, db_tag
    ):
        # TODO: maybe remove the last three parameters, and idx_range
        if source == FsItemTagSource.DBTAG and binding == FsTagBinding.UNBOUND:
            raise ValueError
        tag = FsItemTag(
            item=item,
            idx=idx, first_idx = idx_range[0], last_idx = idx_range[1] - 1,
            type=type, text=text, bases=bases,
            binding=binding, source=source, db_tag=db_tag)
        if tag is not None: session.add(tag)
        return tag

    def bind(self, binding, source, db_tag, idx_range=None):
        self.binding = binding
        self.source = source
        self.db_tag = db_tag
        if idx_range is not None:
            self.first_idx = idx_range.start
            self.last_idx = idx_range.stop - 1
        pass

    @classmethod
    def find_idx(cls, session, item, idx):
        return session.query(FsItemTag).filter_by(item=item, idx=idx).first()

    @classmethod
    def find_text(cls, session, type, text):
        return session.query(FsItemTag).filter_by(type=type, text=text).all()

    def __repr__(self):
        if self.type == FsTagType.WORD:
            idx = 'w%s/%s..%s' % (self.idx, self.first_idx, self.last_idx)
        else:
            idx = 't%s' % self.idx
        tgt = ' => ' + self.db_tag.pname() if self.db_tag is not None else ''
        return '<FsItemTag [%s] %s: %s/%s%s>' % (
            idx, self.text, self.binding.name, self.source.name, tgt)


class FsTagMapping(Base):
    """ a text -> DbTag map in an FsTagSource """
    __tablename__ = 'fs-tag-mapping'

    # key

    tag_source_id = Column(
        Integer, ForeignKey('fs-tag-source.id'), primary_key=True)
    tag_source = relationship(
        'FsTagSource', backref=backref('fs-tag-mapping', uselist=False))

    text = Column(String(collation='NOCASE'), primary_key=True)
        # e.g. 'band|Tribe 8'

    # value

    binding = Column(Enum(FsTagBinding))
    # a text is marked to be ignored by setting binding=BOUND, db_tag=None

    db_tag_id = Column(Integer, ForeignKey('db-tag.id'))
    db_tag = relationship(
        'DbTag', backref=backref('fs-tag-mapping', uselist=False))

    @classmethod
    def add(cls, session, tag_source, text, binding, db_tag):
        if binding == FsTagBinding.UNBOUND:
            raise ValueError
        mapping = FsTagMapping(
            tag_source=tag_source, text=text, binding=binding, db_tag=db_tag)
        if mapping is not None: session.add(mapping)
        on_fs_tag_mapping_added(session, mapping)
        return mapping

    @classmethod
    def find(cls, session, tag_source, text):
        return session.query(FsTagMapping).filter_by(
            tag_source=tag_source, text=text).first()

    @classmethod
    def set(cls, session, tag_source, text, binding, db_tag):
        mapping = cls.find(session, tag_source, text)
        if mapping is None:
            if binding != FsTagBinding.UNBOUND:
                mapping = cls.add(session, tag_source, text, binding, db_tag)
        else:
            old_binding = mapping.binding
            if binding != old_binding:
                on_fs_tag_mapping_removed(session, mapping)
                if binding == FsTagMapping.UNBOUND:
                    session.delete(mapping)
                    return None
            mapping.binding = binding
            mapping.db_tag = db_tag
            if binding != old_binding:
                on_fs_tag_mapping_added(session, mapping)
        return mapping

    def leaf_text(self):
        x = self.text.rfind('|')
        if x == -1:
            return self.text
        else:
            # TODO: strip spaces around '|' when storing .text
            return self.text[x + 1:].lstrip(' ')

    def pname(self):
        return '%s => %s' % (
            self.text,
            self.db_tag.pname() if self.db_tag is not None else 'None'
        )

    def __repr__(self):
        return '<FsTagMapping %s>' %  self.pname()


class TagChange(Base):
    """ a timestamp-sorted list of new DbTags and FsTagMappings
        which have not yet been applied to FsFolders and FsImages
    """
    __tablename__ = 'tag-change'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    text = Column(String)

    Index('tag-change-index', 'timestamp', unique=False)

    @classmethod
    def clear(cls, session):
        """ Clear the global TagChange list """
        session.query(TagChange).delete()

    @classmethod
    def add(cls, session, text):
        """ Add <text> to the global TagChange list """
        obj = cls(timestamp=datetime.datetime.now(), text=text)
        if obj is not None: session.add(obj)
        return obj

    def delete(self, session):
        """ Delete from the global TagChange list """
        session.delete(self)

    @classmethod
    def first(cls, session):
        """ Return the oldest item in the global TagChange list. """
        return session.query(TagChange).order_by(TagChange.timestamp).first()

    @classmethod
    def all(cls, session):
        """ Return the global TagChange list, sorted oldest-first. """
        return session.query(TagChange).order_by(TagChange.timestamp).all()

    def __repr__(self):
        return '<TagChange %s @ %s>' % (self.text, str(self.timestamp))

class FsFolder(FsItem):
    """ a filesystem source from which DbFolder were imported
        if source.type is dir_set, a filesystem directory
        if source.type is file_set, a group of files with a common name prefix
    """
    __tablename__ = 'fs-folder'

    # isa FsItem (.name is relative path from FsSource.path to IEFolder.fs_path)
    id = Column(Integer, ForeignKey('fs-item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsFolder'}

    # DbFolder date and name suggested by import/export code (e.g scan_dir_set)
    # may each be None
    # copied from the corresponding members in IEFolder
    db_date = Column(Date)
    db_name = Column(String)

    # last-import timestamps
    last_scan = Column('last-scan', DateTime)
    last_import_tags = Column('last-import-tags', DateTime)

    # FsFolder <<-> FsSource
    source_id = Column(Integer, ForeignKey('fs-source.id'))
    source = relationship(
        'FsSource', foreign_keys=[source_id], back_populates='folders')

    # FsFolder <<-> DbFolder
    db_folder_id = Column(Integer, ForeignKey('db-folder.id'))
    db_folder = relationship(
        'DbFolder', foreign_keys=[db_folder_id], back_populates='fs_folders')

    # FsFolder <->> FsImage
    images = relationship(
        'FsImage', foreign_keys='[FsImage.folder_id]', back_populates='folder')

    Index('fs-folder-index', 'source', 'name', unique=True)

    @classmethod
    def add(cls, session, source, name,
        db_date=None, db_name=None, db_folder=None
    ):
        obj = cls(
            source=source, name=name,
            db_date=db_date, db_name=db_name, db_folder=db_folder)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, source, name):
        return session.query(FsFolder).filter_by(
            source=source, name=name).first()

    @classmethod
    def get(cls, session, source, name,
        db_date=None, db_name='', db_folder=None
    ):
        fs_folder = cls.find(session, source, name)
        if fs_folder is None:
            return (
                cls.add(session, source, name, db_date, db_name, db_folder)
                , True)
        else:
            return fs_folder, False

    def db_item(self):
        return self.db_folder

    def pname(self):
        return '%s|%s' % (self.source.pname(), self.name)

    def __repr__(self):
        return '<FsFolder %s>' % self.pname()


class FsImage(FsItem):
    """ a (family of) filesystem file(s) from which a DbImage was imported
        the filesystem could contain a .tif, a .psd, and a .jpg,
        and one FsImage would be created,
        with .image_types indicating which were found
    """
    __tablename__ = 'fs-image'

    # isa Item (name is <seq>[<suffix>], as with DbImage and FsImage)
    id = Column(Integer, ForeignKey('fs-item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsImage'}

    # FsImage <<-> FsFolder
    folder_id = Column(Integer, ForeignKey('fs-folder.id'), primary_key=True)
    folder = relationship(
        'FsFolder', foreign_keys=[folder_id], back_populates='images')

    # FsImage <<-> DbImage
    db_image_id = Column(Integer, ForeignKey('db-image.id'))
    db_image = relationship(
        'DbImage', foreign_keys=[db_image_id], back_populates='fs_images')

    @classmethod
    def add(cls, session, folder, name, db_image=None):
        obj = cls(folder=folder, name=name, db_image=db_image)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, folder, name):
        return  session.query(FsImage).filter(
            FsImage.folder == folder, FsImage.name == name
        ).first()

    @classmethod
    def get(cls, session, folder, name, db_image=None):
        """ find or add an FsImage: return fs_image, is_new """
        fs_image = cls.find(session, folder, name)
        if fs_image is None:
            return cls.add(session, folder, name, db_image), True
        else:
            return fs_image, False

    def db_item(self):
        return self.db_image

    def text(self):
        return '%s|%s' % (self.folder.pname(), self.name)

    def __repr__(self):
        return "<FsImage %s>" % (self.text())


session = None

# builtin database objects
global_tag_source = None
band_tag = None
venue_tag = None

def _get_db_builtins(session):
    """ get builtin database objects """
    global global_tag_source, band_tag, venue_tag
    global_tag_source, is_new = FsTagSource.get(session, '$global')
    band_tag = DbTag.get(session, 'band')
    venue_tag = DbTag.get(session, 'venue')

def _open_db(url):
    """ open a database and return a session """
    global session
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    _get_db_builtins(session)
    return session

def open_mem_db():
    """ open a memory database """
    return _open_db('sqlite:///:memory:')

def close_db():
    """ close the database """
    pass

def open_preloaded_mem_db():
    session = open_mem_db()

    std_ts = FsTagSource.add(session, 'standard')
    corbett_ts = FsTagSource.add(session, 'corbett')
    s1 = FsSource.add(
        session, 'main1234', '\\photos',
        FsSourceType.DIR, True, std_ts)
    s2 = FsSource.add(
        session, 'C:', '\\photos',
        FsSourceType.DIR, False, std_ts)
    s3 = FsSource.add(
        session, 'HD2', '\\corbett-psds',
        FsSourceType.FILE, False, corbett_ts)
    s4 = FsSource.add(
        session, 'http:', '//www.pbase.com/murraybowles',
        FsSourceType.WEB, True, std_ts)

    venue = DbTag.add(session, 'venue')
    gilman = DbTag.add(session, 'Gilman', parent=venue)
    band = DbTag.add(session, 'band')
    bikini_kill = DbTag.add(session, 'Bikini Kill', parent=band)

    bk_mapping = FsTagMapping.add(
        session, corbett_ts, 'Bikini Kill',
        FsTagBinding.BOUND, bikini_kill)

    session.commit()
    pass

if __name__=='__main__':
    open_preloaded_mem_db()