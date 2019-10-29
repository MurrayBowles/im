""" database column descriptor, used by tbl_acc, tbl/row_buf, and tbl_xxx_view """

from typing import Any, List, Mapping, NewType, Tuple, Type


from util import force_list


class ColDesc(object):
    db_name: str            # the attribute db_name in its database table class
    disp_names: List[str]   # display names, in decreasing length
    fmt: str                # {l|c|r}<#columns>
    hidden: bool
    editable: bool

    # set by TblDesc._complete_col_desc()
    db_attr: Any            # the column attribute object in its database table class

    def_fmt = 'l8'          # left-justified, 8 columns

    def __init__(
            self, db_name, disp_names,
            hidden=False, editable=False, **kwargs
    ):
        self.db_name = db_name
        self.disp_names = force_list(disp_names)
        self.fmt = kwargs['fmt'] if 'fmt' in kwargs else self.__class__.def_fmt
        self.hidden = hidden
        self.editable = editable

    def base_repr(self):
        s = '%r, %r' % (self.db_name, self.disp_names)
        if self.fmt != ColDesc.def_fmt:
            s += ', fmt: ' + self.fmt
        if self.hidden:
            s += ', hidden=True'
        if self.editable:
            s += ', editable=True'
        return s

    def __repr__(self):
        return self.__class__.__name__ + '(' + self.base_repr() + ')'


class DataColDesc(ColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TextCD(DataColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DateCD(DataColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class IntCD(DataColDesc):
    def_fmt = 'r8'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class IdCD(DataColDesc):
    def_fmt = 'l16'          # left-justified, 16 columns

    def __init__(self, *args, **kwargs):
        if 'hidden' not in kwargs:
            kwargs['hidden'] = True  # default hidden to True
        super().__init__(*args, **kwargs)


class LinkColDesc(ColDesc):
    foreign_tbl_name: str   # e.g. 'FsFolder'
    # db_name is the database attribute used to join to the foreign table

    # set by TblDesc._complete_col_desc()
    foreign_td: Any         # the TblDesc of the foreign table

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'foreign_tbl_name' in kwargs:
            self.foreign_tbl_name = kwargs['foreign_tbl_name']
        else:
            raise KeyError('foreign_tbl_name not specified')


class RefCD(LinkColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ParentCD(LinkColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

if __name__ == '__9main__':
    int_cd = IntCD('size', ['Size', 'Sz'])
    id_cd = IdCD('parent_id', 'Parent ID')
    ref_cd = RefCD('parent_id', 'Folder', foreign_tbl_name='DbFolder')
    pass