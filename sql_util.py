''' SQL utilities'''

from typing import List

from col_desc import ColDesc, DataColDesc, LinkColDesc, ShortcutCD
from row_desc import RowDesc
from tbl_desc import TblDesc


class JoinState:
    tbl_desc: TblDesc
    chains: List[List[ColDesc]]
    select_strs: List[str]      # SQL JOIN-clause strings

    def __init__(self, tbl_desc: TblDesc):
        self.tbl_desc = tbl_desc
        self.chains = []
        self.sql_strs = []
        self.select_cols = {}   # map: db_name -> (select_strs[] index, col_desc)
        self.select_strs = []

    def _register_join_chain(self, join_chain: List[ColDesc]):
        ''' Return idx, l: a join_chains index, the length of the match.
        cases:
            1. join_chain exactly matches (a prefix of a) a list in join_chains, l == len(join_chain)
            2. a list in join_chains matches a prefix of join_chain, l == the length of the prefix
            3. no match: idx is the index of a new empty list added to join_chains, l == 0
        '''
        arg_len = len(join_chain)
        jcx = 0
        for jc in self.chains:
            check_len = len(jc)
            min_len = min(arg_len, check_len)
            try:
                for x in range(0, min_len):
                    if(jc[x] is not join_chain[x]):
                        raise ValueError
            except ValueError:
                jcx += 1
                continue
            if check_len >= arg_len:
                # case 1: join_chain matches join_chains[jcx]
                return jcx, arg_len
            else:
                # case 2: join_chain extends join_chains[jcx]
                self.chains[jcx].extend(join_chain[min_len:])
            return jcx, check_len
        # case 3: join_chain matches nothing in join_chains
        self.chains.append(join_chain)
        return jcx, 0

    def _add_joins(self, join_chain: List[ColDesc]):
        ''' Add sql_strs for join_chain, and return the target-table SQL name '''
        jcx, num_match = self._register_join_chain(join_chain)
        jcx_str = str(jcx)
        if num_match == 0:
            td1 = self.tbl_desc
            td1_name = td1.sql_name()
        else:
            td1 = join_chain[num_match - 1].foreign_td
            td1_name = td1.sql_name(jcx_str)
        for x in range(num_match, len(join_chain)):
            pcd = join_chain[x]
            td2 = pcd.foreign_td
            join_str = 'JOIN %s AS %s ON %s.%s == %s.id' % (
                td2.sql_name(),
                td2.sql_name(jcx_str),
                td1_name,
                pcd.db_name,
                td2.sql_name(jcx_str)
            )
            self.sql_strs.append(join_str)
            td1 = td2
            td1_name = td1.sql_name(jcx_str)
        return td1_name

    def _sql_col_ref(self, col_desc: ColDesc, select: bool):
        ''' Return the SQL string to reference col_desc, adding any necessary sql_strs.
            Called only through the closures returned by sql_col_ref_fn()
        '''
        if col_desc.db_name in self.select_cols:
            col_ref = col_desc.db_name
        else:
            path_cds = col_desc.sql_path_cds()
            if len(path_cds) > 1:
                target_sql_name = self._add_joins(path_cds[0:-1])
                col_ref = '%s.%s' % (target_sql_name, path_cds[-1].db_name)
            else:
                col_ref = '%s.%s' % (self.tbl_desc.sql_name(), path_cds[0].db_name)
            if select:
                col_ref += ' AS %s' % col_desc.db_name
                if col_desc.db_name not in self.select_cols:
                    x = len(self.select_strs)
                    self.select_cols[col_desc.db_name] = (x, col_desc)
                    self.select_strs.append(col_ref)
        return col_ref

    def sql_col_ref_fn(self, select: bool = False):
        return lambda cd: self._sql_col_ref(cd, select)

if __name__ == '__main__':
    import tbl_descs
    TblDesc.complete_tbl_descs()
    DbFolder_td = TblDesc.lookup_tbl_desc('DbFolder')
    DbImage_td = TblDesc.lookup_tbl_desc('DbImage')
    pass
