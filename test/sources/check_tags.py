""" library to initialize and check DbTags, FsTagMappings, and FsItemTags """

from datetime import date, datetime, time

import db
import ie_fs
import tags

'''
execute(op)

op:
    ('{+-}tag',                 tag-spec)
    ('{+-}mapping',             mapping-spec)
    ('{+-}binding',             binding-spec)
    ('{+-}db-folder',           folder-name)
    ('!db-folder-tag',          db-folder-tag-spec)
    ('?db-folder-tag',          db-folder-tag-pattern)
    ('!source,                  fs-source-spec)
    ('{+-}fs-folder',           fs-folder-spec)
    ('!ie-folder',              ie-folder-spec)
    ('?ie-folder',              ie-folder-spec)
    ('set-fs-folder_tags',      (fs-folder-name, ie-folder-name))
    ('rebind-fs-folder_tags',   fs-folder-name)
    ('?fs-folder-tag',          fs-folder-tag-pattern)
    '[' op,... ']'
    
tag-spec:
    ('tag-label', 'tag-text')
        e.g. ('cop', 'band|Christ On Parade')
    'tag-text'
        tag-label == tag-text
    '[' tag-spec,... ']'
    
mapping-spec:
    ('mapping-flags', 'tag-text', 'tag-label' | None)
    '[' mapping-spec,... ']'
mapping-flags: {b|s}{g|l}
    b: BOUND, s: SUGGESTED
    g: GLOBAL, l: LOCAL
        e.g. ('bg', 'C.O.P.', 'cop') 
        
db-folder-tag-spec:
    ( 'db-folder-name', '[' db-item-tag-spec,... ']'
        [, '[' db-image-tag-spec ,... ']' ] )
db-image-tag-spec:
    ( 'db-image-name', '[' db-item-tag-spec,... ']' )
db-item-tag-spec:
    ( db-item-tag-flag-spec, 'tag-label' )
db-item-tag-flag-spec: {+-deb}+
    +: add, -: delete
    d: DIRECT, e: EXTERNAL, b: BLOCKED
   
db-folder-tag-pattern:
    ( 'db-folder-name', '[' db-item-tag-pattern,... ']'
        [, '[' db-image-tag-pattern,... ']' )
db-image-tag-pattern:
    ( 'db-image-name', '[' db-item-tag-pattern,... ']' )    
db-item-tag-pattern:
    ( db-item-tag-flag-pattern, 'tag-label' )
db-item-tag-flag-pattern: {0} | {=&~}{deb}+
    0: tag must NOT be present
    =: flags must exactly match
    &: flags must all be present
    ~: flags must all be absent
    d: DIRECT, e: EXTERNAL, b: BLOCKED
    
fs-source-spec:
    fs-source-obj
    ( fs-source-flags, 'volume-name', 'path' )
    '[' fs-source-spec,... ']'
fs-source-flags: {d|f|w|r}
    d: DIR, f:se FILE, w: WEB, r: read-only
    
fs-folder-spec:
    ('folder-name', '[' 'image-name' ,... ']')
    '[' fs-folder-spec,... ']'
    
ie-folder-spec:
    ( 'ie-folder-name', 'folder-tag-bases', '[' ie-item-tag-spec,... ']'
        [, 'image-tag-bases', '[' ie-image-spec,... ']' ] )
ie-image-spec:
    ( 'ie-image-name', '[' ie-item-tag-spec,... ']' )
ie-item-tag-spec:
    ( '{a|b|u|w|n}', 'tag-text' )    
    a: AUTO, b: BASED, u: UNBASED, w: WORD, n: NOTE
 
fs-folder-tag-pattern:
    ( 'fs-folder-name', '[' fs-item-tag-pattern,... ']'
        [, '[' fs-image-tag-pattern,... ']' ] )
fs-image-tag-pattern:
    ( 'fs-image-name', '[' fs-item-tag-pattern,... ']' )
fs-item-tag-pattern:
    ( 'w<fs-item-tag-flags>', word-list, 'tag-label' )
    ( 't<fs-item-tag-flags>', 'tag-text', 'tag-label' ) 
fs-item-tag-flags: {b                   |s|u}{n|t|g|l|d}
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
        self.date = date.today()        # used for DbFolder.date
        self.datetime = datetime.combine(self.date, time())
        self.fs_sources = []            # list of sources we created
        self.db_folders = {}            # folder-name => DbFolder
        self.fs_folders = {}            # (fs_source, folder-name) => FsFolder
        self.ie_folders = {}            # folder-name => IEFolder
        self.db_images = {}             # image-name => DbImage
        self.fs_images = {}             # image-name => FsImage

    def execute(self, cfg_op):
        dispatch = {
            '+tag':                 self.add_tag,
            '-tag':                 self.del_tag,
            '+db-folder':           self.add_db_folder,
            '!db-folder-tag':       self.mod_db_folder_tags,
            '?db-folder-tag':       self.check_db_folder_tags,
            '+mapping':             self.add_mapping,
            '-mapping':             self.del_mapping,
            '!fs-source':           self.set_fs_source,
            '+fs-folder':           self.add_fs_folder,
            'set-fs-folder-tags':   self.set_fs_folder_tags,
            'rebind-fs-folder-tags':self.rebind_fs_folder_tags,
            '?fs-folder-tag':       self.check_fs_folder_tags,
            'check-fs-folder-tags': self.check_fs_folder_tags,
            '!ie-folder':           self.set_ie_folder,
            '?ie-folder':           self.check_ie_folder
            #'+binding':             self.add_binding,
            #'-binding':             self.del_binding,
            #'-folder':              self.del_folder,
            #'!f-grouping':          self.set_folder_grouping,
            #'!i-grouping':          self.set_image_grouping
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
                    raise
        map_op_tree(cfg_op)

    def _sql_cleanup(self, obj_list):
        map(self.session.delete, obj_list)

    def cleanup(self):
        map(self._sql_cleanup, [
            self.fs_images.values(),
            self.db_images.values(),
            self.fs_sources,
            self.fs_folders.values(),
            self.db_folders.values(),
            self.mappings.values(),
            self.tags.values()
        ])
        if self.local_tag_source is not None:
            self.session.delete(self.local_tag_source)
        self.ie_folders = {}

    def add_tag(self, tag_spec):
        # unpack the tag-spec
        if type(tag_spec) is tuple:
            tag_label = tag_spec[0]
            tag_text = tag_spec[1]
        else:
            tag_label = tag_spec
            tag_text = tag_spec

        db_tag = db.DbTag.get_expr(self.session, tag_text)
        self.tags[tag_label] = db_tag
        return db_tag

    def _get_tag(self, tag_label):
        try:
            db_tag = self.tags[tag_label]
        except:
            db_tag = None
        return db_tag

    def del_tag(self, op):
        # unpack the tag-spec
        tag_label = tag_spec[0]

        db_tag = self.get_tag(tag_label)
        self.session.delete(db_tag)

    def add_db_folder(self, folder_name):
        db_folder = db.DbFolder.add(self.session, self.date, folder_name)
        self.db_folders[folder_name] = db_folder
        return db_folder

    def mod_db_folder_tags(self, folder_tag_spec):
        def mod_db_item_tags(item, item_tag_specs):
            for item_tag_spec in item_tag_specs:
                # unpack the db-image-item-tag-spec
                flags_spec = item_tag_spec[0]
                tag_label = item_tag_spec[1]

                db_tag = self._get_tag(tag_label)
                flags = [0, 0]  # [ add-flags, delete-flags ]
                idx = 0
                for f in flags_spec:
                    if f == '+':
                        idx = 0
                    elif f == '-':
                        idx = 1
                    elif f == 'd':
                        flags[idx] |= db.TagFlags.DIRECT
                    elif f == 'e':
                        flags[idx] |= db.TagFlags.EXTERNAL
                    elif f == 'b':
                        flags[idx] |= db.TagFlags.BLOCKED
                item.mod_tag_flags(self.session, db_tag, flags[0], flags[1])

        # unpack the db-folder-tag-spec
        folder_name = folder_tag_spec[0]
        folder_item_tag_specs = folder_tag_spec[1]
        image_tag_specs = [] if len(folder_tag_spec) < 3 else folder_tag_spec[2]

        folder = db.DbFolder.find(self.session, self.date, folder_name)
        assert folder is not None
        mod_db_item_tags(folder, folder_item_tag_specs)

        for image_tag_spec in image_tag_specs:
            # unpack the db-image-tag_spec
            image_name = image_tag_spec[0]
            image_item_tag_specs = image_tag_spec[1]

            image = db.DbImage.find(self.session, folder, image_name)
            assert image is not None
            mod_db_item_tags(image, image_item_tag_specs)

    def check_db_folder_tags(self, folder_tag_pattern):
        def check_db_item_tags(item, item_tag_patterns):
            for item_tag_pattern in item_tag_patterns:
                # unpack the db-item-tag-pattern
                flag_spec = item_tag_pattern[0]
                tag_label = item_tag_pattern[1]

                db_tag = self._get_tag(tag_label)
                item_tag = item.find_item_tag(self.session, db_tag)

                if flag_spec[0] == '0':
                    if item_tag is not None:
                        pass
                    assert item_tag is None
                else:
                    if item_tag is None:
                        pass
                    assert item_tag is not None
                    op = flag_spec[0]
                    flags = 0
                    for f in flag_spec[1:]:
                        flags |= {
                            'd':    db.TagFlags.DIRECT,
                            'e':    db.TagFlags.EXTERNAL,
                            'b':    db.TagFlags.BLOCKED
                        }[f]
                    if op == '=':
                        assert item_tag,flags == flags
                    elif op == '&':
                        assert (item_tag.flags & flags) == flags
                    elif op == '~':
                        assert (item_tag.flags) == 0

        # unpack the db-folder-tag-pattern
        folder_name = folder_tag_pattern[0]
        folder_item_tag_patterns = folder_tag_pattern[1]
        image_tag_patterns = (
            [] if len(folder_tag_pattern) < 3 else folder_tag_pattern[2])

        folder = db.DbFolder.find(self.session, self.date, folder_name)
        assert folder is not None
        check_db_item_tags(folder, folder_item_tag_patterns)

        for image_tag_pattern in image_tag_patterns:
            # unpack the db-image-tag_pattern
            image_name = image_tag_pattern[0]
            image_item_tag_patterns = image_tag_pattern[1]

            image = db.DbImage.find(self.session, folder, image_name)
            assert image is not None
            check_db_item_tags(image, image_item_tag_patterns)

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
        db_tag = None if tag_label is None else self._get_tag(tag_label)
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
        if type(source) is not db.FsSource:
            # unpack the fs-source-spec
            flags = source[0]
            volume = source[1]
            path = source[2]
            read_only = False
            source_type = db.FsSourceType.DIR
            for f in flags:
                if f == 'd':    source_type = db.FsSourceType.DIR
                elif f == 'f':  source_type = db.FsSourceType.FILE
                elif f == 'w':  source_type = db.FsSourceType.WEB
                elif f == 'r':  read_only = True

            source = db.FsSource.add(self.session,
                volume, path, source_type, read_only, self.local_tag_source)
            self.fs_sources.append(source)
        self.fs_source = source

    def _check_fs_item_tags(self, item, item_tag_specs):
        def find_item_tag(text):
            for item_tag in item.item_tags:
                if item_tag.text.lower() == text.lower():
                    return item_tag
            else:
                assert False

        def check_item_tag(self, item_tag):
            if item_tag.type != tag_type:
                pass
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
                    if item_tag.idx != item_tag0.idx + x:
                        pass
                    assert item_tag.idx == item_tag0.idx + x
                    if item_tag.first_idx != item_tag0.idx:
                        pass
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


    def add_fs_folder(self, folder_spec):
        # unpack the folder-spec
        folder_name = folder_spec[0]
        image_names = folder_spec[1]

        try:
            db_folder = self.db_folders[folder_name]
        except:
            db_folder = None
        fs_folder = db.FsFolder.add(
            self.session, self.fs_source, folder_name,
            self.date, folder_name, db_folder)

        for image_name in image_names:
            # TODO: db_image
            fs_image = db.FsImage.add(
                self.session, fs_folder, image_name, None)

        self.fs_folders[(self.fs_source, folder_name)] = fs_folder
        return fs_folder

    def set_ie_folder(self, folder_spec):
        def item_tag(spec, bases):
            # unpack the tag-spec
            flag = spec[0]
            text = spec[1]

            # unpack the flags
            tag_type = {
                'a':    ie_fs.IETagType.AUTO,
                'b':    ie_fs.IETagType.BASED,
                'u':    ie_fs.IETagType.UNBASED,
                'w':    ie_fs.IETagType.WORD,
                'n':    ie_fs.IETagType.NOTE
            }[flag[0]]

            # TODO: URL?
            return ie_fs.IETag(tag_type, text, bases)

        # unpack the folder-spec
        folder_name = folder_spec[0]
        folder_tag_bases = folder_spec[1]
        folder_tag_specs = folder_spec[2]
        if len(folder_spec) > 4:
            image_tag_bases = folder_spec[3]
            image_specs = folder_spec[4]
        else:
            image_tag_bases = ""
            image_specs = []

        folder = ie_fs.IEFolder(
            'test-path', self.date, folder_name, self.datetime)
        for folder_tag_spec in folder_tag_specs:
            folder.add_tag(item_tag(folder_tag_spec, folder_tag_bases))

        for image_spec in image_specs:
            # unpack the image-spec
            image_name = image_spec[0]
            image_tag_specs = image_spec[1]

            image = ie_fs.IEImage(folder, image_name)
            for image_tag_spec in image_tag_specs:
                image.add_tag(item_tag(image_tag_spec, image_tag_bases))
            folder.add_image(image)

        self.ie_folders[folder_name] = folder
        return folder

    def check_ie_folder(self, folder_spec):
        def check_item_tag(tag, spec, bases):
            # unpack the tag-spec
            flag = spec[0]
            text = spec[1]

            # unpack the flags
            tag_type = {
                'a':    ie_fs.IETagType.AUTO,
                'b':    ie_fs.IETagType.BASED,
                'u':    ie_fs.IETagType.UNBASED,
                'w':    ie_fs.IETagType.WORD,
                'n':    ie_fs.IETagType.NOTE
            }[flag[0]]

            # TODO: URL?
            if tag.type != tag_type:
                pass
            assert tag.type == tag_type
            if tag.bases !=  bases:
                pass
            assert tag.bases == bases
            if tag.text != text:
                pass
            assert tag.text == text

        # unpack the folder-spec
        folder_name = folder_spec[0]
        folder_tag_bases = folder_spec[1]
        folder_tag_specs = folder_spec[2]
        if len(folder_spec) > 4:
            image_tag_bases = folder_spec[3]
            image_specs = folder_spec[4]
        else:
            image_tag_bases = ""
            image_specs = []

        assert folder_name in self.ie_folders
        folder = self.ie_folders[folder_name]
        for folder_tag_spec, tag in zip(folder_tag_specs, folder.tags):
            check_item_tag(tag, folder_tag_spec, folder_tag_bases)

        for image_spec in image_specs:
            # unpack the image-spec
            image_name = image_spec[0]
            image_tag_specs = image_spec[1]

            assert image_name in folder.images
            image = folder.images[image_name]
            for image_tag_spec, tag in zip(image_tag_specs, image.tags):
                check_item_tag(tag, image_tag_spec, image_tag_bases)


    def set_fs_folder_tags(self, spec):
        # unpack the spec
        fs_folder_name = spec[0]
        ie_folder_name = spec[1]

        fs_folder = self.fs_folders[(self.fs_source, fs_folder_name)]
        ie_folder = self.ie_folders[ie_folder_name]
        fs_tag_source = self.local_tag_source # FIXME
        tags.set_fs_item_tags(self.session,
                              fs_folder, ie_folder.tags, fs_tag_source)

        for ie_image in ie_folder.images.values():
            ie_image_name = ie_image.name
            fs_image = db.FsImage.find(self.session, fs_folder, ie_image_name)
            assert fs_image is not None
            tags.set_fs_item_tags(self.session,
                                  fs_image, ie_image.tags, fs_tag_source)
            pass

        pass

    def rebind_fs_folder_tags(self, fs_folder_name):
        fs_folder = self.fs_folders[(self.fs_source, fs_folder_name)]
        fs_tag_source = self.local_tag_source
        tags.rebind_fs_item_tags(self.session, fs_folder, fs_tag_source)

        for fs_image in fs_folder.images:
            tags.rebind_fs_item_tags(self.session, fs_folder, fs_tag_source)
        pass
