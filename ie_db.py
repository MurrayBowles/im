""" import/export folders/images to/from the database """

import copy
from collections import deque
from typing import Union

import db
import ie_db
from fuksqa import fuksqa
import web_ie_db
from ie_cfg import *
from ie_fs import *
from tags import set_fs_item_tags
from wx_task import WxTask2


class IEWorkItem(object):

    def __init__(self, fs_folder, ie_folder,
        nest_lvl=0, parent=None, base_folder=None
    ):

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
        self.deleted_images = []
            # list of db.FsImages that have been deleted from the import source
        self.existing_images = []
            # list of existing (db.FsImage, IEImage, is_new)
        self.get_exif = set()
            # set of ie_images to get the exif data (e.g. tags) for
        self.get_thumbnail = set()
            # set of IeImages to get/update the thumbnail for

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
    """ return a list of IEWorkItems
        1) scan <paths> to obtain a list of IEFolders
        2) for each, check whether there's already an db.FsFolder
        an IEWorkItem is a fs_folder/ie_folder pair, where one item may be None
    """

    worklist = deque()
    if import_mode == ImportMode.SET:
        if fs_source.source_type == db.FsSourceType.DIR:
            ie_folders = scan_dir_set(
                paths[0], is_std_dirname, proc_std_dirname)
        elif fs_source.source_type == db.FsSourceType.FILE:
            ie_folders = scan_file_set(
                paths[0], lambda filename: True, proc_corbett_filename)
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
                    worklist.append(
                        IEWorkItem(fs_folders.pop(0), ie_folders.pop(0)))
                elif fs_rel_path < ie_rel_path:
                    worklist.append(
                        IEWorkItem(fs_folders.pop(0), None))
                else:
                    worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            elif len(fs_folders) != 0:
                # an existing FsFolder was not seen in this external scan
                worklist.append(IEWorkItem(fs_folders.pop(0), None))
            elif len(ie_folders) != 0:
                # a new folder has been found in the external scan
                worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            else:
                break
    return worklist


def create_fs_folder(session, ie_folder, fs_source):
    """ create an FsFolder, and maybe a DbFolder, for <ie_folder> """

    # create an FsFolder
    fs_folder = db.FsFolder.get(
        session, fs_source, fs_source.rel_path(ie_folder.fs_path))[0]

    # also create a DbFolder if ie_folder has a good db_name and date
    if (IEMsg.find(IEMsgType.NAME_NEEDS_EDIT, ie_folder.msgs) is None and
                IEMsg.find(IEMsgType.NO_DATE, ie_folder.msgs) is None):
        db_folder = db.DbFolder.get(
            session, ie_folder.db_date, ie_folder.db_name)[0]
        fs_folder.db_folder = db_folder
    return fs_folder


def _thumbnail_needs_update(fs_or_db_image: Union[db.FsImage, db.DbImage], thumbnail_timestamp):
    return (
        fs_or_db_image.thumbnail_timestamp is None
        or fs_or_db_image.thumbnail_timestamp < thumbnail_timestamp )


def _update_thumbnail(
    fs_or_db_image: Union[db.FsImage, db.DbImage], thumbnail, thumbnail_timestamp
):
    fs_or_db_image.thumbnail = thumbnail
    fs_or_db_image.thumbnail_timestamp = thumbnail_timestamp


def _set_db_image(fs_image: db.FsImage, db_image: db.DbImage):
    # should be a FsImage method, but Python can't deal with circular imports
    fs_image.db_image = db_image
    if db_image is not None and fs_image.thumbnail_timestamp is not None:
        if _thumbnail_needs_update(db_image, fs_image.thumbnail_timestamp):
            _update_thumbnail(db_image, fs_image.thumbnail, fs_image.thumbnail_timestamp)


