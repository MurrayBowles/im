''' import/export GUI '''

import copy
import logging
import os
import ps
from wx.lib.pubsub import pub
from threading import Thread
import time
import wx
from wx.lib.pubsub import pub

import db
import gui_wrap
from cfg import cfg
from ie_cfg import *
from ie_db import IECmd
import util

class IEState(Enum):

    IE_IDLE = 0,
    IE_GOING = 1,
    IE_CANCELLING = 2

source_type_map = { 1: 'directories', 2: 'files' }

class ImportExportTab(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        box = wx.BoxSizer(wx.VERTICAL)
        self.top_box = box
        self.source = None
        self.import_mode = ImportMode.SET
        self.paths = None

        # FsSource selection
        FsSourceCtrl(self, box, change_fn = self.on_source_changed)

        self.source_actions_box = wx.BoxSizer(wx.VERTICAL)

        # all directories/files vs selected directories/files
        self.select_radio = gui_wrap.RadioButton(
            self, self.source_actions_box, choices=['All', 'Some'], change_fn = self.on_select_radio)

        # directory/file selection goes here
        self.dir_ctrl_sizer_idx = 1 # in source_actions_box
        self.showing_dir_ctrl = False

        # flags
        self.import_folder_tags = gui_wrap.AttrCheckBox(
            self, self.source_actions_box, 'import folder tags', cfg.ie, 'import_folder_tags')
        self.import_image_tags = gui_wrap.AttrCheckBox(
            self, self.source_actions_box, 'import image tags', cfg.ie, 'import_image_tags')
        self.import_thumbnails = gui_wrap.AttrCheckBox(
            self, self.source_actions_box, 'import thumbnails', cfg.ie, 'import_thumbnails')
        self.export_image_tags = gui_wrap.AttrCheckBox(
            self, self.source_actions_box, 'export image tags', cfg.ie, 'export_image_tags')

        # action
        self.gc_box = wx.BoxSizer(wx.HORIZONTAL)
        self.gc_button = wx.Button(self, -1, 'Import/Export')
        self.ie_state = IEState.IE_IDLE
        self.gc_button.Bind(wx.EVT_BUTTON, self.on_go_cancel)
        self.gc_box.Add(self.gc_button)

        # progress string
        self.progress = gui_wrap.StaticText(self, self.gc_box, '', size=(200,20))
        # FIXME: should auto-resize with the text

        self.source_actions_box.Add(self.gc_box)
        self._fix_source_actions()
        box.Add(self.source_actions_box)

        box.SetSizeHints(self)
        self.SetSizer(box)
        self.Fit()

    def _fix_source_actions(self):
        show = self.source is not None
        if show:
            self.fix_select_radio()
        self.source_actions_box.ShowItems(show)

    def on_source_changed(self, obj):
        if obj is not None and util.win_path(obj.volume, obj.path) is None:
            # obj.volume is not mounted
            obj = None
        self.source = obj
        if obj is not None:
            if self.import_mode == ImportMode.SEL:
                self.import_mode = ImportMode.SET
                self.fix_dir_ctrl()
            self.paths = [self.source.win_path()]
            self.fix_select_radio()
            self.fix_dir_ctrl()
        self._fix_source_actions()
        self.Layout()

    def fix_select_radio(self):
        self.select_radio.set_selection(0)  # All <what>
        what = source_type_map[self.source.source_type]
        self.select_radio.set_item_label(0, 'All ' + what)
        self.select_radio.set_item_label(1, 'Selected ' + what)
        pass

    def on_select_radio(self, value):
        import_mode = ImportMode(value)
        self.import_mode = import_mode
        self.fix_dir_ctrl()
        self.Fit()
        self.Layout()

    def fix_dir_ctrl(self):
        show_dir_ctrl = self.source is not None and self.import_mode == ImportMode.SEL
        if show_dir_ctrl != self.showing_dir_ctrl:
            if show_dir_ctrl:
                self.paths = []
                path = self.source.win_path()
                self.dir_ctrl = gui_wrap.DirCtrl(
                    self, self.source_actions_box, sizer_idx=self.dir_ctrl_sizer_idx,
                    init_path=path, select_fn=self.on_select_paths,
                    style=(
                        wx.DIRCTRL_MULTIPLE |
                        (wx.DIRCTRL_DIR_ONLY if self.source.source_type == db.FsSourceType.DIR else 0)))
            else:
                # FIXME: not quite sure how many of the lines below are necessary
                # if the wxPython docs were correct, just a Remove and a Layout would suffice,
                # but (1) a Layout on WHAT and (2) they don't
                self.source_actions_box.Hide(self.dir_ctrl_sizer_idx)
                self.source_actions_box.Remove(self.dir_ctrl_sizer_idx)
                self.paths = [self.source.win_path()]
            self.showing_dir_ctrl = show_dir_ctrl
            self.source_actions_box.Layout()
            self.Fit()
            self.Layout()

    def on_select_paths(self, paths):
        self.paths = paths

    def on_go_cancel(self, event):
        cfg.save()

        if self.ie_state == IEState.IE_IDLE:
            logging.info('import/export begun')
            self.ie_state = IEState.IE_GOING
            self.gc_button.SetLabel('Stop')

            pub.subscribe(self.on_ie_begun, 'ie.begun')
            pub.subscribe(self.on_ie_import_thumbnails, 'ie.import thumbnails')
            pub.subscribe(self.on_ie_imported_thumbnails, 'ie.imported thumbnails')
            pub.subscribe(self.on_ie_import_tags, 'ie.import tags')
            pub.subscribe(self.on_ie_imported_tags, 'ie.imported tags')
            pub.subscribe(self.on_ie_background_done, 'ie.background done')
            pub.subscribe(self.on_ie_folder_done, 'ie.folder done')
            pub.subscribe(self.on_ie_done, 'ie.done')

            self.ie_cmd = GuiIECmd(self.import_mode, self.source, self.paths)
        elif self.ie_state == IEState.IE_GOING:
            logging.info('import/export stopping')
            self.ie_state = IEState.IE_CANCELLING
            self.gc_button.Disable()
            self.ie_cmd.cancel()

    def on_progress(self):
        self.progress.set_text('  ' + self.progress_text)
        pass

    def on_ie_begun(self, data):
        self.worklist = data
        self.num_folders = len(data)
        self.cur_folders = 0
        self.progress_text = '%u/%u folders' % (self.cur_folders, self.num_folders)
        self.on_progress()
        pass

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

    def on_ie_background_done(self, data):
        self.ie_cmd.step_done()

    def on_ie_folder_done(self, data):
        self.cur_folders += 1
        self.progress_text = '%u/%u folders' % (self.cur_folders, self.num_folders)
        self.on_progress()

    def on_ie_done(self, data):
        cancelled = data
        logging.info('import/export ended')
        self.progress_text = ''
        self.on_progress()
        self.ie_state = IEState.IE_IDLE
        self.gc_button.SetLabel('Import/Export')
        self.gc_button.Enable()
        self.Layout()
        pass


class GuiIECmd(IECmd):

    def __init__(self, import_mode, fs_source, paths):

        self.ie_cfg = copy.deepcopy(cfg.ie)
        self.ie_cfg.import_mode = import_mode
        self.ie_cfg.paths = paths
        self.fs_source = fs_source

        super().__init__(db.session, self.ie_cfg, self.fs_source)

    def do_pub(self, msg, data):

        def do_do_pub(msg, data):
            pub.sendMessage(msg, data=data)

        wx.CallAfter(do_do_pub, msg, data=data)
        pass

    def bg_spawn(self):
        GuiIECmdThread(self)

    def bg_done(self):
        self.do_pub('ie.background done', data=None)


class GuiIECmdThread(Thread):

    def __init__(self, cmd):
        self.cmd = cmd
        Thread.__init__(self)
        self.start()  # start the thread

    def run(self):
        self.cmd.bg_proc()


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
            s = ''
            if source.name is not None:
                s = '%s = ' % (source.name)
            if source.volume.endswith(':'):
                v = source.volume + source.path
            else:
                v =  '[%s]' % (source.volume) + source.path
            if util.win_path(source.volume, source.path) is None:
                v = '(' + v + ')'   # TODO: should be greyed, but ListBox won't do that
            s += v
            return s
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
        obj = self.obj
        return obj is not None and util.win_path(obj.volume, obj.path) is not None

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
    ''' dialog for adding or editing an import/export source
        collects source_name, read_only, volume, path
    '''

    def __init__(self, *args, **kw):

        # the presence of edit_obj indicates this is an edit, not an add dialog
        if 'edit_obj' in kw:
            self.obj = kw['edit_obj']
            init_tag_source_id = self.obj.tag_source.id if self.obj.tag_source is not None else -1
            self.volume = self.obj.volume
            self.path = self.obj.path
            kw.pop('edit_obj')
            ok_label = 'Set'
        else:
            self.obj = None
            init_tag_source_id = -1
            ok_label = 'Add'
            self.volume = ''
            self.path = ''
        cancel_label = 'Cancel'

        super().__init__(*args, **kw)

        self.parent = args[0]

        self.source_name = ''
        self.tag_source = None
        self.source_type = db.FsSourceType.DIR # TODO: add an editor
        self.read_only = False

        self.SetTitle('%s Import/Export Source' % ('Add' if self.obj is None else 'Edit'))
        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        if self.obj  is None:  # Add
            # directory
            gui_wrap.DirCtrl(
                self, box, select_fn=self.on_dir_selected, style = wx.DIRCTRL_DIR_ONLY)
        else:                       # Edit
            gui_wrap.StaticText(self, box, 'source: ' + self.obj.text())

        # name
        gui_wrap.AttrTextCtrl(self, box, 'name', self, 'source_name')

        # tag source
        FsTagSourceCtrl(self, box, change_fn = self.on_tag_source_changed, init_id=init_tag_source_id)

        # read-only
        gui_wrap.AttrCheckBox(self, box, 'read-only', self, 'read_only')

        # source type
        gui_wrap.RadioButton(self, box, label = 'source type: ', choices = [
            'set of directories', 'set of files'
        ], change_fn = self.on_source_type_changed)

        # OK/CANCEL buttons
        self.dialog_buttons = gui_wrap.DialogButtons(
            self, box, ok_label=ok_label, cancel_label=cancel_label,
            ok_disabled=self.obj is None)

        self.SetSizer(box)
        self.Fit()

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

    def on_tag_source_changed(self, obj):
        self.tag_source = obj
        self._fix_dialog_buttons()

    def on_source_type_changed(self, value):
        self.source_type = db.FsSourceType.DIR if value == 0 else db.FsSourceType.FILE


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


