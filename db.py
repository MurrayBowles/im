""" SQLAlchemy database classes """

from enum import IntEnum as PyIntEnum
import datetime
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy.ext.orderinglist import ordering_list

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float
from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy import LargeBinary, String, Table, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm import composite

from imdate import IMDate
import tags
import util


# DbXxx: the database's internal representation of folders/images/tags/notes


class TagFlags(PyIntEnum):
    """ flags describing the relationship between a DbTag and its Item """

    NONE        = 0
    DIRECT      = 1 # this tag was applied by the user
    EXTERNAL    = 2 # this tag was imported from some FsItem
    BLOCKED     = 4 # this tag was blocked by the user
    # abbreviations
    B           = BLOCKED
    BD          = BLOCKED | DIRECT
    D           = DIRECT
    DE          = DIRECT | EXTERNAL
    DEB         = DIRECT | EXTERNAL | BLOCKED
    E           = EXTERNAL
    EB          = EXTERNAL | BLOCKED

    def __str__(self):
        return 'TagFlags.%s' % self.name


class ItemTag(Base):
    """ Item <<->> DbTag association table """

    __tablename__ = 'item_tags'

    id = Column(Integer, primary_key=True)
    tag_id = Column(Integer, ForeignKey('db_tag.id'))
    item_id = Column(Integer, ForeignKey('item.id'))
    flags = Column(Enum(TagFlags))

    def __str__(self):
        return "[ItemTag tag_id=%u, item_id=%u, ItemTag=%s]" %(
            self.tag_id, self.item_id, self.flags)

# DbImage <<->> DbCollection
image_collections = Table('image-collections', Base.metadata,
    Column('image_id', Integer, ForeignKey('db_image.id')),
    Column('collection_id', Integer, ForeignKey('db_collection.id'))
)


max_import_edit_level = 3   #  the maximum value set for Item.import_edit_level


class IssueType(Enum):  # (flag, import_edit_level, string)
    NO_DATE                 = (1, 0, 'ND')
    # FsFolder.db_date is null, DbFolder not auto-linked
    NAME_NEEDS_EDIT         = (2, 0, 'NNE')
    # FsFolder.db_name is questionable, DbFolder not auto-linked
    FOLDER_TAGS_ARE_WORDS   = (4, 1, 'FTAW')
    # FsFolder: folder auto-tagging is likely to fail
    IMAGE_TAGS_ARE_WORDS    = (8, 1, 'ITAW')
    # FsFolder: image auto-tagging is likely to fail
    UNEXPECTED_FILE         = (16, 2, 'UF')
    # FsFolder contains mystery file(s)
    EXTRA_IMAGE_INSTS       = (32, 2, 'XII')
    # FsFolder: there are multiple instances for some extension for some images

    def __str__(self):
        return self[2]


class Item(Base):
    """ something which has a name and can be tagged:
        a Folder, Collection, Image, or Tag
    """
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)

    type = Column(String(12))
    # e.g. 'DbCollection' | 'DbFolder' | 'DbImage' | 'FsFolder'
    # this must be the actual table class name
    __mapper_args__ = {'polymorphic_identity': 'Item', 'polymorphic_on': type}

    name = Column(String(100))

    # Item <<-(ItemTag)->> DbTag
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
                # session.delete(item_tag) this should work, but doesn't
                self.tags.remove(item_tag)
        else:
            flags = mod_flags(0)
            if flags != 0:
                session.add(ItemTag(item=self, tag=db_tag, flags=flags))

    def get_tags(self, session):
        return session.query(ItemTag).filter_by(item=self).all()

    def __str__(self):
        # this should always be overloaded
        return "[Item %s, %s]" % (self.type, self.name)


