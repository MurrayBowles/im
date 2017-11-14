''' import/export folders/images to/from the database '''

from collections import deque
from db import DbFolder, DbImage, FsFolder, FsImage, FsSourceType
from ie_cfg import *
from ie_fs import *
from threading import Thread
import web_ie_db


class IEWorkItem(object):

    def __init__(self, fs_folder, ie_folder):

        self.fs_folder = fs_folder
        self.ie_folder = ie_folder
        self.msgs = []  # list() # of IENote

        # set by web_ie_db.scan_web_page (FsSourceType.WEB)
        self.child_paths = []

        # set by fs_start_work_item()
        self.deleted_images = []    # list of FsImages that have been deleted from the import source
        self.existing_images = []   # list of existing (FsImage, IEImage, is_new)
        self.get_exif = set()       # set of ie_images to get the exif data (e.g. tags) for
        self.get_thumbnail = set()  # set of IeImages to get/update the thumbnail for

    def __repr__(self):
        return '<WorkItem %s %s>' % (
            str(self.fs_folder) if self.fs_folder is not None else 'NoFS',
            str(self.ie_folder) if self.ie_folder is not None else 'NoIE'
        )

def get_web_ie_work_item(session, fs_source, path, top_level):
    child_paths = []

    page_name = util.last_url_component(path)
    match = leading_date_space.match(page_name)
    if match is None:
        db_date = None
        db_name = page_name
    else:
        yymmdd = match.group()
        db_date = util.date_from_yymmdd(yymmdd)
        db_name = page_name[match.end():].lstrip('_')
    db_name = db_name.replace('_', ' ')
    mtime =  datetime.datetime.now() # updated by scan_web_page
    ie_folder = IEFolder(path, db_date, db_name, mtime)
    if db_date == None:
        ie_folder.msgs.append(IEMsg(IEMsgType.NO_DATE, path))

    fs_folder = FsFolder.find(
        session, fs_source, fs_source.rel_path(ie_folder.fs_path))
    work_item = IEWorkItem(fs_folder, ie_folder)
    work_item.top_level = top_level
    return work_item

def get_ie_worklist(session, fs_source, import_mode, paths):
    ''' return a list of IEWorkItems
        1) scan <paths> to obtain a list of IEFolders
        2) for each, check whether there's already an FsFolder
        an IEWorkItem is a fs_folder/ie_folder pair, where one item may be None
    '''

    worklist = deque()
    if import_mode == ImportMode.SET:
        if fs_source.source_type == FsSourceType.DIR:
            ie_folders = scan_dir_set(paths[0], is_std_dirname, proc_std_dirname)
        elif fs_source.source_type == FsSourceType.FILE:
            ie_folders = scan_file_set(paths[0], lambda filename: True, proc_corbett_filename)
        else:
            assert fs_source.source_type == FsSourceType.WEB
            return [get_web_ie_work_item(session, fs_source, paths[0], top_level=True)]

    else: # ImportMode.SEL
        if fs_source.source_type == FsSourceType.DIR:
            ie_folders = scan_dir_sel(paths, proc_std_dirname)
        else: # FsSourceType.FILE
            assert fs_source.source_type == FsSourceType.FILE
            ie_folders = scan_file_sel(paths, proc_corbett_filename)


    if import_mode == ImportMode.SEL:
        # get all FsFolders that match folders
        for ie_folder in ie_folders:
            fs_folder = FsFolder.find(
                session, fs_source, fs_source.rel_path(ie_folder.fs_path))
            worklist.append(IEWorkItem(fs_folder, ie_folder))
    else:                           # DIR_SET or FILE_SET
        # get all FsFolders in the FsSource
        fs_folders = fs_source.folders
        # merge fs_folders with ie_folders
        while True:
            if len(fs_folders) != 0 and len(ie_folders) != 0:
                # we're updating a known FsFolder
                fs_rel_path = fs_folders[0].name
                ie_rel_path = fs_source.rel_path(ie_folders[0].fs_path)
                if fs_rel_path == ie_rel_path:
                    worklist.append(IEWorkItem(fs_folders.pop(0), ie_folders.pop(0)))
                elif fs_rel_path < ie_rel_path:
                    worklist.append(IEWorkItem(fs_folders.pop(0), None))
                else:
                    worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            elif len(fs_folders) != 0:
                # an FsFolder in the database was not seen in this filesystem scan
                worklist.append(IEWorkItem(fs_folders.pop(0), None))
            elif len(ie_folders) != 0:
                # a folder has been found in the filesystem which is not in the FsFolder database
                worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            else:
                break
    return worklist

