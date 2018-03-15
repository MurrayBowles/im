""" import/export GUI """

import logging
import os
import wx
from wx.lib.pubsub import pub

import db
import gui_wrap
from cfg import cfg
from ie_cfg import *
from ie_db import IETask2
import util

class IEState(Enum):

    IE_IDLE = 0,
    IE_GOING = 1,
    IE_CANCELLING = 2

source_type_map = {
    db.FsSourceType.DIR:    'directories',
    db.FsSourceType.FILE:   'files',
    db.FsSourceType.WEB:    '(error)'
}

class ImportExportTab(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        box = wx.BoxSizer(wx.VERTICAL)
        self.top_box = box
        self.source = None
        self.import_mode = ImportMode.SET
        self.paths = None

        self.accessible_source = False      # accessible_source_box is being displayed
        self.fs_source = False              # fs_source_box is being displayed
        self.selected_fs_source = False     # dir_ctrl is being displayed

        # FsSource selection
        FsSourceCtrl(self, box, change_fn = self.on_source_changed)
        
        # accessible_source_box gets inserted here
        self.accessible_source_box_idx = 1

        self.fix_display()
        box.SetSizeHints(self)
        self.SetSizer(box)
        self.Fit()

    def hide_box_item(self, box, item_idx):
        box.Hide(item_idx)
        box.Remove(item_idx)
        
    def add_accessible_source_box(self):
        self.accessible_source_box = wx.BoxSizer(wx.VERTICAL)
        
        # fs_source box gets inserted here
        self.fs_source_box_idx = 0  # in accessible_source_box
        
        # flags
        self.import_folder_tags = gui_wrap.AttrCheckBox(self, self.accessible_source_box,
            'import folder tags', cfg.ie, 'import_folder_tags')
        self.import_image_tags = gui_wrap.AttrCheckBox(self, self.accessible_source_box,
            'import image tags', cfg.ie, 'import_image_tags')
        self.import_thumbnails = gui_wrap.AttrCheckBox(self, self.accessible_source_box,
            'import thumbnails', cfg.ie, 'import_thumbnails')
        self.export_image_tags = gui_wrap.AttrCheckBox(self, self.accessible_source_box,
            'export image tags', cfg.ie, 'export_image_tags')

        # action
        self.gc_box = wx.BoxSizer(wx.HORIZONTAL)
        self.gc_button = wx.Button(self, -1, 'Import/Export')
        self.ie_state = IEState.IE_IDLE
        self.gc_button.Bind(wx.EVT_BUTTON, self.on_go_cancel)
        self.gc_box.Add(self.gc_button)

        # progress string
        self.progress = gui_wrap.StaticText(self, self.gc_box, '', size=(200, 20))
        # FIXME: should auto-resize with the text

        self.accessible_source_box.Add(self.gc_box)
        
        self.top_box.Insert(self.accessible_source_box_idx, self.accessible_source_box)

    def del_accessible_source_box(self):
        self.hide_box_item(self.top_box, self.accessible_source_box_idx)

    def add_fs_source_box(self):
        self.fs_source_box = wx.BoxSizer(wx.VERTICAL)
        self.fs_source_box_idx = 0  # in accessible_source_box

        # all directories/files vs selected directories/files
        what = source_type_map[self.source.source_type]
        self.select_radio = gui_wrap.RadioButton(
            self, self.fs_source_box,
            choices=['All ' + what, 'Some ' + what],
            change_fn=self.on_select_radio)

        # directory/file selection DirCtrl gets inserted here when self.selected_fs_source
        self.dir_ctrl_sizer_idx = 1  # in fs_source_box

        self.accessible_source_box.Insert(self.fs_source_box_idx, self.fs_source_box)

    def del_fs_source_box(self):
        self.hide_box_item(self.accessible_source_box, self.fs_source_box_idx)

    def add_dir_ctrl(self):
        self.paths = []
        path = self.source.win_path()
        self.dir_ctrl = gui_wrap.DirCtrl(
            self, self.fs_source_box, sizer_idx=self.dir_ctrl_sizer_idx,
            init_path=path, select_fn=self.on_select_paths,
            style=(
                wx.DIRCTRL_MULTIPLE |
                (wx.DIRCTRL_DIR_ONLY if self.source.source_type == db.FsSourceType.DIR else 0)))

    def del_dir_ctrl(self):
        # self.paths = [self.source.win_path()]
        self.hide_box_item(self.fs_source_box, self.dir_ctrl_sizer_idx)

    def fix_display(self):
        """ show/hide add/remove display items depending on state """
        new_accessible_source = self.source != None and self.source.accessible()
        new_fs_source = (new_accessible_source and
            self.source.source_type != db.FsSourceType.WEB)
        new_selected_fs_source = (new_fs_source and
            self.import_mode == ImportMode.SEL)

        changed = False
        if new_accessible_source and not self.accessible_source:
            self.add_accessible_source_box()
            changed = True
        if new_fs_source and not self.fs_source:
            self.add_fs_source_box()
            changed = True
        if new_selected_fs_source and not self.selected_fs_source:
            self.add_dir_ctrl()
            changed = True
        if not new_selected_fs_source and self.selected_fs_source:
            self.del_dir_ctrl()
            changed = True
        if not new_fs_source and self.fs_source:
            self.del_fs_source_box()
            changed = True
        if not new_accessible_source and self.accessible_source:
            self.del_accessible_source_box()
            changed = True

        if changed:
            self.accessible_source = new_accessible_source
            self.fs_source = new_fs_source
            self.selected_fs_source = new_selected_fs_source
            self.Layout()
            self.Fit()

    def on_source_changed(self, obj):
        if obj is not None and not obj.accessible():
            # obj.volume is not mounted
            obj = None
        self.source = obj
        if obj is not None:
            if self.import_mode == ImportMode.SEL:
                self.import_mode = ImportMode.SET
            self.paths = [self.source.win_path()]
            self.fix_select_radio()
        self.fix_display()

    def fix_select_radio(self):
        if self.fs_source:
            self.select_radio.set_selection(0)  # All <what>
            what = source_type_map[self.source.source_type]
            self.select_radio.set_item_label(0, 'All ' + what)
            self.select_radio.set_item_label(1, 'Selected ' + what)

    def on_select_radio(self, value):
        import_mode = ImportMode(value)
        self.import_mode = import_mode
        self.fix_display()

    def on_select_paths(self, paths):
        self.paths = paths

    def on_go_cancel(self, event):
        cfg.save()

        if self.ie_state == IEState.IE_IDLE:
            logging.info('import/export begun')
            self.ie_state = IEState.IE_GOING
            self.gc_button.SetLabel('Stop')

            # status messages
            pub.subscribe(self.on_ie_begun, 'ie.sts.begun')
            pub.subscribe(self.on_ie_import_thumbnails, 'ie.sts.import thumbnails')
            pub.subscribe(self.on_ie_imported_thumbnails, 'ie.sts.imported thumbnails')
            pub.subscribe(self.on_ie_import_tags, 'ie.sts.import tags')
            pub.subscribe(self.on_ie_imported_tags, 'ie.sts.imported tags')
            pub.subscribe(self.on_ie_import_webpage, 'ie.sts.import webpage')
            pub.subscribe(self.on_ie_imported_webpage, 'ie.sts.imported webpage')
            pub.subscribe(self.on_ie_folder_done, 'ie.sts.folder done')
            pub.subscribe(self.on_ie_done, 'ie.sts.done')

            self.ie_cmd = IETask(
                slicer=slicer, session=db.session,
                ie_cfg=cfg.ie, fs_source=self.source,
                import_mode=self.import_mode, paths=self.paths)
            self.start()
            pass
        elif self.ie_state == IEState.IE_GOING:
            logging.info('import/export stopping')
            self.ie_state = IEState.IE_CANCELLING
            self.gc_button.Disable()
            self.ie_cmd.cancel()

    def on_progress(self):
        self.progress.set_text('  ' + self.progress_text)
        pass

    # status message handlers

    def on_ie_begun(self, data):
        self.worklist = data
        self.num_folders = len(data)
        self.cur_folders = 0
        self.progress_text = '%u/%u folders' % (self.cur_folders, self.num_folders)
        self.on_progress()

    def on_ie_import_thumbnails(self, data):
        self.num_thumbnails = data
        self.cur_thumbnails = 0
        self.progress_text = '%u/%u folders, %u/%u thumbnails' % (
            self.cur_folders, self.num_folders, self.cur_thumbnails, self.num_thumbnails)
        self.on_progress()

    def on_ie_imported_thumbnails(self, data):
        self.cur_thumbnails +=  data
        self.progress_text = '%u/%u folders, %u/%u thumbnails' % (
            self.cur_folders, self.num_folders, self.cur_thumbnails, self.num_thumbnails)
        self.on_progress()

    def on_ie_import_tags(self, data):
        self.num_tags = data
        self.cur_tags = 0
        self.progress_text = '%u/%u folders, %u/%u EXIFs' % (
            self.cur_folders, self.num_folders, self.cur_tags, self.num_tags)
        self.on_progress()

    def on_ie_imported_tags(self, data):
        self.cur_tags += data
        self.progress_text = '%u/%u folders, %u/%u EXIFs' % (
            self.cur_folders, self.num_folders, self.cur_tags, self.num_tags)
        self.on_progress()

    def on_ie_import_webpage(self, data):
        self.cur_webpages = 0

    def on_ie_imported_webpage(self, data):
        self.cur_webpages += data
        self.progress_text = '%u/%u folders, %u webpages' % (
            self.cur_folders, self.num_folders, self.cur_webpages)
        self.on_progress()

    def on_ie_folder_done(self, data):
        self.cur_folders += 1
        self.progress_text = '%u/%u folders' % (self.cur_folders, self.num_folders)
        self.on_progress()

    def on_ie_done(self, data):
        cancelled = data
        logging.info('import/export %s', 'cancel_seen' if cancelled else 'done')
        self.progress_text = ''
        self.on_progress()
        self.ie_state = IEState.IE_IDLE
        self.gc_button.SetLabel('Import/Export')
        self.gc_button.Enable()
        self.Layout()
        pass


class FsSourceCtrl:
    def __init__(
            self, parent, sizer,
            size = gui_wrap.default_box,
            label = 'Import/Export Source',
            change_fn = None
    ):
        self.parent = parent
        self.obj = None
        self.change_fn = change_fn

        def source_text(source):
            t = source.live_text()
            if not source.accessible():
                t = '(' + t + ')'
            return t

        sources = db.FsSource.all(db.session)
        self.list_box = gui_wrap.ListBoxAED(
            self.parent, sizer, label='import/export source',
            init_list = sources,
            name_fn=lambda x: source_text(x),
            add_fn = self.on_add,
            edit_fn = self.on_edit,
            del_fn = self.on_del,
            select_fn = self.on_select
        )
        # TODO: ListCtrl? then you could grey the unmounted items

    def _set_obj(self, obj):
        if obj is not self.obj:
            self.obj = obj
            if self.change_fn is not None:
                self.change_fn(obj)

    def selection_accessible(self):
        return self.obj is not none and self.obj.accessible()

    def on_select(self, obj):
        self._set_obj(obj)
        return obj

    def on_add(self):
        dialog = FsSourceAEDialog(self.parent)
        res = dialog.ShowModal()
        if res == wx.ID_OK:
            obj = db.FsSource.add(
                db.session, dialog.volume, dialog.path,
                dialog.source_type, dialog.read_only, dialog.tag_source)
            db.session.commit()
        else:
            obj = None
        dialog.Destroy()
        return obj

    def on_edit(self, obj):
        dialog = FsSourceAEDialog(self.parent, edit_obj=obj)
        res = dialog.ShowModal()
        if res == wx.ID_OK:
            obj.volume = dialog.volume
            obj.path = dialog.path
            obj.source_type = dialog.source_type
            obj.read_only = dialog.read_only
            db.session.commit()
        dialog.Destroy()

    def on_del(self, obj):
        db.session.delete(obj)


class FsSourceAEDialog(wx.Dialog):
    """ dialog for adding or editing an import/export source
        collects source_name, readonly, volume, path
    """

    def __init__(self, *args, **kw):

        # the presence of edit_obj indicates this is an edit, not an add dialog
        if 'edit_obj' in kw:
            self.obj = kw['edit_obj']
            init_tag_source_id = (
                self.obj.tag_source.id if self.obj.tag_source is not None else -1)
            self.volume = self.obj.volume
            self.path = self.obj.path
            self.read_only = self.obj.readonly
            kw.pop('edit_obj')
            ok_label = 'Set'
        else:
            self.obj = None
            init_tag_source_id = -1
            ok_label = 'Add'
            self.volume = ''
            self.path = ''
            self.read_only = False
        cancel_label = 'Cancel'

        super().__init__(*args, **kw)

        self.parent = args[0]

        self.source_name = ''
        self.tag_source = None
        self.source_type = db.FsSourceType.DIR

        self.SetTitle('%s Import/Export Source' % ('Add' if self.obj is None else 'Edit'))
        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        types = {
            db.FsSourceType.DIR:   'set of directories',
            db.FsSourceType.FILE:  'set of files',
            db.FsSourceType.WEB:   'web site'
        }

        if self.obj  is None: # Add
            # source type
            gui_wrap.RadioButton(
                self, box, label='source type: ', choices=list(types.values()),
                change_fn=self.on_source_type_changed)

            # directory
            self.dir_ctrl = gui_wrap.DirCtrl(
                self, box, select_fn=self.on_dir_selected, style = wx.DIRCTRL_DIR_ONLY)

            # URL
            self.text_ctrl = gui_wrap.TextCtrl(
                self, box, 'URL', size = (300, 20), change_fn = self.on_text_changed)
            # self.text_ctrl.set_hidden(True)
        else: # Edit
            gui_wrap.StaticText(self, box, 'source type: ' + types[self.obj.source_type])
            gui_wrap.StaticText(self, box, 'source: ' + self.obj.text())

        # name
        gui_wrap.AttrTextCtrl(self, box, 'name', self, 'source_name')

        # tag source
        FsTagSourceCtrl(
            self, box, change_fn = self.on_tag_source_changed, init_id=init_tag_source_id)

        # read-only
        gui_wrap.AttrCheckBox(self, box, 'read only', self, 'read_only')

        # OK/CANCEL buttons
        self.dialog_buttons = gui_wrap.DialogButtons(
            self, box, ok_label=ok_label, cancel_label=cancel_label,
            ok_disabled=self.obj is None)

        self.SetSizer(box)
        self.Fit()

    def on_source_type_changed(self, value):
        self.source_type = [
            db.FsSourceType.DIR,
            db.FsSourceType.FILE,
            db.FsSourceType.WEB
        ][value]
        # self.dir_ctrl.set_hidden(self.source_type == db.FsSource.WEB)
        # self.text_ctrl.set_hidden(self.source_type != db.FsSource.WEB)
        self.Layout()

    def _fix_dialog_buttons(self):
        self.dialog_buttons.set_ok_enabled(
            self.tag_source is not None and self.path is not None)

    def on_dir_selected(self, paths):
        path = paths[0]
        volume = util.volume_label(path)
        if len(volume) == 0:
            volume, path = os.path.splitdrive(path)
        else:
            path = os.path.splitdrive(path)[1]
        self.volume = volume
        self.path = path
        self._fix_dialog_buttons()

    def on_text_changed(self, text):
        # this happens on every keystroke, so text can be an invalid URL at any point
        if text.find(':') != -1:
            self.volume, self.path = text.split(':', 1)
            self.volume += ':'
        else:
            self.volume = None
            self.path = text
        self._fix_dialog_buttons()

    def on_tag_source_changed(self, obj):
        self.tag_source = obj
        self._fix_dialog_buttons()


class FsTagSourceCtrl:
    def __init__(
            self, parent, sizer,
            size = gui_wrap.default_box,
            init_id = None,
            label = 'Tag Source',
            change_fn = None
    ):
        self.parent = parent
        self.obj = None
        self.change_fn = change_fn

        tag_sources = db.session.query(db.FsTagSource).all()
        self.list_box = gui_wrap.ListBoxAED(
            self.parent, sizer, label=label,
            init_list=tag_sources, init_id=init_id,
            name_fn=lambda x: x.description,
            add_fn=self.on_add,
            edit_fn=self.on_edit,
            del_fn=self.on_del,
            select_fn=self.on_select)

    def _set_obj(self, obj):
        if obj is not self.obj:
            self.obj = obj
            if self.change_fn is not None:
                self.change_fn(obj)

    def on_select(self, obj):
        self._set_obj(obj)
        return obj

    def on_add(self):
        dialog = FsTagSourceAEDialog(self.parent)
        res = dialog.ShowModal()
        if res == wx.ID_OK:
            obj = db.FsTagSource.add(db.session, dialog.description)
            db.session.commit()
        else:
            obj = None
        dialog.Destroy()
        return obj

    def on_edit(self, obj):
        dialog = FsTagSourceAEDialog(self.parent, edit_obj=obj)
        res = dialog.ShowModal()
        if res == wx.ID_OK:
            obj.description = dialog.description
            db.session.commit()
        dialog.Destroy()

    def on_del(self, obj):
        db.session.delete(obj)


class FsTagSourceAEDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        # the presence of edit_obj indicates this is an edit, not an add dialog
        if 'edit_obj' in kw:
            self.obj = kw['edit_obj']
            kw.pop('edit_obj')
            ok_label = 'Set'
        else:
            self.obj = None
            ok_label = 'Add'
        cancel_label = 'Cancel'

        super().__init__(*args, **kw)

        self.parent = args[0]

        self.description = ''

        self.SetTitle('%s Import/Export Tag Source' % ('Add' if self.obj is None else 'Edit'))
        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        # description
        gui_wrap.AttrTextCtrl(self, box, 'description', self, 'description', change_fn = self.on_change)

        # TODO: view tag mappings if EDIT

        # dialog buttons
        self.dialog_buttons = gui_wrap.DialogButtons(
            self, box, ok_label=ok_label, cancel_label=cancel_label,
            ok_disabled=self.obj is None)

        self.SetSizer(box)
        self.Fit()

    def on_change(self, text):
        self.dialog_buttons.set_ok_enabled(text != '')


