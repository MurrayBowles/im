''' database Table Descriptor instances '''

from col_desc import DateCD, IMDateEltCD, IdCD, ParentCD, ShortcutCD, TextCD
import db
from tbl_desc import TblDesc, ItemTblDesc
from tbl_view import TblItemView, TblReportView

Item_td = TblDesc(db.Item, 'Item', [
    IdCD('id', ['ID']),
    TextCD('name', 'Name'),
    TextCD('type', 'Type')  # FIXME: enumeration
], {
    TblReportView: ['name', 'type']
}, '+id')

DbFolder_td = ItemTblDesc(db.DbFolder, ['Database Folder', 'DbFolder'], [
    DateCD('date', ['Date']),
    IMDateEltCD('date2_year', ['Year']),
    IMDateEltCD('date2_month', ['Month']),
    IMDateEltCD('date2_day', ['Day'])
], {
    TblReportView: ['name', 'date'],
}, '-date,+name')

DbImage_td = ItemTblDesc(db.DbImage, 'Database Image', [
    ParentCD('folder_id', 'Folder', foreign_tbl_name='DbFolder'),
    ShortcutCD('folder_date', 'Folder Date', path_str='folder_id.date'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder_id.name')
], {
    TblReportView: ['name', 'parent_id']
}, '-folder_date,+folder_name,+name')

TblDesc.complete_tbl_descs()

if __name__== '__main__':
    Item_s = repr(Item_td)
    report_vcs = Item_td.viewed_cols(TblReportView)
    item_vcs = Item_td.viewed_cols(TblItemView)
    DbFolder_s = repr(DbFolder_td)
    TblDesc.complete_tbl_descs()
    pass