def fg_start_ie_work_item(session, ie_cfg, work_item, fs_source):
    import_mode = ie_cfg.import_mode

    def import_ie_image(fs_image, ie_image, new_fs_image):
        work_item.existing_images.append((fs_image, ie_image, new_fs_image))
        if db_folder is not None:
            db_image = DbImage.get(session, db_folder, ie_image.name)[0]
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

    if fs_source.source_type == FsSourceType.DIR:
        # scan the folder's image files
        # (this has already been done in the FsSourceType.FILE case by scan_file_set/sel)
        scan_std_dir_files(ie_folder)
    elif fs_source.source_type == FsSourceType.WEB:
        # all the work is done inn the background thread
        return

    if fs_folder is None:
        # create an FsFolder
        fs_folder = FsFolder.get(session, fs_source, fs_source.rel_path(ie_folder.fs_path))[0]
        work_item.fs_folder = fs_folder
        # also auto-create a DbFolder if ie_folder has a good name and date
        if (IEMsg.find(IEMsgType.NAME_NEEDS_EDIT, ie_folder.msgs) is None and
                    IEMsg.find(IEMsgType.NO_DATE, ie_folder.msgs) is None):
            db_folder = DbFolder.get(session, ie_folder.db_date, ie_folder.db_name)[0]
            fs_folder.db_folder = db_folder
    db_folder = fs_folder.db_folder # this may be None
    if import_mode == ImportMode.SEL and fs_source.source_type == FsSourceType.FILE:
        # find/create FsImages corresponding to each IeImage
        for ie_image in work_item.ie_folder.images.values():
            fs_image, new_fs_image = FsImage.get(session, fs_folder, ie_image.name)
            import_ie_image(fs_image, ie_image, new_fs_image)
    else:
        # get sorted lists of all FsImages and IEImages currently known for the folder
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
                    fs_image = FsImage.add(session, fs_folder, ie_image.name)
                    import_ie_image(fs_image, ie_image, True)
            elif len(fs_images) != 0:
                work_item.deleted_images.extend(fs_images)
                break
            elif len(ie_images) != 0:
                ie_image = ie_images.pop(0)
                fs_image = FsImage.add(session, fs_folder, ie_image.name)
                import_ie_image(fs_image, ie_image, True)
            else:
                break

def fg_finish_ie_work_item(session, ie_cfg, work_item, fs_source, worklist):
    ''' do auto-tagging, move thumbnails to DbImage '''

    # for the WEB case, queue processing for child pages
    for child_path in work_item.child_paths:
        # FIXME: this be inside fg_finish_workitem
        child_work_item = get_web_ie_work_item(
            session, fs_source, child_path, top_level=False)
        worklist.append(child_work_item)
    pass

def bg_proc_ie_work_item(work_item, fs_source, pub_fn):
    ''' get thumbnails or exifs for a work item
        do all the processing for a web page
        run in a background thread
    '''
    if fs_source.source_type == FsSourceType.WEB:
        if work_item.ie_folder is not None:
            pub_fn('ie.sts.import webpage', 1)
            web_ie_db.scan_web_page_children(
                work_item.ie_folder, work_item.child_paths, work_item.top_level)
            pub_fn('ie.sts.imported webpage', 1)
    else:
        if len(work_item.get_thumbnail) > 0:
            pub_fn('ie.sts.import thumbnails', len(work_item.get_thumbnail))
            get_ie_image_thumbnails(work_item.get_thumbnail, pub_fn)
        if len(work_item.get_exif) > 0:
            pub_fn('ie.sts.import tags', len(work_item.get_exif))
            get_ie_image_exifs(work_item.get_exif, pub_fn)

class IECmd:
    ''' state of an import/export command '''

    def __init__(self, session, ie_cfg, fs_source):
        self.session = session
        self.ie_cfg = ie_cfg
        self.fs_source = fs_source
        self.worklist = get_ie_worklist(
            session, fs_source, ie_cfg.import_mode, ie_cfg.paths)
        self.worklist_idx = 0
        self.cancelling = False
        self.do_pub('ie.sts.begun', self.worklist)
        self.do_pub('ie.cmd.start item')

    def do_pub(self, msg, data=None):
        ''' do a pubsub.pub in the main thread
            must be overridden
        '''
        pass

    def bg_spawn(self):
        ''' start a background thread, executing self.bg_proc()
            must be overridden
        '''
        raise NotImplementedError('bg_spawn')

    def start_item(self):
        ''' preprocess the work item, gathering image files in some cases,
            then spawn a background process if thumbnails or EXIFs need to be read
            called by the main thread when it receives ie.cmd.start item
        '''
        if self.cancelling or self.worklist_idx >= len(self.worklist):
            self.do_pub('ie.sts.done', self.cancelling)
        else:
            work_item = self.worklist[self.worklist_idx]

            fg_start_ie_work_item(self.session, self.ie_cfg, work_item, self.fs_source)

            if (len(work_item.get_exif) > 0 or
                len(work_item.get_thumbnail) > 0 or
                self.fs_source.source_type == FsSourceType.WEB):
                self.bg_spawn()
            else:
                self.do_pub('ie.cmd.finish item')

    def bg_proc(self):
        ''' extract the exifs and/or thumbnails for a folder
            or do all the extraction for a web page
            run in the background thread created by bg_spawn
        '''
        def pub_fn(msg, data):
            self.do_pub(msg, data)
        work_item = self.worklist[self.worklist_idx]

        bg_proc_ie_work_item(work_item, self.fs_source, pub_fn)

        self.do_pub('ie.cmd.finish item')

    def finish_item(self):
        ''' post-process the work item, autotagging the folder and its images
            where possible, then report completion of the folder to the GUI
           called by the main thread when it receives ie.cmd.start item
        '''
        work_item = self.worklist[self.worklist_idx]

        fg_finish_ie_work_item(
            self.session, self.ie_cfg, work_item, self.fs_source, self.worklist)

        self.do_pub('ie.sts.folder done', self.worklist[self.worklist_idx].ie_folder.db_name)
        self.worklist_idx += 1
        self.do_pub('ie.cmd.start item')

    def cancel(self):
        ''' mark the wowklist for cancellation '''
        self.cancelling = True