class DbFolder(Item):
    """ represents a single photo-shooting session """
    __tablename__ = 'db_folder'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbFolder'}

    # date = Column(Date)             # FIXME: remove
    date2_year = Column(Integer)
    date2_month = Column(Integer)
    date2_day = Column(Integer)
    date2 = composite(IMDate, date2_year, date2_month, date2_day)

    edit_level = Column(Integer)
    # 0..5, where 5 is good; initialized from FsFolder.import_edit_level

    # DbFolder <->> DbImage
    images = relationship(
        'DbImage', foreign_keys='[DbImage.folder_id]', back_populates='folder', lazy='dynamic')

    # DbFolder <->> FsFolder
    fs_folders = relationship(
        'FsFolder', foreign_keys='[FsFolder.db_folder_id]',
        back_populates='db_folder', lazy='dynamic')

    # DbFolder -> thumbnail DbImage  TODO: currently not set
    thumbnail_id = Column(Integer, ForeignKey('db_image.id'))
    thumbnail = relationship('DbImage', foreign_keys='[DbFolder.thumbnail_id]')

    Index('db_folder_index', 'date2', 'db_name', unique=True)
    Index('db_folder_flyer_index', 'date2_month', 'date2_day', 'db_name', unique=True)

    @classmethod
    def add(cls, session, date, name):
        date2 = IMDate(date.year, date.month, date.day)
        obj = cls(
            # date=date,
            date2=date2, name=name)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, date, name):
        date2 = IMDate(date.year, date.month, date.day)
        return session.query(DbFolder).filter_by(date2=date2, name=name).first()

    @classmethod
    def get(cls, session, date, name):
        """ find or create a DbFolder: return db_folder, is_new"""
        db_folder = cls.find(session, date, name)
        if db_folder is None:
            return cls.add(session, date, name), True
        else:
            return db_folder, False

    def fs_items(self):
        return self.fs_folders

    def __str__(self):  # checked
        return '[DbFolder %s %s]' % (self.date, self.name)


class DbCollection(Item):
    """ a collection of images from multiple folders """
    __tablename__ = 'db_collection'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbCollection'}

    # DbCollection <<->> DbImage
    images = relationship(
        'DbImage', secondary=image_collections, back_populates='collections')

    # DbCollection -> thumbnail DbImage  TODO: currently not set
    thumbnail_id = Column(Integer, ForeignKey('db_image.id'))
    thumbnail = relationship(
        "DbImage", foreign_keys='[DbCollection.thumbnail_id]')

    Index('db_collection_index', 'db_name', unique=True)

    @classmethod
    def add(cls, session, name):
        obj = cls(name=name)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session,  name):
        return session.query(DbCollection).filter_by(name=name).first()

    def __str__(self):
        return '[DbCollection %s]' % self.name


class ImageData(Base):
    ''' data extracted from a FS image

        At the point a DbImage is created for an FsImage, FsImage.data_id is nulled
        and moved to DbImage.data_id. If there are multiple FsImages for a DbImage,
        their .data_ids are nulled the next time they are encountered in a scan.
    '''
    __tablename__ = 'image_data'
    id = Column(Integer, primary_key=True)

    # DBImage ---> ImageData: set by fg_finish_ie_work_item() or ie_db._set_db_image()
    # FsImage -0-> ImageData: set by fg_finish_ie_work_item(), cleared by _set_db_image()

    # TODO: image_types bitset

    thumbnail_timestamp = Column(DateTime)
    thumbnail = Column(LargeBinary())
    # checked by fg_start_ie_work_item() to schedule a thumbnail read
    # updated by fg_finish_ie_work_item() and cleared by FsImage.set_db_image()

    # EXIF attributes -- see exif.py
    exif_timestamp = Column(DateTime)   # also covers imported image tags
    image_width = Column(Integer)
    image_height = Column(Integer)
    focal_length = Column(Float)
    flash = Column(String)
    shutter_speed = Column(Float)
    aperture = Column(Float)
    sensitivity = Column(Integer)


