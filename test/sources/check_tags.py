""" library to initialize and check DbTags, FsTagMappings, and FsItemTags """

import db
import tags

'''
run(op)

op:
    ('{+-}tag',     tag-spec)
    ('{+-}mapping', mapping-spec)
    ('{+-}binding', binding-spec)
    ('{+-}folder',  folder-spec)
    '[' cfg-op,... ']'
    
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
    
folder-spec:
    ('folder-name', list of item-spec [, image-spec])
    '[' folder-spec,... ']'
image-spec:
    ('image-name', '[' item-spec,... ']')
item-spec:
    ('w', word-list)    e.g. ['green', 'day']
    ('t', 'tag-text')   e.g. 'band|Green Day'
'''

class Ctx:
    def __init__(self, session):
        self.session = session
        self.tags = {}                  # tag-label => DbTag
        self.mappings = {}              # ('g|l', 'tag-text') => FsTagMapping
        self.local_tag_source = None    # FsTagSource
        self.db_folders = {}            # folder-name => DbFolder
        self.fs_folders = {}            # folder-name => FsFolder
        self.db_images = {}             # image-name => DbImage
        self.fs_images = {}             # image-name => FsImage

    def run(self, cfg_op):
        dispatch = {
            '+tag':         self.add_tag,
            '-tag':         self.del_tag,
            '+mapping':     self.add_mapping,
            '-mapping':     self.del_mapping
            #'+binding':     self.add_binding,
            #'-binding':     self.del_binding,
            #'+folder':      self.add_folder,
            #'-folder':      self.del_folder,
            #'!f-grouping':  self.set_folder_grouping,
            #'!i-grouping':  self.set_image_grouping
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
                try:
                    fn(spec)
                except Exception as ed:
                    pass
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


'''
check_item_tags(list of folder-tag-check) 

folder-tag-check:
    ( 'fs-folder-name', list of item-tag-check [, list of image-tag-check )
image-tag-check:
    ( 'fs-image-name', list of item-tag-check )
    
item-tag-check:
    ( 'w<item-tag-flags>', word-list, 'tag-label' )
    ( 't<item-tag-flags>', 'tag-text', 'tag-label' ) 
item-tag-flags: {b|s|u}{n|t|g|l|d}
    b: BOUND, s: SUGGESTED, u: UNBOUND
    n: NONE, t: TAG, g: GLOBAL, l: LOCAL, d: DIRECT
'''