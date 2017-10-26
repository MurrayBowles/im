''' database classes '''

import enum

from sqlalchemy import create_engine
engine = create_engine('sqlite:///:memory:', echo=True)
#TODO: postgresql

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy import LargeBinary, String, Table, Text
from sqlalchemy.orm import relationship

tagged_items = Table('tagged_items', Base.metadata,
    Column('tag_id', Integer, ForeignKey('tag.id')),
    Column('item_id', Integer, ForeignKey('item.id'))
)

class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text())
    thumbnail = LargeBinary()
    # Tag tree
    parent_id = Column(Integer, ForeignKey('tag.id'))
    children = relationship('Tag')
    parent = relationship('Tag', remote_side=[id])
    # Tag <<->> Item
    items = relationship('Item', secondary=tagged_items, back_populates='tags')

    def __repr__(self):
        return "<Tag %s>" % (self.name)


class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    type = Column(String(12))
    __mapper_args__ = {'polymorphic_identity': 'item', 'polymorphic_on': type}
    name = Column(String(100))
    description = Column(Text())
    thumbnail = LargeBinary()
    # Item <<->> Tag
    tags = relationship('Tag', secondary=tagged_items, back_populates='items')

    def __repr__(self):
        return "<Item(%s) %s>" % (self.type, self.name)


class Identity(Item):
    __tablename__ = 'identity'
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = { 'polymorphic_identity': 'identity' }


class Person(Identity):
    __tablename__ = 'person'
    id = Column(Integer, ForeignKey('identity.id'), primary_key=True)
    __mapper_args__ = { 'polymorphic_identity': 'person' }


class Place(Identity):
    __tablename__ = 'place'
    id = Column(Integer, ForeignKey('identity.id'), primary_key=True)
    __mapper_args__ = { 'polymorphic_identity': 'place' }


class Directory(Item):
    __tablename__ = 'directory'
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'directory'}
    # Directory tree
    parent_id = Column(Integer, ForeignKey('directory.id'))
    children = relationship('Directory', foreign_keys=[parent_id])
    parent = relationship('Directory', foreign_keys=[parent_id], remote_side=[id])
    # Directory <->> Image
    images = relationship('Image', foreign_keys='[Image.directory_id]', back_populates='directory')
    # Directory <->> FsDirectory
    fs_directories = relationship(
        'FsDirectory', foreign_keys='[FsDirectory.directory_id]', back_populates='directory')

    def print_tree(self, pfx='', ind='    ', print_images=False):
        print(pfx + str(self))
        for c in self.children:
            c.print_tree(pfx=pfx + ind, ind=ind, print_images=print_images)
        if print_images:
            for i in self.images:
                print(pfx + ind + str(i))


class Image(Item):
    __tablename__ = 'image'
    id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    __mapper_args__ = { 'polymorphic_identity': 'image' }
    # Image <<-> Directory
    directory_id = Column(Integer, ForeignKey('directory.id'))
    directory = relationship('Directory', foreign_keys=[directory_id], back_populates='images')
    # Image <->> FsImage
    fs_images = relationship(
        'FsImage', foreign_keys='[FsImage.image_id]', back_populates='image')


class DirectorySetType(enum.Enum):
    internal = 'internal'
    external = 'external'
    cd = 'cd'
    glacier = 'glacier'


class DirectorySet(Base):
    __tablename__ = 'directory_set'
    id = Column(Integer, primary_key=True)
    type = Column(Enum(DirectorySetType))
    pathname = Column(String(1024))
    description = Column(Text())
    online = Column(Boolean, default=False)
    last_sync = Column(DateTime)
    # DirectorySet <->> FsDirectory
    fs_directories = relationship(
        'FsDirectory', foreign_keys='[FsDirectory.directory_set_id]', back_populates='directory_set')

    def __repr__(self):
        return "<DirectorySet-%s %s>" % (self.type, self.pathname)

    def print_tree(self, pfx='', ind='    ', print_images=False):
        print(pfx + str(self))
        for d in self.fs_directories:
            d.print_tree(pfx=pfx + ind, ind=ind, print_images=print_images)