class DbImage(Item):
    """ a single image (usually with multiple files: NEF/TIFF/PSD/JPEG) """
    __tablename__ = 'db_image'

    # isa Item (db_name is <seq>[<suffix>], as with FsImage and IEImage)
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbImage'}

    # DBImage -> ImageData: set by fg_finish_ie_work_item() or ie_db._set_db_image()
    data_id = Column(Integer, ForeignKey('image_data.id'), nullable=True)
    data = relationship('ImageData', foreign_keys=[data_id])

    # DbImage <<-> DbFolder
    folder_id = Column(Integer, ForeignKey('db_folder.id'))
    folder = relationship(
        'DbFolder', foreign_keys=[folder_id], back_populates='images')

    # DbImage <<->> DbCollection
    collections = relationship(
        'DbCollection', secondary=image_collections, back_populates='images')

    # DbImage <->> FsImage
    fs_images = relationship(
        'FsImage', foreign_keys='[FsImage.db_image_id]',
        back_populates='db_image', lazy='dynamic')

    Index('db_folder_image_index', 'folder_id', 'db_name', unique=True)
    Index('db_date_image_index', 'folder.date', 'db_name')

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

    def fs_items(self):
        return self.fs_images

    def __str__(self):  # checked
        return '[DbImage %s-%s]' % (
            util.yymmdd_from_date(self.folder.date), self.name)


class DbTagType(PyIntEnum):
    """ the relation between a tag and its .base_tag """

    BASE = 1        # normal (base) tag; .base_tag is None
    IDENTITY_IS = 2 # tag refers to the person/place/thing represented by .base_tag
    REPLACED_BY = 3 # tag has been replaced by .base_tag
    DEPRECATED = 4  # tag has been deprecated; .base_tag is None

    def __str__(self):
        return 'DbTagType.%s' % self.name

class DbTag(Item):
    """ a hierarchical tag on a Item """
    __tablename__ = 'db_tag'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbTag'}

    # DbTag tree
    parent_id = Column(Integer, ForeignKey('db_tag.id'), nullable=True)
    parent = relationship('DbTag', remote_side=[id], foreign_keys=[parent_id])
    children = relationship(
        'DbTag', foreign_keys='[DbTag.parent_id]', back_populates='parent', lazy='dynamic')

    # DbTag <<->> Item
    items = relationship(
        'ItemTag', backref='tag', primaryjoin = id == ItemTag.tag_id)

    # DbTag -> replacement or identity DbTag
    tag_type = Column(Integer)  # DbTagType
    base_tag_id = Column(Integer, ForeignKey('db_tag.id'), nullable=True)
    base_tag = relationship(
        'DbTag', remote_side=[id], foreign_keys=[base_tag_id])

    lower_name = Column(String) # TODO: this extra column shouldn't be necessary
    Index('db_tag', lower_name, 'parent')

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
            tags.on_db_tag_added(session, obj)
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
                tags.on_db_tag_removed(session, self)
            old_type = self.tag_type
            self.tag_type = new_type
            if old_type == DbTagType.DEPRECATED:
                tags.on_db_tag_added(session, self)
                
    def set_name(self, session, new_name):
        # TODO: change parent too, or just db_name?
        if new_name != self.name:
            tags.on_db_tag_removed(session, self)
            self.name = new_name
            tags.on_db_tag_added(session, self)
    
    def pname(self):
        tag = self
        s = tag.name
        while tag.parent is not None:
            try:
                tag = tag.parent
                s = tag.name + '|' + s
            except Exception as ed:
                print('hey')
        return s

    def __str__(self):  # checked
        return "[DbTag %s: %s]" % (self.pname(), DbTagType(self.tag_type))

    def __cmp__(self, other):
        return self.pname().__cmp__(other.pname())


class DbTextType(PyIntEnum):
    """ the syntax of a DbNote's state """
    TEXT = 1        # simple state
    URL = 2         # a URL

    def __str__(self):
        return 'DbTextType.%s' % self.name


class DbNoteType(Base):
    """ the type of a DbNote (e.g. db_name, location, PBase page,...) """
    __tablename__ = 'db_note_type'
    id = Column(Integer, primary_key=True)

    name = Column(String(30))
    text_type = Column(Integer)  # DbTextType enumeration

    @classmethod
    def add(cls, session, name, text_type):
        obj = cls(name=name, text_type=text_type.value)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find_id(cls, session, id):
        return session.query(DbNoteType).filter_by(id=id).first()

    def __str__(self):
        return '[NoteType %s: %s]' % (self.name, self.text_type)

