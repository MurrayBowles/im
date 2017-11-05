''' import/export folders/images to/from the database '''

from collections import deque
from db import DbFolder, DbImage, FsFolder, FsImage
from ie_cfg import *
from ie_fs import *


class IEWorkItem(object):

    def __init__(self, fs_folder, ie_folder):

        self.fs_folder = fs_folder
        self.ie_folder = ie_folder
        self.msgs = []  # list() # of IENote

        # set by proc_work_item()
        self.deleted_images = []    # list of FsImages that have been deleted from the import source
        self.existing_images = []   # list of existing (FsImage, IEImage, is_new)
        self.get_exif = set()       # set of ie_images to get the exif data (e.g. tags) for
        self.get_thumbnail = set()  # set of IeImages to get/update the thumbnail for

    def __repr__(self):
        return '<WorkItem %s %s>' % (
            str(self.fs_folder) if self.fs_folder is not None else 'NoFS',
            str(self.ie_folder) if self.ie_folder is not None else 'NoIE'
        )

def get_ie_worklist(session, fs_source, source_type, paths):
    ''' return a list of IEWorkItems '''

    if source_type == SourceType.DIR_SET:
        ie_folders = scan_dir_set(paths[0], is_std_dirname, proc_std_dirname)
    elif source_type == SourceType.DIR_SEL:
        ie_folders = scan_dir_sel(paths, proc_std_dirname)
    elif source_type == SourceType.FILE_SET:
        ie_folders = scan_file_set(paths[0], lambda filename: True, proc_corbett_filename)
    elif source_type == SourceType.FILE_SEL:
        ie_folders = scan_file_sel(paths, proc_corbett_filename)
    else:
        raise ValueError('unknown source type')
    worklist = deque()
    if source_type.is_multiple():   # DIR_SEL or FILE_SEL
        # get all FsFolders that match folders
        for ie_folder in ie_folders:
            fs_folder = FsFolder.find(session, fs_source, ie_folder.fs_name)
            worklist.append(IEWorkItem(fs_folder, ie_folder))
    else:                           # DIR_SET or FILE_SET
        # get all FsFolders in the FsSource
        fs_folders = fs_source.folders
        # merge fs_folders with ie_folders
        while True:
            if len(fs_folders) != 0 and len(ie_folders) != 0:
                fs_name = fs_folders[0].name
                ie_name = ie_folders[0].fs_name
                if fs_name == ie_name:
                    worklist.append(IEWorkItem(fs_folders.pop(0), ie_folders.pop(0)))
                elif fs_name < ie_name:
                    worklist.append(IEWorkItem(fs_folders.pop(0), None))
                else:
                    worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            elif len(fs_folders) != 0:
                worklist.append(IEWorkItem(fs_folders.pop(0), None))
            elif len(ie_folders) != 0:
                worklist.append(IEWorkItem(None, ie_folders.pop(0)))
            else:
                break
    return worklist

def fg_proc_ie_work_item(session, ie_cfg, work_item, fs_source, source_type):

    def import_ie_image(fs_image, ie_image, new_fs_image):
        work_item.existing_images.append((fs_image, ie_image, new_fs_image))
        if db_folder is not None:
            db_image = DbImage.get(session, db_folder, ie_image.name)[0]
            if fs_image.db_image is None:
                fs_image.db_image = db_image
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
    if source_type == SourceType.DIR_SET or source_type == SourceType.DIR_SEL:
        # scan the folder's image files
        # (this has already been done in the FILE_SET/SEL case by scan_file_set/sel)
        scan_std_dir_files(ie_folder)
    if fs_folder is None:
        # create an FsFolder
        fs_folder = FsFolder.get(session, fs_source, ie_folder.fs_name)[0]
        work_item.fs_folder = fs_folder
        # also auto-create a DbFolder if ie_folder has a good name and date
        if (IEMsg.find(IEMsgType.NAME_NEEDS_EDIT, ie_folder.msgs) is None and
                    IEMsg.find(IEMsgType.NO_DATE, ie_folder.msgs) is None):
            db_folder = DbFolder.get(session, ie_folder.date, ie_folder.name)[0]
            fs_folder.db_folder = db_folder
    db_folder = fs_folder.db_folder # this may be None
    if source_type == SourceType.FILE_SEL:
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
                    worklist.deleted_images.append(fs_image)
                else: # ie_image.name < fs_image.name
                    fs_image = FsImage.add(session, fs_folder, ie_image.name)
                    import_ie_image(fs_image, ie_image, True)
            elif len(fs_images) != 0:
                worklist.deleted_images.extend(fs_images)
                break
            elif len(ie_images) != 0:
                ie_image = ie_images.pop(0)
                fs_image = FsImage.add(session, fs_folder, ie_image.name)
                import_ie_image(fs_image, ie_image, True)
            else:
                break

def bg_proc_ie_work_item(work_item):
    get_ie_image_thumbnails(work_item.get_thumbnail)
    get_ie_image_exifs(work_item.get_exif)
