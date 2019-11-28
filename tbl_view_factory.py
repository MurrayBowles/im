''' workaraound for Pyton circularity issues '''

from tbl_view import TblTP
from tbl_report_view import TblReportTP


def get(parent, tbl_desc):
    return TblReportTP(parent, tbl_desc)