class DbNote(Base):
    """ a state note on a Item
        DbNotes are added/accessed/deleted by calling <Item>.add/get/del_note
    """
    __tablename__ = 'db_note'
    id = Column(Integer, primary_key=True)

    idx = Column(Integer) # tab_idx in .item.notes
    text = Column(String(100))

    # DbNote -> DbNoteType
    type_id = Column(Integer, ForeignKey('db_note_type.id'))
    type = relationship("DbNoteType", backref=backref("db_note", uselist=False))
    #type = relationship('DbNoteType', foreign_keys='[DbNote.tyoe_id]')

    # DbNote -> Item
    item_id = Column(Integer, ForeignKey('item.id'))
    item = relationship("Item", backref=backref("db_note", uselist=False))
    #item = relationship('Item', foreign_keys='[DbNote.item_id]')

    def __str__(self):
        return '[DbNote %s[%s]: %s]' % (self.item, self.idx, self.type)


""" FsXxx: an inventory of what's been imported from the filesystem """


class FsTagSource(Base):
    """ who tagged these FsFolders/Images """
    __tablename__ = 'fs_tag_source'

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

    def __str__(self):  # checked
        return '[FsTagSource %s]' % self.description


class FsSourceType(PyIntEnum):
    DIR     = 1 # a directory of image directories
    FILE    = 2 # a directory of image files
    WEB     = 3 # a web site to be scraped

    def __str__(self):
        return 'FsSourceType.%s' % self.name

class FsSource(Item):
    """ external source from which a set of FsFolders/Images was imported """
    __tablename__ = 'fs_source'

    # isa Item (.db_name is the user-assigned db_name, or None)
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsSource'}

    # secondary key (TODO tab_idx? enforce uniqueness?)
    volume = Column(String(32))
        # source volume: '<volume letter>:' or '<volume label>'
    path = Column(String(260))
        # source pathname
        # for WEB, volume is 'http[s]:' and db_name is the rest of the URL

    source_type = Column(Enum(FsSourceType))
        # TODO why is Enum ok here but not for DbNoteType.text_type
    readonly = Column(Boolean)

    # FsSource -> FsTagSourceId
    tag_source_id = Column(Integer, ForeignKey('fs_tag_source.id'))
    tag_source = relationship(
        'FsTagSource', foreign_keys=[tag_source_id])

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

    def __str__(self):  # checked
        return '[FsSource %s]' % (self.pname())


class FsItem(Item):
    """ FsFolder | FsImage """
    __tablename__ = 'fs_item'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsItem'}

    # FsItem ->> FsItemTag
    item_tags = relationship('FsItemTag',
        order_by='FsItemTag.idx', collection_class=ordering_list('idx'))

    def db_item(self):
        raise NotImplementedError

    def db_tag_set(self):
        """ Return the set of DbTags currently bound to self.item_tags. """
        res = set() # of DbTag
        for item_tag in self.item_tags:
            if item_tag.binding == FsTagBinding.BOUND:
                res.add(item_tag.db_tag)
        return res

    def __str__(self):
        return '[FsItem]'  # FIXME: show type?


class FsTagType(PyIntEnum):
    """ tag word(s) vs tag """
    WORD        = 1
    TAG         = 2

    def __str__(self):
        return 'FsTagType.%s' % self.name


class FsTagBinding(PyIntEnum):
    UNBOUND     = 0 # not bound (this external tag is being ignored)
    SUGGESTED   = 1 # .db_tag is a suggested tag
    BOUND       = 2 # .db_tag will be bound to the external tag or word(s)

    def is_bound(self):
        return self == FsTagBinding.BOUND

    def has_db_tag(self):
        return self >= FsTagBinding.SUGGESTED

    def __str__(self):
        return 'FsTagBinding.%s' % self.name


