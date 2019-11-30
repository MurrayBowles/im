''' database Table Descriptor instances '''

from col_desc import DateCD, DateTimeCD, IdCD, IMDateCD, IMDateEltCD, IntCD
from col_desc import ParentCD, RefCD, ShortcutCD, TextCD
import db
from tbl_desc import TblDesc, ItemTblDesc
from tbl_view import TblItemTP
from tbl_report_view import TblReportTP

Item_td = TblDesc(db.Item, 'Item', [
    IdCD('id', ['ID']),
    TextCD('name', 'Name'),
    TextCD('type', 'Type')  # FIXME: enumeration
], {
    TblReportTP: ['name', 'type']
}, '+id')

DbFolder_td = ItemTblDesc(db.DbFolder, 'Folder', [
    DateCD('date', ['Date']),
    IMDateEltCD('date2_year', ['Year']),
    IMDateEltCD('date2_month', ['Month']),
    IMDateEltCD('date2_day', ['Day']),
    IMDateCD('date2', 'Date'),
    IntCD('edit_level', 'Edit Level')
], {
    TblReportTP: ['date2', 'name', 'edit_level'],
}, '-date2,+name')

ImageData_td = TblDesc(db.ImageData, ['Image Data'], [
    IntCD('sensitivity', ['Sensitivity', 'ISO']),
    IntCD('image_height', ['Height']),
    IntCD('image_width', ['Width'])
], {
    TblReportTP: ['image_width', 'image_height', 'sensitivity']
}, '-sensitivity')  # FIXME: sorter should not be mandatory
ImageData_td._menu_text = 'Image Data'

DbImage_td = ItemTblDesc(db.DbImage, 'Image', [
    ParentCD('folder_id', 'Folder', foreign_tbl_name='DbFolder'),
    ShortcutCD('folder_date2', 'Folder Date', path_str='folder_id.date2'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder_id.name'),
    RefCD('data_id', 'Data', foreign_tbl_name='ImageData'),
    ShortcutCD('sensitivity', ['Sensitivity', 'ISO'], path_str='data_id.sensitivity')
], {
    TblReportTP: ['folder_name', 'name', 'sensitivity']
}, '-folder_date2,+folder_name,+name')

FsFolder_td = ItemTblDesc(db.FsFolder, ['External Folder', 'FsFolder'], [
    IMDateEltCD('db_date2_year', ['Year']),
    IMDateEltCD('db_date2_month', ['Month']),
    IMDateEltCD('db_date2_day', ['Day']),
    IMDateCD('db_date2', 'Suggested Date'),
    TextCD('db_name', 'Suggested Name'),
    DateTimeCD('last_scan', 'Last Scan'),
    DateTimeCD('last_import_tags', 'Last Tags Import')
], {
    TblReportTP: ['db_date2', 'db_name', 'last_scan'],
}, '-db_date2,+db_name')


FsImage_td = ItemTblDesc(db.FsImage, 'External Image', [
    RefCD('data_id', 'Data', foreign_tbl_name='ImageData'),
    ParentCD('folder_id', 'Folder', foreign_tbl_name='FsFolder'),
    ShortcutCD('folder_date', 'Folder Date', path_str='folder_id.db_date2'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder_id.db_name'),
    ParentCD('db_image_id', 'Image', foreign_tbl_name='DbImage')
], {
    TblReportTP: ['folder_date', 'folder_name', 'name']
}, '-folder_date,+folder_name,+name')

TblDesc.complete_tbl_descs()

if __name__== '__main__':
    Item_s = repr(Item_td)
    report_vcs = Item_td.viewed_cols(TblReportTP)
    item_vcs = Item_td.viewed_cols(TblItemTP)
    DbFolder_s = repr(DbFolder_td)
    TblDesc.complete_tbl_descs()
    pass
