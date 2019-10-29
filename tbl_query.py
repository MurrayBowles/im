''' database queries: Filters, Sorters '''

from tbl_desc import TblDesc
from col_desc import ColDesc


class TblQuery(object):

    cols: List[Union[TblDesc, ColDesc]]     # TD [, ref|parent-CD ...], data-CD
    # filter: Filter
    # sorter: Sorter

    def __init__(self, cols):
        self.cols = cols

    def __repr__(self):
        s = 'TblQuery(%r)' % (self.cols)
        return s

    def get(self, session, limit=None, skip=0):
        for col in self.cols:

        base_td = self.cols[0]
        q = session.Query(base_td.tbl_cls)  # the base table
        leaf_cd = self.cols[-1]


class ColPath(object):
    steps: List[Union[TblDesc, ColDesc]]  # TD [, ref|parent-CD ...], data-CD

    def __init__(self, root_td: TblDesc, path_str: str):
        self.steps = [root_td]
        cur_td = root_td
        for step_str in path_str.split('.')[0:-1]:
            cur_cd = root_td.