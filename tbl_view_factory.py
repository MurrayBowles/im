''' workaraound for Pyton circularity issues '''

from typing import Union

from row_desc import RowDesc
from tbl_desc import TblDesc
from tbl_query import TblQuery
from tbl_report_view import TblReportTP


def get(parent, spec: Union[TblDesc, TblQuery]):
    if isinstance(spec, TblDesc):
        tp_cls = TblReportTP
        vc = spec.viewed_cols(TblReportTP)
        cds = [spec.lookup_col_desc(name) for name in vc]
        tbl_query = TblQuery(spec, RowDesc(cds))
    else:  # TblQuery
        tbl_query = spec
        tp_cls = TblReportTP  # TODO: based on query somehow
    return tp_cls(parent, tbl_query)