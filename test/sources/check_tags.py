""" library to initialize and check DbTags, FsTagMappings, and FsItemTags """

from datetime import date

import db
import tags

'''
execute(op)

op:
    ('{+-}tag',         tag-spec)
    ('{+-}mapping',     mapping-spec)
    ('{+-}binding',     binding-spec)
    ('{+-}db-folder',   folder-name)
    ('?db-folder-tags', db-folder-tag-spec)
    ('!source,          source-obj)
    ('{+-}fs-folder',   fs-folder-spec)
    ('?fs-folder-tags', fs-folder-tag-spec)
    '[' op,... ']'
    
tag-spec:
    ('tag-label', 'tag-text')
        e.g. ('cop', 'band|Christ On Parade')
    '[' tag-spec,... ']'
    
mapping-spec:
    ('mapping-flags', 'tag-text', 'tag-label' | None)
    '[' mapping-spec,... ']'
mapping-flags: {b|s}{g|l}
    b: BOUND, s: SUGGESTED
    g: GLOBAL, l: LOCAL
        e.g. ('bg', 'C.O.P.', 'cop') 
    
db-folder-tag-spec:
    ( 'db-folder-name', list of db-tag-spec [, list of db-image-tag-spec )
db-image-tag-spec:
    ( 'db-image-name', list of db-tag-spec )    
db_tag_spec:
    
    
fs-folder-spec:
    ('folder-name', '[' item-spec,... ']' [, fs-image-spec])
    '[' folder-spec,... ']'
fs-image-spec:
    ('image-name', '[' item-spec,... ']')
item-spec:
    ('w', word-list)    e.g. ['green', 'day']
    ('t', 'tag-text')   e.g. 'band|Green Day'
    
fs-folder-tag-spec:
    ( 'fs-folder-name', list of fs-item-tag-spec [, list of fs-image-tag-spec )
fs-image-tag-spec:
    ( 'fs-image-name', list of fs-item-tag-spec )
    
fs-item-tag-spec:
    ( 'w<fs-item-tag-flags>', word-list, 'tag-label' )
    ( 't<fs-item-tag-flags>', 'tag-text', 'tag-label' ) 
fs-item-tag-flags: {b|s|u}{n|t|g|l|d}
    b: BOUND, s: SUGGESTED, u: UNBOUND
    n: NONE, t: TAG, g: GLOBAL, l: LOCAL, d: DIRECT
'''

