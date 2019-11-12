''' search filter tuples '''

from typing import Any, Tuple

from sql_util import JoinState

class Filter(object):
    tup: Tuple[Any]
    ''' filter-tup:
            ('</<=/==/!=/>=/>', col-desc, value)
            ('begins/ends/contains', col-desc, str-expr)
            ('null/nonnull', col-desc)
            ('tag', tag-expr)
            ('note', note-expr)
            ('|/&', filter-tup,...)
            ('-', filter-tup, filter-tup)
        tag-expr:
            'tag-str'
            ('|/&', tag-expr,...)
            ('-', tag-expr, tag-expr)
        note-expr:
            ('begins/ends/contains', col-desc, str-expr)
            ('|/&', note-expr,...)
            ('-', note-expr, note-expr)
        str-expr:
            str
            ('|/&', str-expr,...)
            ('-', str-expr, str-expr)
    '''
    def __init__(self, *args):
        self.tup = tuple(args)

    @staticmethod
    def _tup_str(t, js: JoinState):
        map = {
            '<':        lambda t: Filter._relop_str(t, js, '<'),
            '<=':       lambda t: Filter._relop_str(t, js, '<='),
            '==':       lambda t: Filter._relop_str(t, js, '=='),
            '!=':       lambda t: Filter._relop_str(t, js, '!='),
            '>=':       lambda t: Filter._relop_str(t, js, '>='),
            '>':        lambda t: Filter._relop_str(t, js, '>'),
            '&':        lambda t: Filter._many_str(t, js, 'AND'),
            '|':        lambda t: Filter._many_str(t, js, 'OR')
        }
        try:
            return map[t[0]](t)
        except KeyError:
            raise KeyError(str(t))

    @staticmethod
    def _relop_str(t, js: JoinState, op):
        return '%s %s %s' % (
            js.sql_col_ref(t[1]), op, t[1].sql_literal_str(t[2]))

    @staticmethod
    def _many_str(t, js: JoinState, op):
        operands = [Filter._tup_str(operand, js) for operand in t[1:]]
        return (' %s ' % op).join(operands)

    def sql_str(self, js: JoinState):
        return 'WHERE ' + Filter._tup_str(self.tup, js)

if __name__ == '__main__':
    import tbl_descs
    from tbl_desc import TblDesc
    js = None
    s = None
    def check(tbl_desc, *args):
        global js
        global s
        f = Filter(*args)
        js = JoinState(tbl_desc)
        try:
            s = f.sql_str(js)
        except Exception as ed:
            print('hey')
        pass

    TblDesc.complete_tbl_descs()
    DbFolder_td = TblDesc.lookup_tbl_desc('DbFolder')
    DbImage_td = TblDesc.lookup_tbl_desc('DbImage')
    check(DbFolder_td, '<', DbFolder_td.row_desc.col_descs[0], 123)
    check(DbFolder_td, '==', DbFolder_td.row_desc.col_descs[1], 'diana')
    check(DbFolder_td, '&', ('<', DbFolder_td.row_desc.col_descs[0], 123), ('==', DbFolder_td.row_desc.col_descs[1], 'diana'))
    pass




