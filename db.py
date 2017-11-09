''' database classes '''

from enum import Enum as PyEnum
from enum import IntEnum as PyIntEnum

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import Boolean, Column, Date, DateTime, Enum
from sqlalchemy import Float, ForeignKey, Index, Integer
from sqlalchemy import LargeBinary, String, Table, Text
from sqlalchemy.orm import backref, relationship

from ie_cfg import IEFolderAct, IEImageAct

# DbXxx: the database's representation of folders/images/tags/notes

# DbTag <<->> Item
tagged_items = Table('tagged-items', Base.metadata,
    Column('tag_id', Integer, ForeignKey('db-tag.id')),
    Column('item_id', Integer, ForeignKey('item.id'))
)


# DbImage <<->> DbCollection
image_collections = Table('image-collections', Base.metadata,
    Column('image_id', Integer, ForeignKey('db-image.id')),
    Column('collection_id', Integer, ForeignKey('db-collection.id'))
)


class Item(Base):
    ''' something which has a name and can be tagged: a Folder, Collection, Image, or Tag '''
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)

    type = Column(String(10)) # 'Collection' | 'Folder' | 'Image' | 'Tag'
    __mapper_args__ = {'polymorphic_identity': 'Item', 'polymorphic_on': type}

    name = Column(String(100))

    # Item <<->> DbTag
    tags = relationship('DbTag', secondary=tagged_items, back_populates='items')

    # Item <->> DbNote
    notes = relationship('DbNote', foreign_keys='[DbNote.item_id]', back_populates='item')

    def __repr__(self):
        # this should always be overloaded
        return "<%s %s>" % (self.type, self.name)


def yymmdd(iso_date):
    ''' convert YYYY-MM-DD => YYMMDD. '''
    return str(iso_date)[2:].replace('-', '')


class DbFolder(Item):
    ''' represents a single photo-shooting session '''
    __tablename__ = 'db-folder'

    # isa Item (name is
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbFolder'}

    date = Column(Date)

    # DbFolder <->> DbImage
    images = relationship('DbImage', foreign_keys='[DbImage.folder_id]', back_populates='folder')

    # DbFolder <->> FsFolder
    fs_folders = relationship(
        'FsFolder', foreign_keys='[FsFolder.db_folder_id]', back_populates='db_folder')

    # DbFolder -> thumbnail DbImage
    thumbnail_id = Column(Integer, ForeignKey('db-image.id'))
    thumbnail = relationship('DbImage', foreign_keys='[DbFolder.thumbnail_id]')

    Index('db-folder-index', 'date, ''name', unique=True)

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
        ''' find or create a DbFolder: return db_folder, is_new'''
        db_folder = cls.find(session, date, name)
        if db_folder is None:
            return cls.add(session, date, name), True
        else:
            return db_folder, False

    def __repr__(self):
        return '<DbFolder %s %s>' % ( (self.date), self.name)


class DbCollection(Item):
    ''' a collection of images from multiple folders '''
    __tablename__ = 'db-collection'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbCollection'}

    # DbCollection <<->> DbImage
    images = relationship('DbImage', secondary=image_collections, back_populates='collections')

    # DbCollection -> thumbnail DbImage
    thumbnail_id = Column(Integer, ForeignKey('db-image.id'))
    thumbnail = relationship("DbImage", foreign_keys='[DbCollection.thumbnail_id]')

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
    ''' a single image (usually with multiple files: NEF/TIFF/PSD/JPEG) '''
    __tablename__ = 'db-image'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbImage'}

    thumbnail = Column(LargeBinary())
    thumbnail_timestamp = Column(DateTime)

    # DbImage <<-> DbFolder
    folder_id = Column(Integer, ForeignKey('db-folder.id'))
    folder = relationship('DbFolder', foreign_keys=[folder_id], back_populates='images')

    # DbImage <<->> DbCollection
    collections = relationship('DbCollection', secondary=image_collections, back_populates='images')

    # DbImage <->> FsImage (filesystem locations where the image files are found)
    fs_images = relationship(
        'FsImage', foreign_keys='[FsImage.db_image_id]', back_populates='db_image')

    Index('db-folder-image-index', 'folder_id', 'name', unique=True)
    Index('db-date-image-index', 'folder.date', 'name')

    @classmethod
    def add(cls, session, folder, name):
        obj = cls(folder=folder, name=name)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, db_folder,  name):
        return session.query(DbImage).filter_by(folder_id=db_folder.id, name=name).first()
    # TODO: find_in_date vs find_in_folder

    @classmethod
    def get(cls, session, folder, name):
        db_image = cls.find(session, folder, name)
        if db_image is None:
            return cls.add(session, folder, name), True
        else:
            return db_image, False

    def __repr__(self):
        return '<Image %s-%s>' % (yymmdd(self.folder.date), self.name)


