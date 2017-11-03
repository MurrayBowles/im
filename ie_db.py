''' import/export folders/images to/from the database '''

from collections import deque
from db import FsFolder, FsSource
from ie_cfg import *
from ie_fs import *


class IEWorkItem(object):

    def __init__(self, fs_folder, ie_folder):

        self.fs_folder = fs_folder
        self.ie_folder = ie_folder
        self.children = []
        self.msgs = []  # list() # of IENote

    def __repr__(self):
        return '<WorkItem %s %s>' % (
            str(self.fs_folder) if self.fs_folder is not None else '-',
            str(self.ie_folder) if self.ie_folder is not None else '-'
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

def proc_ie_work_item(session, work_item, fs_source, source_type):
    if fs_source == FsSource.DIR_SET or fs_source == FsSource.DIR_SEL:
        # scan the folder's image files (this has already been done in the FILE_SET/SEL case)
        scan_std_dir_files(ie_folder)