class Ctx:
    def __init__(self, session):
        self.session = session
        self.tags = {}                  # tag-label => DbTag
        self.mappings = {}              # ('g|l', 'tag-text') => FsTagMapping
        self.fs_source = None           # FsSource, set by '!source'
        self.local_tag_source = None    # FsTagSource
        self.db_folders = {}            # folder-name => DbFolder
        self.fs_folders = {}            # (fs_source, folder-name) => FsFolder
        self.db_images = {}             # image-name => DbImage
        self.fs_images = {}             # image-name => FsImage

    def execute(self, cfg_op):
        dispatch = {
            '+tag':             self.add_tag,
            '-tag':             self.del_tag,
            '+mapping':         self.add_mapping,
            '-mapping':         self.del_mapping,
            '!source':          self.set_fs_source,
            '?fs-folder-tag':   self.check_fs_folder_tags,
            '+db_folder':       self.add_db_folder,
            '+fs_folder':       self.add_fs_folder,
            #'+binding':        self.add_binding,
            #'-binding':        self.del_binding,
            #'-folder':         self.del_folder,
            #'!f-grouping':     self.set_folder_grouping,
            #'!i-grouping':     self.set_image_grouping
        }
        def map_op_tree(op):
            if type(op) is list:
                for o in op:
                    map_op_tree(o)
            else:
                map_spec_tree(dispatch[op[0]], op[1])
        def map_spec_tree(fn, spec):
            if type(spec) is list:
                for s in spec:
                    map_spec_tree(fn, s)
            else:
                fn(spec)
        map_op_tree(cfg_op)

    def _sql_cleanup(self, obj_list):
        map(self.session.delete, obj_list)

    def cleanup(self):
        map(self._sql_cleanup, [
            self.fs_images,
            self.db_images,
            self.fs_folders,
            self.db_folders,
            self.mappings,
            self.tags.values()
        ])
        if self.local_tag_source is not None:
            self.session.delete(self.local_tag_source)

    def add_tag(self, tag_spec):
        # unpack the tag-spec
        tag_label = tag_spec[0]
        tag_text = tag_spec[1]

        db_tag = db.DbTag.get_expr(self.session, tag_text)
        self.tags[tag_label] = db_tag
        return db_tag

    def del_tag(self, op):
        # unpack the tag-spec
        tag_label = tag_spec[0]

        db_tag = self.tags[tag_label]
        self.session.delete(db_tag)

    def get_tag_source(self, scope_char):
        if scope_char == 'g':
            tag_source = db.global_tag_source
        else:
            if self.local_tag_source is None:
                self.local_tag_source = db.FsTagSource.add(self.session, 'test')
            tag_source = self.local_tag_source
        return tag_source

    def add_mapping(self, mapping_spec):
        # unpack the mapping-spec
        binding_char = mapping_spec[0][0]
        scope_char = mapping_spec[0][1]
        tag_text = mapping_spec[1]
        tag_label = mapping_spec[2]

        tag_source = self.get_tag_source(scope_char)
        binding = (
            db.FsTagBinding.SUGGESTION if binding_char == 's'
            else db.FsTagBinding.BOUND)
        db_tag = None if tag_label is None else self.tags[tag_label]
        mapping = db.FsTagMapping.add(
            self.session, tag_source, tag_text, binding, db_tag)
        self.mappings[(scope_char, tag_text)] = mapping
        return mapping

    def del_mapping(self, mapping_spec):
        # unpack the mapping-spec
        scope_char = mapping_spec[0][1]
        tag_text = mapping_spec[1]

        mapping = self.mappings[(scope_char, tag_text)]
        self.session.delete(mapping)

    def set_fs_source(self, source):
        self.fs_source = source

    def _check_fs_item_tags(self, item, item_tag_specs):
        def find_item_tag(text):
            for item_tag in item.item_tags:
                if item_tag.text.lower() == text.lower():
                    return item_tag
            else:
                assert False

        def check_item_tag(self, item_tag):
            assert item_tag.type == tag_type
            if item_tag.binding != binding:
                pass
            assert item_tag.binding == binding
            if item_tag.source != source:
                pass
            assert item_tag.source == source
            if binding != db.FsTagBinding.UNBOUND:
                if tag_label is not None:
                    db_tag = self.tags[tag_label]
                    if item_tag.db_tag is not db_tag:
                        pass
                    assert item_tag.db_tag is db_tag
            pass

        for item_tag_spec in item_tag_specs:
            # unpack the item_tag_spec
            flags = item_tag_spec[0]
            key = item_tag_spec[1]
            tag_label = None if len(item_tag_spec) < 3 else item_tag_spec[2]

            # unpack the flags
            tag_type = {
                'w': db.FsTagType.WORD,
                't': db.FsTagType.TAG
            }[flags[0]]
            binding = {
                'u': db.FsTagBinding.UNBOUND,
                's': db.FsTagBinding.SUGGESTED,
                'b': db.FsTagBinding.BOUND
            }[flags[1]]
            source = {
                'n': db.FsItemTagSource.NONE,
                't': db.FsItemTagSource.DBTAG,
                'g': db.FsItemTagSource.GLOBTS,
                'l': db.FsItemTagSource.FSTS,
                'f': db.FsItemTagSource.FSTS
            }[flags[2]]

            if tag_type == db.FsTagType.TAG:
                item_tag = find_item_tag(key)
                check_item_tag(self, item_tag)
            else: # db.FsTagType.WORD
                item_tag0 = find_item_tag(key[0])
                check_item_tag(self, item_tag0)
                for x in range(1, len(key)):
                    item_tag = find_item_tag(key[x])
                    assert item_tag.idx == item_tag0.idx + x
                    assert item_tag.first_idx == item_tag0.idx
                    check_item_tag(self, item_tag)
            pass

    def check_fs_folder_tags(self, folder_tag_spec):
        # unpack the folder-tag-spec
        folder_name = folder_tag_spec[0]
        folder_item_tag_specs = folder_tag_spec[1]
        image_tag_specs = (
            [] if len(folder_tag_spec) < 3 else folder_tag_spec[2])

        folder = db.FsFolder.find(self.session, self.fs_source, folder_name)
        assert folder is not None
        self._check_fs_item_tags(folder, folder_item_tag_specs)
        for image_tag_spec in image_tag_specs:
            # unpack the image_tag_spec
            image_name = image_tag_spec[0]
            image_item_tag_specs = image_tag_spec[1]

            image = db.FsImage.find(self.session, folder, image_name)
            assert image is not None
            self._check_fs_item_tags(image, image_item_tag_specs)
        pass

    def add_db_folder(self, folder_name):
        db_folder = db.DbFolder.add(self.session, date.today(), folder_name)
        self.db_folders[folder_name] = db_folder
        return db_folder

    def add_fs_folder(self, folder_spec):
        # unpack the folder-spec
        folder_name = folder_spec[0]
        folder_item_specs = folder_spec[1]
        image_specs = [] if len(folder_spec) < 3 else folder_spec[2]

        try:
            db_folder = self.db_folders[folder_name]
        except:
            db_folder = None
        fs_folder = db.FsFolder.add(
            session, self.fs_source, folder_name,
            date.today(), folder_name, db_folder)
        self.fs_folders[(self.fs_source, folder_name)] = fs_folder
        return fs_folder