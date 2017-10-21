''' Inport/Export configuration '''

from enum import Enum

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
        return ['directory set', 'directory selection', 'file set', 'file selection']

    def __str__(self):
        return SourceType.names()[self.value]

class IECfg(object):

    def __init__(self):
        self.source_type = SourceType.default()
        self.import_folder_tags = True
        self.import_image_tags = True
        self.export_image_tags = True
        self.import_thumbnails = False

