''' import/export folders/images to/from the database '''

from collections import deque
import copy

import db
from ie_cfg import *
from ie_fs import *
from task import Task
import web_ie_db


class IEWorkItem(object):

    def __init__(self, fs_folder, ie_folder, nest_lvl=0, parent=None, base_folder=None):

        self.fs_folder = fs_folder
        self.ie_folder = ie_folder
        self.msgs = []                  # list() # of IEMsg

        # used by web_ie_db.scan_web_page (db.FsSourceType.WEB)
        self.child_paths = []
        self.nest_lvl = nest_lvl        # gallery-page nesting level
        self.parent = parent            # nonnull when nest_lvl > 0
        self.base_folder = base_folder  # nonnull when nest_lvl > 1
            # None  when processing murraybowles
            # None  when processing murraybowles/shows
            # shows when processing murrayboelse/shows/xxx...

        # set by fs_start_work_item()
        self.deleted_images = []    # list of db.FsImages that have been deleted from the import source
        self.existing_images = []   # list of existing (db.FsImage, IEImage, is_new)
        self.get_exif = set()       # set of ie_images to get the exif data (e.g. tags) for
        self.get_thumbnail = set()  # set of IeImages to get/update the thumbnail for

    def __repr__(self):
        return '<WorkItem %s %s>' % (
            str(self.fs_folder) if self.fs_folder is not None else 'NoFS',
            str(self.ie_folder) if self.ie_folder is not None else 'NoIE'
        )

def get_web_ie_work_item(session, fs_source, path, parent):
    child_paths = []

    page_name = util.last_url_component(path)
    match = leading_date_underscore.match(page_name)
    if match is None:
        db_date = None
        db_name = page_name
    else:
        yymmdd = match.group()[0:-1]
        try:
            db_date = util.date_from_yymmdd(yymmdd)
        except:
            pass
        db_name = page_name[match.end():].lstrip('_')
    db_name = db_name.replace('_', ' ')
    mtime =  datetime.datetime.now() # updated by scan_web_page
    ie_folder = IEFolder(path, db_date, db_name, mtime)
    if db_date == None:
        ie_folder.msgs.append(IEMsg(IEMsgType.NO_DATE, path))

    fs_folder = db.FsFolder.find(
        session, fs_source, fs_source.rel_path(ie_folder.fs_path))

    nest_lvl = 0 if parent is None else parent.nest_lvl + 1
    if nest_lvl < 2:
        base_folder = None
    elif nest_lvl == 2:
        base_folder = parent.ie_folder.db_name
    else:
        base_folder = parent.base_folder
    work_item = IEWorkItem(fs_folder, ie_folder, nest_lvl, parent, base_folder)
    return work_item

def get_ie_worklist(session, fs_source, import_mode, paths):
    ''' return a list of IEWorkItems
        1) scan <paths> to obtain a list of IEFolders
        2) for each, check whether there's already an db.FsFolder
        an IEWorkItem is a fs_folder/ie_folder pair, where one item may be None
    '''

    worklist = deque()
    if import_mode == ImportMode.SET:
        if fs_source.source_type == db.FsSourceType.DIR:
            ie_folders = scan_dir_set(paths[0], is_std_dirname, proc_std_dirname)
        elif fs_source.source_type == db.FsSourceType.FILE:
            ie_folders = scan_file_set(paths[0], lambda filename: True, proc_corbett_filename)
        else:
            assert fs_source.source_type == db.FsSourceType.WEB
            return [
                get_web_ie_work_item(session, fs_source, paths[0], parent=None)]

    else: # ImportMode.SEL
        if fs_source.source_type == db.FsSourceType.DIR:
            ie_folders = scan_dir_sel(paths, proc_std_dirname)
        else: # db.FsSourceType.FILE
            assert fs_source.source_type == db.FsSourceType.FILE
            ie_folders = scan_file_sel(paths, proc_corbett_filename)


    if import_mode == ImportMode.SEL:
        # get all db.FsFolders that match folders
        for ie_folder in ie_folders:
            fs_folder = db.FsFolder.find(
                session, fs_source, fs_source.rel_path(ie_folder.fs_path))
            worklist.append(IEWorkItem(fs_folder, ie_folder))
    else:                           # DIR_SET or FILE_SET
        # get all db.FsFolders in the FsSource
        fs_folders = fs_source.folders
        # merge fs_folders with ie_folders
        while True:
            if len(fs_folders) != 0 and len(ie_folders) != 0:
                # we're updating a known db.FsFolder
                fs_rel_path = fs_folders[0].name
                ie_rel_path = fs_source.rel_path(ie_folders[0].fs_path)
                if fs_rel_path == ie_rel_path:
                    worklist.append(IEWorkItem(fs_folders.pop(0), ie_folders.pop(0)))
                elif fs_rel_path < ie_rel_path:
                    worklist.append(IEWorkItem(fs_folders.pop(0), None))
                else:
                    worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            elif len(fs_folders) != 0:
                # an db.FsFolder in the database was not seen in this filesystem scan
                worklist.append(IEWorkItem(fs_folders.pop(0), None))
            elif len(ie_folders) != 0:
                # a folder has been found in the filesystem which is not in the db.FsFolder database
                worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            else:
                break
    return worklist