class DbTagType(PyIntEnum):
    '''' the relation between a tag and its .base_tag '''

    BASE = 1        # this is a normal (base) tag; .base_tag is None
    IDENTITY_IS = 2 # this tag refers to the person/place/thing represented by .base_tag
    REPLACED_BY = 3 # this tag has been replaced by .base_tag
    DEPRECATED = 4  # this tag is deprecated; .base_tag is None


class DbTag(Item):
    ''' a hierarchical tag on a Item '''
    __tablename__ = 'db-tag'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'DbTag'}

    # DbTag tree
    parent_id = Column(Integer, ForeignKey('db-tag.id'), nullable=True)
    parent = relationship('DbTag', remote_side=[id], foreign_keys=[parent_id])
    children = relationship('DbTag', foreign_keys='[DbTag.parent_id]', back_populates='parent')

    # DbTag <<->> Item
    items = relationship('Item', secondary=tagged_items, back_populates='tags')

    # DbTag -> replacement or identity DbTag
    tag_type = Column(Integer)  # DbTagType
    base_tag_id = Column(Integer, ForeignKey('db-tag.id'), nullable=True)
    base_tag = relationship('DbTag', remote_side=[id], foreign_keys=[base_tag_id])

    def base(self):
        return {
            DbTagType.BASE: self,
            DbTagType.IDENTITY_IS: self,
            DbTagType.REPLACED_BY: self.base_tag,
            DbTagType.DEPRECATED: None
        }[self.type.value]

    @classmethod
    def add(cls, session, parent, name, tag_type=DbTagType.BASE, base_tag=None):
        obj = cls(parent=parent, name=name, tag_type=tag_type.value, base_tag=base_tag)
        if obj is not None: session.add(obj)
        return obj

    def __repr__(self):
        def tag_str(tag):
            return tag.name if tag.parent is None else tag_str(tag.parent) + '|' + tag.name

        return "<Tag %s>" % tag_str(self)


class DbTextType(PyIntEnum):
    ''' the syntax of a DbNote's text '''
    TEXT = 1        # simple text
    URL = 2         # a URL


class DbNoteType(Base):
    ''' the type of a DbNote (e.g. name, location, PBase page,...) '''
    __tablename__ = 'db-note-type'
    id = Column(Integer, primary_key=True)

    name = Column(String(30))
    text_type = Column(Integer)  # DbNoteType enumeration

    @classmethod
    def add(cls, session, name, text_type):
        obj = cls(name=name, text_type=text_type.value)
        if obj is not None: session.add(obj)
        return obj

    def __repr__(self):
        return '<NoteType %s: %s>' % (self.name, DbTextType(self.text_type).name)

class DbNote(Base):
    ''' a text note on a Item '''
    __tablename__ = 'db-note'

    # DbNote <<-> Item (a Item contains a list of DbNotes)
    item_id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    item = relationship('Item', foreign_keys=[item_id], back_populates='notes')
    seq = Column(Float, primary_key=True)  # GUI ordering

    text = Column(String(100))

    # DbNote -> DbNoteType
    type_id = Column(Integer, ForeignKey('db-note-type.id'))
    type = relationship("DbNoteType", backref=backref("db-note", uselist=False))

    @classmethod
    def add(cls, session, item, seq, note_type, text=''):
        obj = cls(item=item, seq=seq, type=note_type, text=text)
        if obj is not None: session.add(obj)
        return obj

    def __repr__(self):
        return '<Note %s[%s%s]>' % (
            str(self.item),
            self.type.name,
            str(self.seq) if self.seq != 1 else '')


''' FsXxx: an inventory of what's been imported when, and from where in the filesystem '''


class FsTagSource(Base):
    ''' the person/organization who tagged a set of folders/images being imported '''
    __tablename__ = 'fs-tag-source'

    id = Column(Integer, primary_key=True)
    description = Column(String(100))

    @classmethod
    def add(cls, session, description=''):
        obj = cls(description=description)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find_id(cls, session, id):
        return session.query(FsTagSource).filter_by(id=id).first()

    def __repr__(self):
        return '<FsTagSource %s>' % self.description


class FsSourceType(PyIntEnum):
    ''' whether the FsSource is a directory of directories or a directory of image files
        IntEnum because SQLAlchemy creates int python attributes when you say Column(Enum)
    '''
    DIR = 1
    FILE = 2