class FsDirectory(Base):
    __tablename__ = 'fs_directory'
    id = Column(Integer, primary_key=True)
    pathname = Column(String(1024))
    flattened = Column(Boolean, default=False)
    online = Column(Boolean, default=False)
    last_sync = Column(DateTime)
    # an FsDirectory has either a .directory_set or a .parent, but not both
    # FsDirectory <<-> DirectorySet
    directory_set_id = Column(Integer, ForeignKey('directory_set.id'))
    directory_set = relationship('DirectorySet', foreign_keys=[directory_set_id], back_populates='fs_directories')
    # FsDirectory tree
    parent_id = Column(Integer, ForeignKey('fs_directory.id'))
    children = relationship('FsDirectory', foreign_keys=[parent_id])
    parent = relationship('FsDirectory', foreign_keys=[parent_id], remote_side=[id])
    # FsDirectory <->> FsImage
    fs_images = relationship(
        'FsImage', foreign_keys='[FsImage.fs_directory_id]', back_populates='fs_directory')
    # FsDirectory <<-> Directory
    directory_id = Column(Integer, ForeignKey('directory.id'))
    directory = relationship('Directory', foreign_keys=[directory_id], back_populates='fs_directories')

    def __repr__(self):
        return "<FsDirectory %s>" % (self.pathname)

    def print_tree(self, pfx='', ind='    ', print_images=False):
        print(pfx + str(self))
        for c in self.children:
            c.print_tree(pfx=pfx + ind, ind=ind, print_images=print_images)
        if print_images:
            for i in self.fs_images:
                print(pfx + str(i))


class FsImage(Base):
    __tablename__ = 'fs_image'
    id = Column(Integer, primary_key=True)
    filename = Column(String(256))
    # FsImage <<-> FsDirectory
    fs_directory_id = Column(Integer, ForeignKey('fs_directory.id'))
    fs_directory = relationship('FsDirectory', foreign_keys=[fs_directory_id], back_populates='fs_images')
    # FsImage <<-> Image
    image_id = Column(Integer, ForeignKey('image.id'))
    image = relationship('Image', foreign_keys=[image_id], back_populates='fs_images')

    def __repr__(self):
        return "<FsImage %s>" % (self.filename)


def db_test():
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    color = Tag(name='color')
    session.add(color)
    session.commit()
    red = Tag(name='red', parent=color)
    green = Tag(name='green', parent_id=color.id)
    session.add_all([red, green])
    session.commit()
    for t in session.query(Tag).all():
        print(t)
    joe = Person(name='Joe')
    john = Person(name='John')
    caravan = Place(name='Caravan')
    d160222 = Directory(name='160222')
    dbefore = Directory(name='before', parent=d160222)
    i1234 = Image(name='160222-1234', directory=d160222)
    i1235 = Image(name='160222-1235', directory=d160222)
    session.add_all([joe, john, caravan, i1234, i1235, d160222, dbefore])
    session.commit()
    for i in session.query(Item).all():
        print(i)
    joe.tags.append(green)
    i1234.tags.append(green)
    red.items.append(john)
    red.items.append(caravan)
    d160222.tags.append(green)
    d160222.tags.append(red)
    for t in session.query(Tag).all():
        print(t)
        for i in t.items:
            print('-' + str(i))
    green.items.remove(joe)
    john.tags.remove(red)
    for t in session.query(Tag).all():
        print(t)
        for i in t.items:
            print('-' + str(i))
    print(str(d160222) + ':')
    for i in d160222.images:
        print('i-' + str(i))
    for c in d160222.children:
        print('d-' + str(c))
    e_photos = DirectorySet(type=DirectorySetType.internal, pathname='e:\photos')
    print(e_photos)
    fs_d160222 = FsDirectory(directory_set=e_photos, pathname="160222")
    d160222.fs_directories.append(fs_d160222)
    print(fs_d160222)
    fs_i1234 = FsImage(fs_directory=fs_d160222, filename="1234")
    fs_i1234.image = i1234
    fs_i1235 = FsImage(fs_directory=fs_d160222, filename="1235")
    i1235.fs_images.append(fs_i1235)
    fs_before = FsDirectory(parent=fs_d160222, pathname="before")
    print(fs_before)
    session.add_all([e_photos, fs_d160222, fs_i1234, fs_i1235, fs_before])
    print('tree')
    session.commit()
    e_photos.print_tree(print_images=True)
    d160222.print_tree(print_images=True)
    fs_d160222.directory.print_tree(print_images=True)