def create_fs_folder(session, ie_folder, fs_source):
    ''' create an FsFolder, and maybe a DbFolder, for <ie_folder> '''
    # create an FsFolder
    fs_folder = db.FsFolder.get(
        session, fs_source, fs_source.rel_path(ie_folder.fs_path))[0]
    # also auto-create a DbFolder if ie_folder has a good name and date
    if (IEMsg.find(IEMsgType.NAME_NEEDS_EDIT, ie_folder.msgs) is None and
                IEMsg.find(IEMsgType.NO_DATE, ie_folder.msgs) is None):
        db_folder = db.DbFolder.get(session, ie_folder.db_date, ie_folder.db_name)[0]
        fs_folder.db_folder = db_folder
    return fs_folder

def fg_start_ie_work_item(session, ie_cfg, work_item, fs_source):
    import_mode = ie_cfg.import_mode

    def import_ie_image(fs_image, ie_image, new_fs_image):
        work_item.existing_images.append((fs_image, ie_image, new_fs_image))
        if db_folder is not None:
            db_image = db.DbImage.get(session, db_folder, ie_image.name)[0]
            if fs_image.db_image is None:
                fs_image.db_image = db_image
            if ie_cfg.import_thumbnails and ie_image.newest_inst_with_thumbnail is not None:
                pass
            if ie_cfg.import_thumbnails and ie_image.newest_inst_with_thumbnail is not None and (
                            db_image.thumbnail is None or
                            ie_image.latest_inst_with_timestamp.mod_datetime > db_image.thumbnail_timestamp):
                # add to the list of IEImages to get/update thumbnails for
                work_item.get_thumbnail.add(ie_image)
        if new_fs_image:
            if ie_cfg.import_image_tags:
                work_item.get_exif.add(ie_image)
        pass

    fs_folder = work_item.fs_folder
    ie_folder = work_item.ie_folder

    if fs_source.source_type == db.FsSourceType.DIR:
        # scan the folder's image files
        # (this has already been done in the db.FsSourceType.FILE case by scan_file_set/sel)
        scan_std_dir_files(ie_folder)
    elif fs_source.source_type == db.FsSourceType.WEB:
        # all the work is done inn the background thread
        return

    if fs_folder is None:
        # create an FsFolder and maybe its DbFolder
        fs_folder = create_fs_folder(session, ie_folder, fs_source)
        work_item.fs_folder = fs_folder
    db_folder = fs_folder.db_folder # this may be None

    if import_mode == ImportMode.SEL and fs_source.source_type == db.FsSourceType.FILE:
        # find/create FsImages corresponding to each IeImage
        for ie_image in ie_folder.images.values():
            fs_image, new_fs_image = db.FsImage.get(session, fs_folder, ie_image.name)
            import_ie_image(fs_image, ie_image, new_fs_image)
    else:
        # get sorted lists of all db.FsImages and IEImages currently known for the folder
        fs_images = list(fs_folder.images)
        ie_images = list(work_item.ie_folder.images.values())
        fs_images.sort(key=lambda x: x.name)
        ie_images.sort(key=lambda x: x.name)
        # merge the lists, noting additions and deletions
        while True:
            if len(fs_images) != 0 and len(ie_images) != 0:
                fs_image = fs_images.pop(0)
                ie_image = ie_images.pop(0)
                if fs_image.name == ie_image.name:
                    import_ie_image(fs_image, ie_image, False)
                elif fs_image.name < ie_image.name:
                    work_item.deleted_images.append(fs_image)
                else: # ie_image.name < fs_image.name
                    fs_image = db.FsImage.add(session, fs_folder, ie_image.name)
                    import_ie_image(fs_image, ie_image, True)
            elif len(fs_images) != 0:
                work_item.deleted_images.extend(fs_images)
                break
            elif len(ie_images) != 0:
                ie_image = ie_images.pop(0)
                fs_image = db.FsImage.add(session, fs_folder, ie_image.name)
                import_ie_image(fs_image, ie_image, True)
            else:
                break