class FsSource(Item):
    ''' the filesystem parent directory from which a set of folders/images was imported '''
    __tablename__ = 'fs-source'

    # isa Item
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsSource'}

    # secondary key (TODO index? enforce uniqueness?)
    volume = Column(String(32)) # source volume: '<volume letter>:' or '<volume label>'
    path = Column(String(260))  # source pathname

    source_type = Column(Enum(FsSourceType))
    readonly = Column(Boolean)

    # FsSource -> FsTagSourceId
    tag_source_id = Column(Integer, ForeignKey('fs-tag-source.id'))
    tag_source = relationship('FsTagSource', backref=backref('fs-tag-source', uselist=False))

    # FsSource <->> FsFolder
    folders = relationship(
        'FsFolder', foreign_keys='[FsFolder.source_id]', back_populates='source')

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
        return session.query(FsSource).filter_by(volume=volume, path=path).first()

    def label(self):
        return self.volume if self.volume is not None and not self.volume.endswith(':') else None

    def text(self):
        s = ''
        if self.name is not None:
            s += '(%s) ' % (self.name)
        if self.volume.endswith(':'):
            s + self.volume
        else:
            s += '[%s]' % (self.volume)
        s += self.path
        return s

    def __repr__(self):
        return '<FsSource %s>' % (self.text())


class FsFolder(Item):
    ''' a filesystem source from which DbFolder were imported
        if source.type is dir_set, this was a filesystem directory
        if source.type is file_set, this was a group of files with (say) a common prefix
    '''
    __tablename__ = 'fs-folder'

    # isa Item (.name is the same as IEFolder.fs_name)
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsFolder'}

    # last-import timestamps
    last_scan = Column('last-scan', DateTime)
    last_import_tags = Column('last-import-tags', DateTime)

    # FsFolder <<-> FsSource
    source_id = Column(Integer, ForeignKey('fs-source.id'))
    source = relationship('FsSource', foreign_keys=[source_id], back_populates='folders')

    # FsFolder <<-> DbFolder
    db_folder_id = Column(Integer, ForeignKey('db-folder.id'))
    db_folder = relationship('DbFolder', foreign_keys=[db_folder_id], back_populates='fs_folders')

    # FsFolder <->> FsImage
    images = relationship('FsImage', foreign_keys='[FsImage.folder_id]', back_populates='folder')

    Index('fs-folder-index', 'source_id', 'name', unique=True)

    @classmethod
    def add(cls, session, source, fs_name, db_folder=None):
        obj = cls(source=source, name=fs_name, db_folder=db_folder)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, source, name):
        return session.query(FsFolder).filter_by(source_id=source.id, name=name).first()

    @classmethod
    def get(cls, session, source, fs_name, db_folder=None):
        fs_folder = cls.find(session, source, fs_name)
        if fs_folder is None:
            return cls.add(session, source, fs_name, db_folder), True
        else:
            return fs_folder, False

    def __repr__(self):
        return "<FsFolder %s|%s>" % (str(self.source), self.name)


class FsImage(Item):
    ''' a (family of) filesystem file(s) from which a DbImage was imported
        the filesystem could contain a .tif, a .psd, and a .jpg, and one FsImage would be created,
        with .image_types indicating which were found
    '''
    __tablename__ = 'fs-image'

    # isa Item (.name is the same as IEImage.name)
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'FsImage'}

    # FsImage <<-> FsFolder
    folder_id = Column(Integer, ForeignKey('fs-folder.id'), primary_key=True)
    folder = relationship('FsFolder', foreign_keys=[folder_id], back_populates='images')

    # FsImage <<-> DbImage
    db_image_id = Column(Integer, ForeignKey('db-image.id'))
    db_image = relationship('DbImage', foreign_keys=[db_image_id], back_populates='fs_images')

    @classmethod
    def add(cls, session, folder, name, db_image=None):
        obj = cls(folder=folder, name=name, db_image=db_image)
        if obj is not None: session.add(obj)
        return obj

    @classmethod
    def find(cls, session, folder, name):
        return  session.query(FsImage).filter(
            FsImage.folder_id == folder.id, FsImage.name == name
        ).first()

    @classmethod
    def get(cls, session, folder, name, db_image=None):
        ''' find or add an FsImage: return fs_image, is_new '''
        fs_image = cls.find(session, folder, name)
        if fs_image is None:
            return cls.add(session, folder, name, db_image), True
        else:
            return fs_image, False


    def __repr__(self):
        return "<FsImage %s/%s>" % (str(self.folder), self.name)

session = None

def _open_db(url):
    ''' open a database and return a session '''
    global session
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def open_mem_db():
    ''' open a memory database '''
    return _open_db('sqlite:///:memory:')

def close_db():
    ''' close the database '''
    pass

def open_preloaded_mem_db():
    session = open_mem_db()
    ts1 = FsTagSource.add(session, 'standard')
    ts2 = FsTagSource.add(session, 'corbett')
    s1 = FsSource.add(session, 'main1234', '/photos', FsSourceType.DIR, True, ts1)
    s2 = FsSource.add(session, 'C:', '/photos', FsSourceType.DIR, False, ts1)
    s1 = FsSource.add(session, 'HD2', '/corbett-psds', FsSourceType.FILE, False, ts2)
    session.commit()