class FsItemTagSource(PyIntEnum):
    NONE        = 0 # no tag
    DBTAG       = 1 # tag/word(s) found in DbTags
    GLOBTS      = 2 # tag/word(s) found in global_tag_source
    FSTS        = 3 # tag/word(s) found in FsSource.tag_source
    DIRECT      = 4 # directly tagged by the user on this FsFolder/Image

    def __str__(self):
        return 'FsItemTagSource.%s' % self.name


class FsItemTag(Base):
    """ an external tag (or a possible word of a tag) for an FsItem """
    __tablename__ = 'fs_item_tag'

    # primary key
    id = Column(Integer, primary_key=True)

    item_id = Column(Integer, ForeignKey('fs_item.id'))
    item = relationship(
        'FsItem', foreign_keys=[item_id], back_populates='item_tags')

    # secondary key

    type = Column(Enum(FsTagType))
    text = Column(String(collation='NOCASE'))

    # value
    idx = Column(Integer)       # tab_idx of this ItemTag in item.item_tags[]
    user_grouping = Column(Boolean)
        # first/last_ids were assigned by the user, not by _bind_fs_item_tags()
        # when type == TAG, user_grouping == False
    first_idx = Column(Integer) # tab_idx of the first FsItemTag in the bound tag
    last_idx =  Column(Integer) # tab_idx of the last FsItemTag in the bound tag
        # first_idx <= idx <= last_idx
        # when type == TAG, first_idx == last_idx

    bases = Column(String)
        # ,-separated list of suggested tag bases,
        #   e.g. 'band' or 'venue' or 'band, venue'
        # FIXME: this should just be an integer enum:
        # the possible lists are fixed by the code

    source = Column(Enum(FsItemTagSource))
    binding = Column(Enum(FsTagBinding))

    # if .binding.has_db_tag()
    db_tag_id = Column(Integer,ForeignKey('db_tag.id'))
    db_tag = relationship('DbTag', foreign_keys=[db_tag_id], uselist=False)

    Index('fs_item_tag', 'type', 'state', unique=False)

    @classmethod
    def insert(cls, session, item, idx, type, text, bases):
        # TODO: test in test_db
        # renumber the grouping indexes at and above idx
        for x in range(idx, len(item.item_tags)):
            it = item.item_tags[x]
            if it.first_idx >= idx:
                it.first_idx += 1
            it.last_idx += 1
        # create and insert the new item_tag
        item_tag = FsItemTag(
            item=item,
            first_idx=idx, last_idx=idx, user_grouping=False,
            type=type, text=text, bases=bases,
            source=FsItemTagSource.NONE,
            binding=FsTagBinding.UNBOUND, db_tag=None)
        if item_tag is not None:
            session.add(item_tag)
        return item_tag

    def delete(self, session):
        # TODO: test in test_db
        item = self.item
        idx = self.idx

        #ungroup
        self.del_grouping()

        # delete (hmmm...)
        item.item_tags.pop(idx)
        # session.delete(self) this ought to work too

        # renumber the grouping indexes above idx
        for x in range(idx, len(item.item_tags)):
            it = item.item_tags[x]
            if it.first_idx >= idx:
                it.first_idx -= 1
            it.last_idx -= 1

    def set_binding(self, binding, source, db_tag):
        if source == FsItemTagSource.DBTAG and binding == FsTagBinding.UNBOUND:
            raise ValueError
        self.binding = binding
        self.source = source
        self.db_tag = db_tag
        pass

    @classmethod
    def add_grouping(cls, item, idx_range):
        for idx in idx_range:
            item.item_tags[idx].first_idx = idx_range.start
            item.item_tags[idx].last_idx = idx_range.stop - 1

    def del_grouping(self):
        item = self.item
        for idx in range(self.first_idx, self.last_idx + 1):
            item.item_tags[idx].first_idx = idx
            item.item_tags[idx].last_idx = idx

    @classmethod
    def find_idx(cls, session, item, idx):
        return session.query(FsItemTag).filter_by(item=item, idx=idx).first()

    @classmethod
    def find_text(cls, session, type, text):
        return session.query(FsItemTag).filter_by(type=type, text=text).all()

    def diff_tup(self):
        # (w|t, state, bases)
        t = 'w' if self.type == FsTagType.WORD else 't'
        return t, self.text, self.bases

    def __str__(self):  # checked
        if self.type == FsTagType.WORD:
            idx = 'w%s/%s..%s' % (self.idx, self.first_idx, self.last_idx)
        else:
            idx = 't%s' % self.idx
        tgt = ' => ' + self.db_tag.pname() if self.db_tag is not None else ''
        return '[FsItemTag [%s] %s: %s/%s%s]' % (
            idx, self.text, self.binding, self.source, tgt)