def find_text_binding(session, type, text, fs_tag_source):
    ''' return [text, FsTagBinding, FsItemTagSource, DbTag id] '''
    mapping = db.FsTagMapping.find(session, fs_tag_source, type, text)
    if mapping is not None:
        # <text> is mapped in <fs_tag_source>
        return [text, mapping.binding, db.FsItemTagSource.FSTS, mapping.db_tag]
    mapping = db.FsTagMapping.find(session, db.global_tag_source, type, text)
    if mapping is not None:
        # <text> is mapped in <global_tag_source>
        return [text, mapping.binding, db.FsItemTagSource.GLOBTS, mapping.db_tag]
    db_tag = db.DbTag.find_expr(session, text)
    if db_tag is not None:
        # <text> occurs in the DbTag database
        return [text, db.FsTagBinding.BOUND, db.FsItemTagSource.DBTAG, db_tag]
    return [text, db.FsTagBinding.UNBOUND, db.FsItemTagSource.NONE, None]

def find_ie_tag_binding(session, ie_tag, text, fs_tag_source):
    ''' return [text, FsTagBinding, FsItemTagSource, DbTag id] '''
    type = db.FsTagType.WORD if ie_tag.type == IETagType.WORD else db.FsTagType.TAG
    if text.find('|') == -1 and ie_tag.bases is not None:
        # try both <text> and <base>|<text> for each base in ie_tag.bases
        bases = ie_tag.bases.split(',')
        results = []
        for base in bases:
            base = base.strip()
            t = base + '|' + text
            results.append(find_text_binding(session, type, t, fs_tag_source))

        flat_result = find_text_binding(session, type, text, fs_tag_source)
        if flat_result[1].has_db_tag() and flat_result[3].parent is not None:
            # DbTag parent is not one of the proposed bases:
            # demote from BOUND to SUGGESTED
            if flat_result[1] == db.FsTagBinding.BOUND:
                flat_result[1] = db.FsTagBinding.SUGGESTED
        results.append(flat_result)

        flat_tag_matches = db.DbTag.find_flat(session, text)
        for flat_tag_match in flat_tag_matches:
            binding = [
                text, db.FsTagBinding.SUGGESTED, db.FsItemTagSource.DBTAG, flat_tag_match]
            results.append(binding)

        results.sort(key = lambda x: x[1], reverse=True)
        result = results[0]
    else:
        result = find_text_binding(session, type, text, fs_tag_source)
    return result

