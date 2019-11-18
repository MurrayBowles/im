""" database Column Descriptors """

from typing import Any, List, TypeVar

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

    def sql_literal_str(self, literal):
        return str(literal)

    def sql_path_cds(self):
        return [self]

    def sql_select_str(self, col_ref_fn):
        return col_ref_fn(self)

    def sql_relop_str(self, op: str, literal, col_ref_fn):
        return '%s %s %s' % (col_ref_fn(self), op, self.sql_literal_str(literal))

    def sql_order_str(self, descending: bool, col_ref_fn):
        s = col_ref_fn(self)
        if descending:
            s += ' DESC'
        return s

    ''' see also:
    Join State.sql_col_ref()
    Filter._relop_str(), _between_str()
    TblDesc._complete_col_desc()
    '''

    @classmethod
    def find(cls, db_name, col_descs: List[Any]):   # FIXME: Any should be ColDesc
        for col_desc in col_descs:
            if col_desc.db_name == db_name:
                return col_desc
        raise KeyError('db_name %s not in col_descs' % db_name)

class DataColDesc(ColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TextCD(DataColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sql_literal_str(self, literal):
        return '"%s"' % literal


class DateCD(DataColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sql_literal_str(self, literal):
        return '"%s"' % literal


class IntCD(DataColDesc):
    def_fmt = 'r8'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class IMDateEltCD(DataColDesc):
    def_fmt = 'l4'

    def __init__(self, *args, **kwargs):
        if 'hidden' not in kwargs:
            kwargs['hidden'] = True  # default hidden to True
        super().__init__(*args, **kwargs)

    def sql_order_str(self, descending: bool, col_ref_fn):
        ref = col_ref_fn(self)
        if descending:
            # IMDate.unk (0) will already sort at the end
            return ref
        else:
            return 'CASE WHEN %s == 0 THEN 999 ELSE %s' % (ref, ref)


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
        self.foreign_td = None

    def base_repr(self):
        s = super().base_repr()
        s += ', foreign_tbl_name=%r' % (self.foreign_tbl_name)
        return s


class RefCD(LinkColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ParentCD(LinkColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SuperCD(LinkColDesc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ShortcutCD(ColDesc):
    path_str: str   # [ link-shortcut-cd-name | link-cd-name '.'... ] [cd-name]

    # set by TblDesc._complete_col_desc(), which flattens embedded Shortcut/VirtualCDs
    path_cds = List[ColDesc]    # [ link-CD ... ] [ CD ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'path_str' in kwargs:
            self.path_str = kwargs['path_str']
        else:
            raise KeyError('path_str not specified')
        self.path_cds = None

    def base_repr(self):
        s = super().base_repr()
        s += ', path_str=%r' % (self.path_str)
        return s

    def sql_literal_str(self, literal):
        return self.path_cds[-1].sql_literal_str(literal)

    def sql_path_cds(self):
        return self.path_cds


class VirtualCD(ColDesc):
    dependencies: List[str]

    # set by TblDesc._complete_col_desc(), which flattens embedded Shortcut/VirtualCDs
    dependency_cds = List[ColDesc]    # [ link-CD ... ] [ CD ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'dependencies' in kwargs:
            self.dependencies = kwargs['dependencies']
        else:
            raise KeyError('dependencies not specified')
        self.dependency_cds = None

    def base_repr(self):
        s = super().base_repr()
        s += ', dependencies=%r' % self.dependencies
        return s

    def sql_literal_str(self, literal):
        raise ValueError('sql_literal_str not overloaded for %s', self.__class__.__name__)

    def sql_select_str(self, col_ref_fn):
        raise ValueError('sql_select_str not specified')

    def sql_relop_str(self, op: str, literal, col_ref_fn):
        raise ValueError('sql_relop_str not specified')

    def sql_order_str(self, descending: bool, col_ref_fn):
        raise ValueError('sql_order_str not specified')


if __name__ == '__main__':
    int_cd = IntCD('size', ['Size', 'Sz'])
    id_cd = IdCD('parent_id', 'Parent ID')
    ref_cd = RefCD('parent_id', 'Folder', foreign_tbl_name='DbFolder')
    shortcut_cd = ShortcutCD('parent_name', 'Folder Name', path_str='parent_id.name')
    pass