class FsTagMapping(Base):
    """ a state -> DbTag map in an FsTagSource """
    __tablename__ = 'fs_tag_mapping'

    # key

    # FsTagSource <-->> FsTagMapping
    tag_source_id = Column(
        Integer, ForeignKey('fs_tag_source.id'), primary_key=True)
    tag_source = relationship('FsTagSource')
        # 'FsTagSource', backref=backref('fs_tag_mapping', uselist=False))

    text = Column(String(collation='NOCASE'), primary_key=True)
        # e.g. 'band|Tribe 8'

    # value

    binding = Column(Enum(FsTagBinding))
    # a state is marked to be ignored by setting binding=BOUND, db_tag=None

    # DbTag <->> FsTagMapping
    db_tag_id = Column(Integer, ForeignKey('db_tag.id'))
    db_tag = relationship('DbTag')
        # 'DbTag', backref=backref('fs_tag_mapping', uselist=False))

    @classmethod
    def add(cls, session, tag_source, text, binding, db_tag):
        if binding == FsTagBinding.UNBOUND:
            raise ValueError
        mapping = FsTagMapping(
            tag_source=tag_source, text=text, binding=binding, db_tag=db_tag)
        if mapping is not None: session.add(mapping)
        tags.on_fs_tag_mapping_added(session, mapping)
        return mapping

    @classmethod
    def find(cls, session, tag_source, text):
        return session.query(FsTagMapping).filter_by(
            tag_source=tag_source, text=text).first()

    @classmethod
    def add_if_nx(cls, session, tag_source, text, binding, db_tag):
        mapping = cls.find(session, tag_source, text)
        if mapping is None:
            return cls.add(session, tag_source, text, binding, db_tag)
        else:
            assert mapping.binding == binding
            assert mapping.db_tag == db_tag
            return mapping

    @classmethod
    def set(cls, session, tag_source, text, binding, db_tag):
        mapping = cls.find(session, tag_source, text)
        if mapping is None:
            if binding != FsTagBinding.UNBOUND:
                mapping = cls.add(session, tag_source, text, binding, db_tag)
        else:
            old_binding = mapping.binding
            if binding != old_binding:
                tags.on_fs_tag_mapping_removed(session, mapping)
                if binding == FsTagMapping.UNBOUND:
                    session.delete(mapping)
                    return None
            mapping.binding = binding
            mapping.db_tag = db_tag
            if binding != old_binding:
                tags.on_fs_tag_mapping_added(session, mapping)
        return mapping

    def leaf_text(self):
        x = self.text.rfind('|')
        if x == -1:
            return self.text
        else:
            # TODO: strip spaces around '|' when storing .state
            return self.text[x + 1:].lstrip(' ')

    def pname(self):
        return '%s => %s' % (
            self.text,
            self.db_tag.pname() if self.db_tag is not None else 'None'
        )

    def __str__(self):  # checked
        return '[FsTagMapping %s]' % self.pname()


class TagChange(Base):
    """ a timestamp-sorted list of new DbTags and FsTagMappings
        which have not yet been applied to FsFolders and FsImages
    """
    __tablename__ = 'tag_change'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    text = Column(String)

    Index('tag_change_index', 'timestamp', unique=False)

    @classmethod
    def clear(cls, session):
        """ Clear the global TagChange list """
        session.query(TagChange).delete()

    @classmethod
    def add(cls, session, text):
        """ Add <state> to the global TagChange list """
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

    def __str__(self):  # checked
        return '[TagChange %s @ %s]' % (self.text, str(self.timestamp))


