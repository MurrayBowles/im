''' Inport/Export configuration '''

from enum import Enum
import wx

class SourceType(Enum):

    DIR_SET = 0
    DIR_SEL = 1
    FILE_SET = 2
    FILE_SEL = 3

    @classmethod
    def default(cls):
        return SourceType.DIR_SET

    @classmethod
    def names(cls):
        return ['folder set', 'folder selection', 'file set', 'file selection']

    def __str__(self):
        return SourceType.names()[self.value]

    def is_file(self):
        return self == SourceType.FILE_SEL

    def is_directory(self):
        return self != SourceType.FILE_SEL

    def is_multiple(self):
        return self == SourceType.DIR_SEL or self == SourceType.FILE_SEL

class IECfg(object):

    def __init__(self):
        self.source_type = SourceType.default()
        self.clear_paths()
        self.import_folder_tags = True
        self.import_image_tags = True
        self.export_image_tags = True
        self.import_thumbnails = False

    def clear_paths(self):
        self.chooser_path = wx.StandardPaths.Get().GetDocumentsDir()
        self.paths = []

