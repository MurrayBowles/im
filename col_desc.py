""" database column descriptor, used by tbl/row_buf and tbl_xxx_view """

from typing import Any, List, Mapping, NewType, Tuple, Type

from util import force_list

class ColDesc(object):
    path: str # name '.'...
    disp_names: List[str] # display names, in decreasing length
    fmt: str # [-]<number>
    hidden: bool
    editable: bool

    def __init__(self, path, disp_names, fmt='-8', hidden=False, editable=False):
        self.path = path
        self.disp_names = force_list(disp_names)
        self.fmt = fmt
        self.hidden = hidden
        self.editable = editable

    def base_repr(self):
        s = '%s, %s' % (self.path, repr(self.disp_names))
        if self.fmt != '-8': s += ', fmt: ' + self.fmt
        if self.hidden: s += ', hidden=True'
        if self.editable: s += ', editable=True'
        return s

    def __repr__(self):
        return self.__class__.__name__ + '(' + self.base_repr() + ')'

class TextColDesc(ColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class DateColDesc(ColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class IntColDesc(ColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
