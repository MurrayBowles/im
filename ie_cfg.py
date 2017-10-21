''' Inport/Export configuration '''

from enum import Enum
import json

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

    def to_json(self):
        obj = {
            'source_type': self.source_type.name
        }
        return json.dumps(obj)