def fg_start_ie_work_item(session, ie_cfg, work_item, fs_source):
    import_mode = ie_cfg.import_mode

    def queue_ie_image_import(fs_image, ie_image, new_fs_image):
        work_item.existing_images.append((fs_image, ie_image, new_fs_image))
        if db_folder is not None:
            db_image = db.DbImage.get(session, db_folder, ie_image.name)[0]
            if fs_image.db_image is None:
                fs_image.db_image = db_image
            fs_or_db_image = db_image
        else:
            fs_or_db_image = fs_image
        if ie_cfg.import_thumbnails:
            thumb_ie_image_inst = ie_image.newest_inst_with_thumbnail
            if thumb_ie_image_inst is not None:
                pass
            if (thumb_ie_image_inst is not None
            and _thumbnail_needs_update(fs_or_db_image, thumb_ie_image_inst.mod_datetime)):
                # add to the list of IEImages to get/update thumbnails for
                work_item.get_thumbnail.add(ie_image)
        if new_fs_image:
            if ie_cfg.import_image_tags:
                work_item.get_exif.add(ie_image)
        pass

    fs_folder = work_item.fs_folder
    ie_folder = work_item.ie_folder

    if fs_source.source_type == db.FsSourceType.FILE:
        # the files have already been scanned by scan_file_set/sel()
        pass
    elif fs_source.source_type == db.FsSourceType.DIR:
        # scan the folder's image files
        scan_std_dir_files(ie_folder)
    elif fs_source.source_type == db.FsSourceType.WEB:
        # all the work is done in the background thread
        return
    else:
        raise Exception('unexpected FsSourceType')


    if fs_folder is None:
        # create an FsFolder and maybe its DbFolder
        fs_folder = create_fs_folder(session, ie_folder, fs_source)
        work_item.fs_folder = fs_folder
    else:
        # there was already an FsFolder for this IEFolder
        pass
    db_folder = fs_folder.db_folder # this may be None

    if (import_mode == ImportMode.SEL
    and fs_source.source_type == db.FsSourceType.FILE):
        # find/create FsImages corresponding to each IEImage
        for ie_image in ie_folder.images.values():
            fs_image, new_fs_image = db.FsImage.get(
                session, fs_folder, ie_image.name)
            queue_ie_image_import(fs_image, ie_image, new_fs_image)
    else:
        # get sorted lists of all FsImages and IEImages for the folder
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
                    queue_ie_image_import(fs_image, ie_image, False)
                elif fs_image.name < ie_image.name:
                    work_item.deleted_images.append(fs_image)
                else: # ie_image.db_name < fs_image.db_name
                    fs_image = db.FsImage.add(session, fs_folder, ie_image.name)
                    queue_ie_image_import(fs_image, ie_image, True)
            elif len(fs_images) != 0:
                work_item.deleted_images.extend(fs_images)
                break
            elif len(ie_images) != 0:
                ie_image = ie_images.pop(0)
                fs_image = db.FsImage.add(session, fs_folder, ie_image.name)
                queue_ie_image_import(fs_image, ie_image, True)
            else:
                break

def bg_proc_ie_work_item(work_item, fs_source, pub_fn):
    """ WEB: scan the work item's web page
        FILE or DIR: get thumbnails or exifs for the work item
        this is run in a background thread and may not touch the database
    """
    try:
        if fs_source.source_type == db.FsSourceType.WEB:
            if work_item.ie_folder is not None:
                pub_fn('ie.sts.import webpage', data=1)
                web_ie_db.scan_web_page_children(
                    work_item.ie_folder, work_item.base_folder,
                    work_item.child_paths)
                pub_fn('ie.sts.imported webpage', data=1)
        else:  # FILE or DIR
            if len(work_item.get_thumbnail) > 0:
                pub_fn(
                    'ie.sts.import thumbnails', data=len(work_item.get_thumbnail))
                get_ie_image_thumbnails(work_item.get_thumbnail, pub_fn)
                pass
            if len(work_item.get_exif) > 0:
                pub_fn(
                    'ie.sts.import tags', data=len(work_item.get_exif))
                get_ie_image_exifs(work_item.get_exif, pub_fn)
                pass
    except Exception as exc_data:
        pass

