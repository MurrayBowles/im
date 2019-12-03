''' database Table Descriptor instances '''

from col_desc import DateCD, ChildrenCD, DateTimeCD, IdCD, IMDateCD, IMDateEltCD, IntCD
from col_desc import MixinCD, ParentCD, ShortcutCD, TextCD
import db
from tbl_desc import TblDesc, ItemTblDesc
from tbl_view import TblItemTP
from tbl_report_view import TblReportTP

Item_td = TblDesc(db.Item, 'Item', [
    IdCD(),
    TextCD('name', 'Name'),
    TextCD('type', 'Type')  # FIXME: enumeration
], {
    TblReportTP: ['id', 'name', 'type']
}, '+id')

DbFolder_td = ItemTblDesc(db.DbFolder, 'DB Folder', [
    IdCD(),
    IdCD('thumbnail_id', 'Thumbnail ID'),
    IMDateEltCD('date_year', 'Year'),
    IMDateEltCD('date_month', 'Month'),
    IMDateEltCD('date_day', 'Day'),
    IMDateCD('date', 'Date'),
    IntCD('edit_level', 'Edit Level'),
    ChildrenCD('images', 'Images', path_str='DbImage.folder_id')
], {
    TblReportTP: ['date', 'name', 'edit_level'],
}, '-date,+name')

ImageData_td = TblDesc(db.ImageData, ['Image Data'], [
    IdCD(),
    IntCD('sensitivity', ['Sensitivity', 'ISO']),
    IntCD('image_height', ['Height']),
    IntCD('image_width', ['Width'])
], {
    TblReportTP: ['image_width', 'image_height', 'sensitivity']
}, '-sensitivity')  # FIXME: sorter should not be mandatory
ImageData_td._menu_text = 'Image Data'

DbImage_td = ItemTblDesc(db.DbImage, 'DB Image', [
    IdCD(),
    IdCD('folder_id', 'Folder ID'),
    ParentCD('folder', 'Folder', path_str='folder_id->DbFolder'),
    ShortcutCD('folder_date', 'Folder Date', path_str='folder.date'),
    ShortcutCD('folder_name', 'Folder Name', path_str='folder.name'),
    IdCD('data_id', 'Data ID'),
    MixinCD('data', 'Data', path_str='data_id->ImageData')
], {
    TblReportTP: ['folder_date', 'folder_name', 'name']
}, '-folder_date,+folder_name,+name')

FsFolder_td = ItemTblDesc(db.FsFolder, ['FS Folder', 'FsFolder'], [
    IdCD(),
    IMDateEltCD('db_date_year', ['Year']),
    IMDateEltCD('db_date_month', ['Month']),
    IMDateEltCD('db_date_day', ['Day']),
    IMDateCD('db_date', 'DB Date'),
    TextCD('db_name', 'DB Name'),
    IdCD('source_id', 'FS Source ID'),
    IdCD('db_folder_id', 'DB Folder ID'),
    ParentCD('db_folder', 'DB Folder', path_str='db_folder_id->DbFolder'),
    DateTimeCD('last_scan', 'Last Scan'),
    DateTimeCD('last_import_tags', 'Last Tags Import'),
    ChildrenCD('images', 'Images', path_str='FsImage.folder_id')
], {
    TblReportTP: ['db_date', 'db_name', 'name', 'last_scan'],
}, '-db_date,+db_name,+name')


FsImage_td = ItemTblDesc(db.FsImage, 'FS Image', [
    IdCD(),
    IdCD('folder_id', 'Folder ID'),
    ParentCD('folder', 'Folder', path_str='folder_id->FsFolder'),
    ShortcutCD('folder_db_date', 'Folder DB Date', path_str='folder.db_date'),
    ShortcutCD('folder_db_name', 'Folder DB Name', path_str='folder.db_name'),
    ShortcutCD('folder_name', 'Folder FS Name', path_str='folder.name'),
    IdCD('data_id', 'Data ID'),
    MixinCD('data', 'Data', path_str='data_id->ImageData'),
    IdCD('db_image_id', 'DB Image ID'),
    ParentCD('db_image', 'DB Image', path_str='db_image_id->DbImage')
], {
    TblReportTP: ['folder_db_date', 'folder_db_name', 'folder_name', 'name']
}, '-folder_db_date,+folder_db_name,+name')

TblDesc.complete_tbl_descs()

if __name__== '__main__':
    Item_s = repr(Item_td)
    report_vcs = Item_td.viewed_cols(TblReportTP)
    item_vcs = Item_td.viewed_cols(TblItemTP)
    DbFolder_s = repr(DbFolder_td)
    TblDesc.complete_tbl_descs()
    pass
