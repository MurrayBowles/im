''' database classes '''

from enum import Enum

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import Boolean, Column, Date, DateTime, Enum
from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy import LargeBinary, String, Table, Text
from sqlalchemy.orm import backref, relationship

from ie_cfg import IEFolderAct, IEImageAct


''' DbXxx: the database's representation of folders/images/tags/notes '''

# DbTag <<->> DbItem
tagged_items = Table('tagged_items', Base.metadata,
    Column('tag_id', Integer, ForeignKey('db-tag.id')),
    Column('item_id', Integer, ForeignKey('db-item.id'))
)

class DbItem(Base):
    ''' something which has a name and can be tagged: a Folder, Collection, Image, or Tag '''
    __tablename__ = 'db-item'
    id = Column(Integer, primary_key=True)

    type = Column(String(10)) # 'Collection' | 'Folder' | 'Image' | 'Tag'
    __mapper_args__ = {'polymorphic_identity': 'Item', 'polymorphic_on': type}

    name = Column(String(100))

    # DbItem <<->> DbTag
    tags = relationship('DbTag', secondary=tagged_items, back_populates='items')

    if False:
        # DbItem <->> DbNote
        notes = relationship('DbNote', foreign_keys='[DbNote.item_id]', back_populates='item')

    def __repr__(self):
        # this should always be overloaded
        return "<Db%s %s>" % (self.type, self.name)


def yymmdd(iso_date):
    ''' YYYY-MM-DD => YYMMDD '''
    return str(iso_date)[2:].replace('-', '')


class DbFolder(DbItem):
    ''' represents a single photo-shooting session '''
    __tablename__ = 'db-folder'

    # isa DbItem
    id = Column(Integer, ForeignKey('db-item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'Folder'}

    date = Column(Date)

    # DbFolder <->> DbImage
    images = relationship('DbImage', foreign_keys='[DbImage.folder_id]', back_populates='folder')

    if False:
        # DbFolder <->> FsFolder
        fs_folders = relationship(
            'FsFolder', foreign_keys='[FsFolder.db_folder_id]', back_populates='db_folder')

        # DbFolder -> thumbnail DbImage
        thumbnail_id = Column(Integer, ForeignKey('thumbnail.id'))
        thumbnail = relationship("DbImage", backref=backref("db-folder", uselist=False))

    Index('db-folder-index', 'name', unique=True)

    def __repr__(self):
        return '<DbFolder %s %s>' % (yymmdd(self.date), self.name)


class DbCollection(DbItem):
    ''' a collection of images from multiple folders '''
    __tablename__ = 'db-collection'

    # isa DbItem
    id = Column(Integer, ForeignKey('db-item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'db-collection'}

    if False:
        # DbCollection <<->> DbImage
        images = relationship('DbImage', secondary=image_collections, back_populates='collections')

        # DbCollection -> thumbnail DbImage
        thumbnail_id = Column(Integer, ForeignKey('thumbnail.id'))
        thumbnail = relationship("DbImage", backref=backref("db-collection", uselist=False))

    Index('db-collection-index', 'name', unique=True)

    def __repr__(self):
        return '<Collection %s>' % self.name


class DbImage(DbItem):
    ''' a single image (usually with multiple files: NEF/TIFF/PSD/JPEG) '''
    __tablename__ = 'db-image'

    # isa DbItem
    id = Column(Integer, ForeignKey('db-item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'Image'}

    thumbnail = Column(LargeBinary())
    zzz = Column(Integer)

    # DbImage <<-> DbFolder
    folder_id = Column(Integer, ForeignKey('db-folder.id'))
    folder = relationship('DbFolder', foreign_keys=[folder_id], back_populates='images')

    if False:
        # DbImage <<->> DbCollection
        collections = relationship('DbCollection', secondary=image_collections, back_populates='images')

        # DbImage <->> FsImage (filesystem locations where the image files are found)
        fs_images = relationship(
            'FsImage', foreign_keys='[FsImage.db_image_id]', back_populates='db_image')

    Index('db-image-index', 'folder.date', 'name')

    def __repr__(self):
        return '<Image %s-%s>' % (yymmdd(self.folder.date), self.name)


class DbTagType(Enum):
    '''' the relation between a tag and its .base_tag '''

    BASE = 1  # this is a normal base tag; .base_tag is None
    IDENTITY_IS = 2  # this tag refers to the person/place/thing represented by .base_tag
    REPLACED_BY = 3  # this tag has been replaced by .base_tag
    DEPRECATED = 4  # this tag is deprecated; .base_tag is None


class DbTag(DbItem):
    ''' a hierarchical tag on a DbItem '''
    __tablename__ = 'db-tag'

    # isa DbItem
    id = Column(Integer, ForeignKey('db-item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'db-tag'}

    # DbTag tree
    parent_id = Column(Integer, ForeignKey('db-tag.id'), nullable=True)
    parent = relationship('DbTag', remote_side=[id], foreign_keys=[parent_id])

    # DbTag <<->> DbItem
    items = relationship('DbItem', secondary=tagged_items, back_populates='tags')

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

    def __repr__(self):
        def tag_str(tag):
            return tag.name if tag.parent is None else tag_str(tag.parent) + '|' + tag.name

        return "<Tag %s>" % tag_str(self)