def fg_finish_ie_work_item(session, ie_cfg, work_item, fs_source, worklist):
    """ do auto-tagging, move thumbnails to db.DbImage """

    if fs_source.source_type == db.FsSourceType.WEB:
        # create FsFolders and FsImages for the IEFolders/Images scanned
        # (for the WEB or FILE case this was done in fg_start_ie_work_item)
        try:
            assert work_item.fs_folder is None
            ie_folder = work_item.ie_folder
            fs_folder = create_fs_folder(session, ie_folder, fs_source)
            work_item.fs_folder = fs_folder
            db_folder = fs_folder.db_folder
            for ie_image in ie_folder.images.values():
                fs_image, new_fs_image = db.FsImage.get(
                    session, fs_folder, ie_image.name)
                work_item.existing_images.append((fs_image, ie_image))
                if db_folder is not None:
                    db_image = db.DbImage.get(session, db_folder, ie_image.name)[0]
                    if fs_image.db_image is None:
                        fs_image.db_image = db_image
        except Exception as ed:
            print('hey')

    # create FsItemTags from any imported tags, and set Db/FsImage thumbnails
    try:
        set_fs_item_tags(session,
            work_item.fs_folder, work_item.ie_folder.tags, fs_source.tag_source)

        for image in work_item.existing_images:
            fs_image = image[0]
            ie_image = image[1]

            set_fs_item_tags(session, fs_image, ie_image.tags, fs_source.tag_source)
            if ie_cfg.import_thumbnails:
                fs_or_db_image = fs_image.db_image if fs_image.db_image is not None else fs_image
                thumb_ie_image_inst = ie_image.newest_inst_with_thumbnail
                if (thumb_ie_image_inst is not None
                and _thumbnail_needs_update(fs_or_db_image, thumb_ie_image_inst.mod_datetime)):
                    _update_thumbnail(
                        fs_or_db_image,
                        ie_image.thumbnail,
                        thumb_ie_image_inst.mod_datetime)
    except Exception as ed:
        print('hey')

    # for the WEB case, queue processing for child pages
    try:
        for child_path in work_item.child_paths:
            child_work_item = get_web_ie_work_item(
                session, fs_source, child_path, work_item)
            worklist.append(child_work_item)
    except Exception as ed:
        print ('hey')

    session.commit()
    pass


class IETask2(WxTask2):
    """ an import/export command """

    def __init__(self, **kw):
        super().__init__(**kw)

        self.session = kw['session']
        self.session.flush() # FUKSQA
        self.ie_cfg = copy.deepcopy(kw['ie_cfg'])
        self.ie_cfg.source = kw['fs_source']
        self.ie_cfg.import_mode = kw['import_mode']
        self.ie_cfg.paths = kw['paths'] # does this need to be a copy?

        self.fs_source = self.ie_cfg.source
        self.worklist = get_ie_worklist(
            self.session,
            self.fs_source, self.ie_cfg.import_mode, self.ie_cfg.paths)
        self.worklist_idx = 0

    def run(self):
        self.pub('ie.sts.begun', data=self.worklist)
        while not self.cancelled() and self.worklist_idx < len(self.worklist):
            work_item = self.worklist[self.worklist_idx]
            try:
                fg_start_ie_work_item(
                    self.session, self.ie_cfg, work_item, self.fs_source)
            except Exception as ed:
                print('hey')

            if (len(work_item.get_exif) > 0 or
                len(work_item.get_thumbnail) > 0 or
                self.fs_source.source_type == db.FsSourceType.WEB
            ):
                try:
                    yield (lambda: bg_proc_ie_work_item(
                        work_item, self.fs_source, self.pub))
                except Exception as ed:
                    print('hey')
                pass
            else:
                yield

            try:
                fg_finish_ie_work_item(
                    self.session, self.ie_cfg, work_item, self.fs_source,
                    self.worklist)
            except Exception as ed:
                print('hey')

            self.pub('ie.sts.folder done',
                data=self.worklist[self.worklist_idx].ie_folder.db_name)
            self.worklist_idx += 1
            yield
        self.pub('ie.sts.done', data=True)