def add_word_fs_item_tags(session, item, base_idx, words, fs_tag_source):
    ''' add db.FsItemTags to <item>.tags[<base_idx>...], of type WORD '''
    def partition_words(pfx, words, partitions):
        partitions.append(pfx + [words])
        if len(words) > 1:
            for x in range(1, len(words)):
                partition_words(pfx + [words[0:x]], words[x:], partitions)
    partitions = []
    partition_words([], words, partitions)
    results = []
    for partition in partitions:
        bindings = []
        total_score = 1
        have_unbound_multiword = False
        for ie_elt_list in partition:
            text = ''
            sep = ''
            for ie_elt in ie_elt_list:
                text += sep + ie_elt.text
                sep = ' '
            binding = find_ie_tag_binding(
                session, ie_elt_list[0], text, fs_tag_source)
            if binding[1] == db.FsTagBinding.UNBOUND and len(ie_elt_list) > 1:
                have_unbound_multiword = True
            bindings.append(binding)
            total_score += binding[1].value # UNBOUND | SUGGESTED | BOUND
        if have_unbound_multiword:
            # don't consider a partition that has unbound multi-word elements
            total_score = 0
        results.append((total_score / len(partition), partition, bindings))
    results.sort(key = lambda x: x[0], reverse=True) # sort by the score
    result = results[0]
    idx = 0
    for ie_tag_list, binding in zip(result[1], result[2]):
        elt_base_idx = idx
        for ie_tag in ie_tag_list:
            item_tag = db.FsItemTag.add(session,
                item, base_idx + idx, base_idx + elt_base_idx,
                type=db.FsTagType.WORD, text=ie_tag.text, bases=words[0].bases,
                binding=binding[1], source=binding[2], db_tag=binding[3])
            idx += 1
    pass

def add_tag_fs_item_tag(session, item, idx, ie_tag, fs_tag_source):
    ''' add a db.FsItemTag to <item>.tags[<idx>], of type TAG '''
    binding = find_ie_tag_binding(session, ie_tag, ie_tag.text, fs_tag_source)
    item_tag = db.FsItemTag.add(session,
        item, idx, idx,
        type=db.FsTagType.TAG, text=ie_tag.text, bases=ie_tag.bases,
        binding=binding[1], source=binding[2], db_tag=binding[3])
    pass

def add_fs_item_note(session, item, ie_tag):
    ''' add a Note to <item> '''
    pass

def init_fs_item_tags(session, item, ie_tags, fs_tag_source):
    idx = 0
    ie_tag_iter = iter(ie_tags)
    # FIXME: what a mess! this would be easier to code in C
    try:
        ie_tag = next(ie_tag_iter)
        while True:
            if ie_tag.type in {IETagType.AUTO, IETagType.BASED, IETagType.UNBASED}:
                add_tag_fs_item_tag(session, item, idx, ie_tag, fs_tag_source)
                idx += 1
                ie_tag = next(ie_tag_iter)
            elif ie_tag.type == IETagType.WORD:
                words = [ie_tag]
                base_idx = idx
                done = False
                while True:
                    try:
                        idx += 1
                        ie_tag = next(ie_tag_iter)
                        if ie_tag.type != IETagType.WORD:
                            break
                        words.append(ie_tag)
                    except StopIteration:
                        done = True
                        break
                add_word_fs_item_tags(session, item, base_idx, words, fs_tag_source)
                if done:
                    break
            else:
                assert ie_tag.type == IETagType.NOTE
                add_fs_item_note(session, item, ie_tag)
                ie_tag = next(ie_tag_iter)
    except StopIteration:
        pass

def fg_finish_ie_work_item(session, ie_cfg, work_item, fs_source, worklist):
    ''' do auto-tagging, move thumbnails to db.DbImage '''

    if fs_source.source_type == db.FsSourceType.WEB:
        # create FsFolders and FsImages for the IEFolders/Images scanned
        # (for the file-system case, this is done BEFORE scanning)
        assert work_item.fs_folder is None
        ie_folder = work_item.ie_folder
        fs_folder = create_fs_folder(session, ie_folder, fs_source)
        work_item.fs_folder = fs_folder
        db_folder = fs_folder.db_folder
        for ie_image in ie_folder.images.values():
            fs_image, new_fs_image = db.FsImage.get(session, fs_folder, ie_image.name)
            work_item.existing_images.append((fs_image, ie_image))
            if db_folder is not None:
                db_image = db.DbImage.get(session, db_folder, ie_image.name)[0]
                if fs_image.db_image is None:
                    fs_image.db_image = db_image

    if True: # TODO work_item.fs_folder.db_folder is not None:
        # create FsItemTags from any imported tags
        init_fs_item_tags(session,
            work_item.fs_folder, work_item.ie_folder.tags, fs_source.tag_source)
        for image in work_item.existing_images:
            init_fs_item_tags(session, image[0], image[1].tags, fs_source.tag_source)
            pass

    # for the WEB case, queue processing for child pages
    for child_path in work_item.child_paths:
        child_work_item = get_web_ie_work_item(
            session, fs_source, child_path, work_item)
        worklist.append(child_work_item)

    session.commit()
    pass

