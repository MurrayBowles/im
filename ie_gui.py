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
import db_gui
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

        # FsTagSource selection
        self.tag_source = db.FsTagSource.find_id(db.session, cfg.ie.tag_source_id)
        if self.tag_source is None:
            cfg.ie.tag_source_id = -1
            tag_source_str = 'no tag source'
        else:
            tag_source_str = 'tag source: %s' % self.tag_source.description
        self.tag_source_ctrl = wx.StaticText(self, -1, tag_source_str)
        self.tag_source_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_edit_tag_source)
        box.Add(self.tag_source_ctrl)

        # FsSource selection
        sources = db.FsSource.all(db.session)
        self.img_source_list_boxAED = db_gui.ListBoxAED(
            self, box, label='import/export source',
            init_list = db.FsSource.all(db.session),
            name_fn=lambda x: x.text(),
            add_fn = self.on_add_source,
            edit_fn = self.on_edit_source,
            del_fn = self.on_del_source
        )

        # import/export selection

        # flags
        def add_flag(text, cfg_attr):
            flag = wx.CheckBox(self, -1, text)
            flag.SetValue(getattr(cfg.ie, cfg_attr))
            flag.Bind(wx.EVT_CHECKBOX, lambda f: on_flag(f, cfg_attr), flag)
            box.Add(flag)
            return flag

        def on_flag(event, cfg_attr):
            setattr(cfg.ie, cfg_attr, event.GetEventObject().GetValue())

        self.import_folder_tags = add_flag('import folder tags', 'import_folder_tags')
        self.import_image_tags = add_flag('import image tags', 'import_image_tags')
        self.import_thumbnails = add_flag('import thumbnails', 'import_thumbnails')
        self.export_image_tags = add_flag('export image tags', 'export_image_tags')

        # action
        self.gc_box = wx.BoxSizer(wx.HORIZONTAL)
        self.gc_button = wx.Button(self, -1, 'Import/Export')
        self.ie_state = IEState.IE_IDLE
        self.gc_button.Bind(wx.EVT_BUTTON, self.on_go_cancel)
        self.gc_box.Add(self.gc_button)

        #self.gc_progress1 = wx.Gauge(self, -1, range = 24)
        #self.gc_progress1.SetValue(12)
        #self.gc_box.Add(self.gc_progress1)

        box.Add(self.gc_box)
        box.SetSizeHints(self)
        self.SetSizer(box)

    def on_edit_tag_source(self, event):
        dialog = TagSourceDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            self.tag_source_id = self.tag_source.id
            cfg.ie.tag_source_id = self.tag_source.id
            self.tag_source_ctrl.SetLabel('tag source: ' + self.tag_source.description)

    def on_add_source(self):
        dialog = SourceAEDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            pass
        return None

    def on_edit_source(self, obj):
        dialog = SourceAEDialog(self, edit_obj=obj)
        if dialog.ShowModal() == wx.ID_OK:
            pass

    def on_del_source(self, obj):
        pass

    def on_edit_img_source(self, event):
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

class SourceAEDialog(wx.Dialog):
    ''' dialog for adding or editing an import/eport source '''

    def __init__(self, *args, **kw):
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

        self.source_name = ''
        self.read_only = False
        self.volume = ''
        self.path = ''

        self.SetTitle('%s Import/Export Source' % ('Add' if self.obj is None else 'Edit'))
        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        # directory
        db_gui.DirCtrl(self, box, select_fn=self.on_dir_selected)

        # name
        db_gui.AttrTextCtrl(self, box, 'name', self, 'source_name')

        # TODO: tag source

        # read-only
        db_gui.AttrCheckBox(self, box, 'read-only', self, 'read_only')

        # dialog buttons
        db_gui.DialogButtons(self, box, self.on_ok, ok_label=ok_label, cancel_label=cancel_label)

        self.SetSizer(box)
        box.RecalcSizes()
        box.Layout()

    def on_dir_selected(self, path):
        volume = util.volume_label(path)
        if len(volume) == 0:
            volume, path = os.path.splitdrive(path)
        else:
            path = os.path.splitdrive(path)[1]
        self.volume = volume
        self.path = path

    def on_ok(self):
        # copy values to caller
        pass

class TagSourceDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.cur_tag_source = getattr(args[0], 'tag_source')
        self.parent = args[0]
        self.cur_tag_sel = -1
        self.names = []
        self.sources = db.session.query(db.FsTagSource).all()
        for x in range(len(self.sources)):
            self.names.append(self.sources[x].description)
            if self.sources[x] == self.cur_tag_source:
                self.cur_tag_sel = x

        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        self.list_box = wx.ListBox(self, choices=self.names)
        if self.cur_tag_sel != -1:
            self.list_box.SetSelection(self.cur_tag_sel)
        self.list_box.Bind(wx.EVT_LISTBOX, self.on_selection)

        add_box = wx.BoxSizer(wx.HORIZONTAL)
        add_box.Add(wx.StaticText(self, -1, 'add '))
        self.text_box = wx.TextCtrl(self, size=(100,20), style=wx.TE_PROCESS_ENTER)
        self.text_box.Bind(wx.EVT_TEXT_ENTER, self.on_add_enter)
        add_box.Add(self.text_box)
        box.Add(add_box)

        button_box = wx.BoxSizer(wx.HORIZONTAL)
        cancel_button = wx.Button(self, id=wx.ID_CANCEL, label='Close')
        button_box.Add(cancel_button)
        delete_button = wx.Button(self, label='Delete')
        delete_button.Bind(wx.EVT_BUTTON, self.on_delete_button)
        button_box.Add(delete_button)
        self.set_button = wx.Button(self, id=wx.ID_OK, label='Set')
        self.set_button.Bind(wx.EVT_BUTTON, self.on_set_button)
        if self.cur_tag_source is None:
            self.set_button.Disable()
        button_box.Add(self.set_button)

        # box.Add(desc_box)
        box.Add(self.list_box)
        box.Add(add_box)
        box.Add(button_box)

        self.SetSizer(box)
        # self.SetSize((300,300))
        self.SetTitle('Edit Tag Source')

    def on_selection(self, event):
        self.cur_tag_sel = self.list_box.GetSelection()
        self.cur_tag_source = self.sources[self.cur_tag_sel]
        self.list_box.Layout()
        self.set_button.Enable()

    def on_add_enter(self, event):
        description = self.text_box.GetLineText(0)
        tag_source = db.FsTagSource.add(db.session, description)
        self.cur_tag_source = tag_source
        db.session.commit()
        self.sources.append(tag_source)
        self.names.append(description)
        self.list_box.Append(description)
        self.list_box.SetSelection(len(self.names) - 1)
        self.cur_tag_sel = len(self.names) - 1
        self.text_box.SetValue('')
        self.set_button.Enable()

    def on_delete_button(self, event):
        self.list_box.Delete(self.cur_tag_sel)
        self.names.pop(self.cur_tag_sel)
        self.sources.pop(self.cur_tag_sel)
        self.cur_tag_source = None
        self.cur_tag_sel = -1
        self.set_button.Disable()

    def on_set_button(self, event):
        if self.cur_tag_source is not None:
            setattr(self.parent, 'tag_source', self.cur_tag_source)
        event.Skip()


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