class FsFolder(FsItem):
    """ a filesystem source from which DbFolder were imported
        if source.type is dir_set, a filesystem directory
        if source.type is file_set, a group of files with a common db_name prefix
    """
    __tablename__ = 'fs_folder'

    # isa FsItem (.item.name is the folder's FS pathname relative to FsSource.item.name)
    id = Column(Integer, ForeignKey('fs_item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsFolder'}

    # DbFolder date and db_name suggested by import/export code (e.g scan_dir_set)
    # may each be None
    # copied from the corresponding members in IEFolder
    # db_date = Column(Date)  # FIXME: remove
    db_date2_year = Column(Integer)
    db_date2_month = Column(Integer)
    db_date2_day = Column(Integer)
    db_date2 = composite(IMDate, db_date2_year, db_date2_month, db_date2_day)
    db_name = Column(String)

    # last-import timestamps
    last_scan = Column('last_scan', DateTime)
    last_import_tags = Column('last_import_tags', DateTime)

    # issues reported by import code
    issues = Column(Integer)                # a bitvector of IssueType[0] flags
    import_edit_level = Column(Integer)     # 0..max_import_edit_level

    # FsFolder <<-> FsSource
    source_id = Column(Integer, ForeignKey('fs_source.id'))
    source = relationship(
        'FsSource', foreign_keys=[source_id], back_populates='folders')

    # FsFolder <<-> DbFolder
    db_folder_id = Column(Integer, ForeignKey('db_folder.id'))
    db_folder = relationship(
        'DbFolder', foreign_keys=[db_folder_id], back_populates='fs_folders')

    # FsFolder <->> FsImage
    images = relationship(
        'FsImage', foreign_keys='[FsImage.folder_id]', back_populates='folder', lazy='dynamic')

    Index('fs_folder_index', 'source', 'db_name', unique=True)

    @classmethod
    def add(cls, session, source, name,
        db_date=None, db_name=None, db_folder=None
    ):
        db_date2 = None if db_date is None else IMDate(
            db_date.year, db_date.month, db_date.day)
        obj = cls(
            source=source, name=name, db_date2=db_date2, db_name=db_name, db_folder=db_folder)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, source, name):
        return session.query(FsFolder).filter_by(source=source, name=name).first()

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

    def __str__(self):  # checked
        return '[FsFolder %s]' % self.pname()


class FsImage(FsItem):
    """ a (family of) filesystem file(s) from which a DbImage was imported
        the filesystem could contain a .tif, a .psd, and a .jpg,
        and one FsImage would be created,
        with .image_types indicating which were found
    """
    __tablename__ = 'fs_image'

    # isa Item (db_name is <seq>[<suffix>], as with DbImage and FsImage)
    id = Column(Integer, ForeignKey('fs_item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsImage'}

    # FsImage -0-> ImageData: set by fg_finish_ie_work_item(), cleared by _set_db_image()
    data_id = Column(Integer, ForeignKey('image_data.id'), nullable=True)
    data = relationship('ImageData', foreign_keys=[data_id])

    # FsImage <<-> FsFolder
    folder_id = Column(Integer, ForeignKey('fs_folder.id'))
    folder = relationship(
        'FsFolder', foreign_keys=[folder_id], back_populates='images')

    # FsImage <<-> DbImage
    db_image_id = Column(Integer, ForeignKey('db_image.id'))
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

    def __str__(self):  # checked
        return '[FsImage %s]' % self.text()


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

def open_file_db(full_path, mode):
    if mode == 'w':
        try:
            os.remove(full_path)
        except Exception as ed:  # the path may not have existed in the first place
            pass
    return _open_db('sqlite:///' + full_path)

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
        session, 'D:', '\\photos',
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