def bg_proc_ie_work_item(work_item, fs_source, pub_fn):
    ''' get thumbnails or exifs for a work item
        do all the processing for a web page
        run in a background thread
    '''
    if fs_source.source_type == db.FsSourceType.WEB:
        if work_item.ie_folder is not None:
            pub_fn('ie.sts.import webpage', 1)
            web_ie_db.scan_web_page_children(
                work_item.ie_folder, work_item.base_folder, work_item.child_paths)
            pub_fn('ie.sts.imported webpage', 1)
    else:
        if len(work_item.get_thumbnail) > 0:
            pub_fn('ie.sts.import thumbnails', len(work_item.get_thumbnail))
            get_ie_image_thumbnails(work_item.get_thumbnail, pub_fn)
        if len(work_item.get_exif) > 0:
            pub_fn('ie.sts.import tags', len(work_item.get_exif))
            get_ie_image_exifs(work_item.get_exif, pub_fn)

class IETask(Task):
    ''' an import/export command '''

    def __init__(self, session, ie_cfg, fs_source, import_mode, paths):
        super().__init__()

        self.session = session
        self.ie_cfg = copy.deepcopy(ie_cfg)
        self.ie_cfg.source = fs_source
        self.ie_cfg.import_mode = import_mode
        self.ie_cfg.paths = paths # copy?
        self.fs_source = fs_source
        self.worklist = get_ie_worklist(session, fs_source, import_mode, paths)
        self.worklist_idx = 0
        self.pub('ie.sts.begun', self.worklist)
        self.queue(self.start_item)

    def start_item(self, data):
        ''' preprocess the work item, gathering image files in some cases,
            then spawn a background process if thumbnails or EXIFs need to be read
            called by the main thread when it receives ie.cmd.start item
        '''

        if self.cancelled() or self.worklist_idx >= len(self.worklist):
            self.pub('ie.sts.done', True)
        else:
            work_item = self.worklist[self.worklist_idx]

            fg_start_ie_work_item(self.session, self.ie_cfg, work_item, self.fs_source)

            if (len(work_item.get_exif) > 0 or
                len(work_item.get_thumbnail) > 0 or
                self.fs_source.source_type == db.FsSourceType.WEB):
                self.spawn(self.bg_proc)
            else:
                self.queue(self.finish_item)

    def bg_proc(self, data):
        ''' extract the exifs and/or thumbnails for a folder
            or do all the extraction for a web page
            run in the background thread created by bg_spawn
        '''
        work_item = self.worklist[self.worklist_idx]
        bg_proc_ie_work_item(work_item, self.fs_source, self.pub)
        self.queue(self.finish_item)

    def finish_item(self, data):
        ''' post-process the work item, autotagging the folder and its images
            where possible, then report completion of the folder to the GUI
           called by the main thread when it receives ie.cmd.start item
        '''
        if self.worklist_idx >= len(self.worklist):
            self.pub('ie.sts.done', True)
            return

        work_item = self.worklist[self.worklist_idx]
        fg_finish_ie_work_item(
            self.session, self.ie_cfg, work_item, self.fs_source, self.worklist)

        self.pub('ie.sts.folder done', self.worklist[self.worklist_idx].ie_folder.db_name)
        self.worklist_idx += 1
        self.queue(self.start_item)



