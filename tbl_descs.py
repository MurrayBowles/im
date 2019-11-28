''' database Table Descriptor instances '''

from col_desc import DateCD, IdCD, IMDateCD, IMDateEltCD, IntCD
from col_desc import ParentCD, RefCD, ShortcutCD, TextCD
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

DbFolder_td = ItemTblDesc(db.DbFolder, ['Folder', 'DbFolder'], [
    DateCD('date', ['Date']),
    IMDateEltCD('date2_year', ['Year']),
    IMDateEltCD('date2_month', ['Month']),
    IMDateEltCD('date2_day', ['Day']),
    IMDateCD('date2', ['date2_year', 'date2_month', 'date2_day'])
], {
    TblReportView: ['name', 'date'],
}, '-date2,+name')

ImageData_td = TblDesc(db.ImageData, ['Image Data'], [
    IntCD('sensitivity', ['Sensitivity', 'ISO']),
    IntCD('image_height', ['Height']),
    IntCD('image_width', ['Width'])
], {
    TblReportView: ['image_width', 'image_height', 'sensitivity']
}, '-sensitivity')  # FIXME: sorter should not be mandatory
ImageData_td._menu_text = 'Image Data'

DbImage_td = ItemTblDesc(db.DbImage, 'Image', [
    ParentCD('folder_id', 'Folder', foreign_tbl_name='DbFolder'),
    ShortcutCD('folder_date2', 'Folder Date', path_str='folder_id.date2'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder_id.name'),
    RefCD('data_id', 'Data', foreign_tbl_name='ImageData'),
    ShortcutCD('sensitivity', ['Sensitivity', 'ISO'], path_str='data_id.sensitivity')
], {
    TblReportView: ['name', 'parent_id']
}, '-folder_date2,+folder_name,+name')

TblDesc.complete_tbl_descs()

if __name__== '__main__':
    Item_s = repr(Item_td)
    report_vcs = Item_td.viewed_cols(TblReportView)
    item_vcs = Item_td.viewed_cols(TblItemView)
    DbFolder_s = repr(DbFolder_td)
    TblDesc.complete_tbl_descs()
    pass
