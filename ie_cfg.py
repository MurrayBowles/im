""" persistent event for Import/Export: cfg.ie """

from enum import Enum
# import wx


class ImportMode(Enum):

    SET = 0 # specify the parent directory of a set of directories/files
    SEL = 1 # specify a selection of directories/files

    @classmethod
    def default(cls):
        return ImportMode.SET

class IEFolderAct(Enum):
    """ import/export actions on a folder """
    SCAN = 0        # scan folder and its images
    IMPORT_TAGS = 1 # import folder tags


class IEImageAct(Enum):
    """ import/export actions on an image file """
    IMPORT_TAGS = 0     # import image tags
    EXPORT_TAGS = 1     # export image tags
    IMPORT_THUMBS = 2   # import image thimbnails


class IECfg(object):
    ''' import/export parameters, persisted between runs '''

    def __init__(self):
        self.tag_source_id = -1
        self.img_source_id = -1
        self.clear_paths()
        self.import_folder_tags = True
        self.import_image_tags = True   # also governs import of EXIF event
        self.export_image_tags = True
        self.import_thumbnails = False
        self.reports = []
        # not really persisted -- just here for communication with ie_fs
        # FIXME: clean this up
        self.import_mode = ImportMode.default()

    def clear_paths(self):
        # self.chooser_path = wx.StandardPaths.Get().GetDocumentsDir()
        self.paths = []

    def clear_reports(self):
        self.reports = []