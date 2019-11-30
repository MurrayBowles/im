""" database Column Descriptors """

import copy
from dataclasses import dataclass
from typing import Any, List, TypeVar

from imdate import IMDate
from util import force_list, gui_null_str


class CDXState(object):
    ''' the state of a Shortcut and/or Virtual ColDesc chain's eXpansion '''

    def __init__(self, xs=None):
        if xs is not None:
            self.path = copy.copy(xs.path)
            self.alias = copy.copy(xs.alias)
        else:
            self.path = []      # List[ColDesc]
            self.alias = None

    def __repr__(self):
        return '%s%s' % (
            '-' if len(self.path) == 0 else '.'.join([cd.db_name for cd in self.path]),
            '' if self.alias is None else ' AS ' + self.alias)

    def ref(self, col_desc):
        res = CDXState(self)  # make a new copy of the CDXState
        res.path.append(col_desc)  # append the CD to the path
        if res.alias is None:
            # set the SQL 'AS' alias from the first CD in the chain
            res.alias = col_desc.db_name
        return res

    def sfx(self, virtual_cd, dependent_cd):
        res = CDXState(self)
        if res.alias is None:
            res.alias = virtual_cd.db_name
        res.alias += virtual_cd._sfx(dependent_cd)
        return res

    def extend(self, shortcut_cd, path):
        res = CDXState(self)
        if res.alias is None:
            res.alias = shortcut_cd.db_name
        res.path.extend(path)
        return res

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
        ''' Return the string to use in SQL literals. '''
        return str(literal)

    def gui_str(self, val):
        ''' Return the string to use in GUI output. '''
        return gui_null_str if val is None else str(val)

    def sql_select(self, col_ref_fn, xs: CDXState):
        ''' Call col_ref_fn(col_desc) for every SQL column accessed to display this column '''
        col_ref_fn(xs.ref(self))

    def sql_relop_str(self, op: str, literal, col_ref_fn, xs: CDXState):
        return '%s %s %s' % (col_ref_fn(xs.ref(self)), op, self.sql_literal_str(literal))

    def sql_order_str(self, descending: bool, col_ref_fn, xs: CDXState):
        s = col_ref_fn(xs.ref(self))
        if descending:
            s += ' DESC'
        return s

    def get_val(self, get_sql_val_fn, xs: CDXState):
        return get_sql_val_fn(xs.ref(self).alias)

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
        raise KeyError('db_name %s not in path' % db_name)


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


class DateTimeCD(DataColDesc):
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

    def sql_order_str(self, descending: bool, col_ref_fn, xs: CDXState):
        ref = col_ref_fn(xs.ref(self))
        if descending:
            # IMDate.unk (0) will already sort at the end
            return ref + ' DESC'
        else:
            return 'CASE WHEN %s == 0 THEN 9999 ELSE %s' % (ref, ref)


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

    def sql_select(self, col_ref_fn, xs: CDXState):
        ''' Call col_ref_fn(col_desc) for every SQL column accessed to display this column '''
        return self.path_cds[-1].sql_select(
            col_ref_fn, xs.extend(self, self.path_cds[0:-1]))

    def sql_relop_str(self, op: str, literal, col_ref_fn, xs: CDXState):
        return self.path_cds[-1].sql_relop_str(
            op, literal, col_ref_fn, xs.extend(self, self.path_cds[0:-1]))

    def sql_order_str(self, descending: bool, col_ref_fn, xs: CDXState):
        return self.path_cds[-1].sql_order_str(
            descending, col_ref_fn, xs.extend(self, self.path_cds[0:-1]))

    def get_val(self, get_sql_val_fn, xs: CDXState):
        return self.path_cds[-1].get_val(get_sql_val_fn, xs.extend(self, self.path_cds[0:-1]))


class VirtualColDesc(ColDesc):
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

    def _sfx(self, dcd):
        assert len(dcd.db_name) > len(self.db_name)
        assert dcd.db_name.startswith(self.db_name)
        return dcd.db_name[len(self.db_name):]

    def base_repr(self):
        s = super().base_repr()
        s += ', dependencies=%r' % self.dependencies
        return s

    def sql_literal_str(self, literal):
        raise ValueError('sql_literal_str called on a VirtualColDesc')

    def sql_select(self, col_ref_fn, xs: CDXState):
        ''' Call col_ref_fn(col_desc) for every SQL column accessed to display this column '''
        for dcd in self.dependency_cds:
            dcd.sql_select(col_ref_fn, xs.sfx(self, dcd))

    def sql_relop_str(self, op: str, literal, col_ref_fn, xs: CDXState):
        lits = literal  # literal is a sequence
        cds = self.dependency_cds
        try:
            if op == '==':
                r = ' AND '.join([
                    cd.sql_relop_str(
                        op, l, col_ref_fn, xs.sfx(self, cd)) for cd, l in zip(cds, lits)])
            elif op == '!=':
                r = ' OR '.join([
                    cd.sql_relop_str(
                        op, l, col_ref_fn, xs.sfx(self, cd)) for cd, l in zip(cds, lits)])
            else:
                def res(lits, cds):
                    if len(lits) == 1:
                        return cds[0].sql_relop_str(
                            op, lits[0], col_ref_fn, xs.sfx(self, cds[0]))
                    else:
                        return '(%s OR %s AND %s)' % (
                            cds[0].sql_relop_str(
                                op, lits[0], col_ref_fn, xs.sfx(self, cds[0])),
                            cds[0].sql_relop_str(
                                '==', lits[0], col_ref_fn, xs.sfx(self, cds[0])),
                            res(lits[1:], cds[1:])
                        )
                r = res(lits, cds)
        except Exception as ed:
            print('asf')
        return r

    def sql_order_str(self, descending: bool, col_ref_fn, xs: CDXState):
        cols = []
        for dcd in self.dependency_cds:
            cols.append(dcd.sql_order_str(descending, col_ref_fn, xs.sfx(self, dcd)))
        return ', '.join(cols)

    def get_val(self, get_sql_val_fn, xs: CDXState):
        return [dcd.get_val(get_sql_val_fn, xs.sfx(self, dcd)) for dcd in self.dependency_cds]


class IMDateCD(VirtualColDesc):
    def __init__(self, *args, **kwargs):
        db_name =  args[0]
        ext_kwargs = kwargs
        ext_kwargs['dependencies'] = [db_name + '_year', db_name + '_month', db_name + '_day']
        super().__init__(*args, **ext_kwargs)

    def sql_relop_str(self, op: str, literal, col_ref_fn, xs: CDXState):
        # literal is an IMDate
        return super().sql_relop_str(op, literal.val, col_ref_fn, xs)

    def get_val(self, get_sql_val_fn, xs: CDXState):
        args = super().get_val(get_sql_val_fn, xs)
        return IMDate(*args)


if __name__ == '__main__':
    int_cd = IntCD('size', ['Size', 'Sz'])
    id_cd = IdCD('parent_id', 'Parent ID')
    ref_cd = RefCD('parent_id', 'Folder', foreign_tbl_name='DbFolder')
    shortcut_cd = ShortcutCD('parent_name', 'Folder Name', path_str='parent_id.name')
    pass