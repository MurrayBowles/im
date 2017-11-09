''' import/export GUI '''

from enum import Enum
import logging
import os
import ps
from threading import Thread
import time
import wx
from wx.lib.pubsub import pub
import wx.lib.agw.multidirdialog as mdd

import db
import gui_wrap
from cfg import cfg
from ie_cfg import *
import util

class IEState(Enum):

    IE_IDLE = 0,
    IE_GOING = 1,
    IE_CANCELLING = 2

class ImportExportTab(wx.Panel):

    # source_types = ['folder set', 'folder selection', 'file set', 'file selection']

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        box = wx.BoxSizer(wx.VERTICAL)
        self.top_box = box
        self.source = None
        self.source_type = SourceType.DIR_SET

        # FsSource selection
        FsSourceCtrl(self, box, change_fn = self.on_source_changed)

        self.source_actions_box = wx.BoxSizer(wx.VERTICAL)

        # select button
        self.select_button = gui_wrap.Button(self, self.source_actions_box, '', self.on_select_button)
        self.select_button.set_hidden(True, )

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

        #self.gc_progress1 = wx.Gauge(self, -1, range = 24)
        #self.gc_progress1.SetValue(12)
        #self.gc_box.Add(self.gc_progress1)

        self.source_actions_box.Add(self.gc_box)
        self._fix_source_actions()
        box.Add(self.source_actions_box)

        box.SetSizeHints(self)
        self.SetSizer(box)
        self.Fit()

    def _fix_source_actions(self):
        self.source_actions_box.ShowItems(self.source is not None)

    def on_set_sel_changed(self, val): # FIXME: unused now
        if self.source is not None:
            if val == 0:
                self.source_type = (
                    SourceType.DIR_SET if self.source.source_type == 1 else SourceType.FILE_SET)
            else:
                self.source_type = (
                    SourceType.DIR_SEL if self.source.source_type == 1 else SourceType.FILE_SEL)

    def on_source_changed(self, obj):
        if obj is not None and util.win_path(obj.volume, obj.path) is None:
            # obj.volume is not mounted
            obj = None
        self.source = obj
        if obj is not None:
            sel_map = { 1: 'Select directories', 2: 'Select files' }
            self.select_button.set_label(sel_map[obj.source_type])
        self._fix_source_actions()
        self.Layout()

    def on_select_button(self, event):
        pass

    def on_go_cancel(self, event):
        cfg.save()
        if self.ie_state == IEState.IE_IDLE:
            logging.info('import/export begun')
            self.ie_state = IEState.IE_GOING
            self.gc_button.SetLabel('Stop')
            pub.subscribe(self.on_ie_begun, 'ie.begun')
            pub.subscribe(self.on_ie_step, 'ie.step')
            pub.subscribe(self.on_ie_ended, 'ie.ended')
            self.ie_thread = IEThread(self)
        elif self.ie_state == IEState.IE_GOING:
            logging.info('import/export stopping')
            self.ie_state = IEState.IE_CANCELLING
            self.gc_button.Disable()

    def on_ie_begun(self, data):
        self.ie_total_steps = data
        self.ie_cur_steps = 0
        self.gc_progress = wx.Gauge(self, -1, range = self.ie_total_steps)
        self.gc_progress.SetValue(self.ie_cur_steps)
        self.gc_box.Add(self.gc_progress)
        self.gc_stats = wx.StaticText(self, -1, '%u/%u' % (self.ie_cur_steps, self.ie_total_steps))
        self.gc_box.Add(self.gc_stats)
        self.top_box.Layout()

    def on_ie_step(self, data):
        self.ie_cur_steps += data
        self.gc_progress.SetValue(self.ie_cur_steps)
        self.gc_stats.SetLabel('%u/%u' % (self.ie_cur_steps, self.ie_total_steps))

    def on_ie_ended(self):
        logging.info('import/export ended')
        self.gc_box.Remove(1)
        self.gc_box.Remove(1)
        self.ie_state = IEState.IE_IDLE
        self.gc_button.SetLabel('Import/Export')
        self.gc_button.Enable()


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
            gui_wrap.DirCtrl(self, box, select_fn=self.on_dir_selected)
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

    def on_dir_selected(self, path):
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


class IEThread(Thread):

    def __init__(self, gui):
        Thread.__init__(self)
        self.gui = gui
        self.dirs_done = 0
        self.dirs_to_do = 23
        self.start()    # start the thread

    def run(self):
        pub.sendMessage('ie.begun', data = self.dirs_to_do)
        for i in range(self.dirs_to_do):
            if self.gui.ie_state == IEState.IE_CANCELLING:
                break
            time.sleep(1)
            pub.sendMessage('ie.step', data = 1)
        pub.sendMessage('ie.ended')

