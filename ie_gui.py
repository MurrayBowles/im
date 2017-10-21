''' import/export GUI '''

import wx
import os
from enum import Enum
from threading import Thread
from wx.lib.pubsub import pub
import time
import ps
import win32api
from cfg import *
from ie_cfg import *

class IEState(Enum):

    IE_IDLE = 0,
    IE_GOING = 1,
    IE_CANCELLING = 2

class ImportExportTab(wx.Panel):

    source_types = ['directory set', 'directory selection', 'file set', 'file selection']

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        box = wx.BoxSizer(wx.VERTICAL)
        self.top_box = box

        # import/export type
        self.source_types = wx.RadioBox(self, -1, 'source type', choices = SourceType.names())
        self.source_types.SetSelection(cfg.ie.source_type.value)
        self.source_types.Bind(wx.EVT_RADIOBOX, self.on_source_type_set)
        box.Add(self.source_types)

        # source
        # TODO: dir-selection case
        self.source_picker = wx.DirPickerCtrl(self, path = os.getcwd()) # FIXME: size
        self.source_picker.Bind(wx.EVT_DIRPICKER_CHANGED, self.on_source_set)
        box.Add(self.source_picker)

        # flags
        def add_flag(text):
            flag = wx.CheckBox(self, -1, text)
            box.Add(flag)
            return flag
        self.get_thumbs = add_flag('get thumbnails')
        self.check_folder_tags = add_flag('check folder tags')
        self.set_folder_tags = add_flag('set folder tags')
        self.check_image_tags = add_flag('check image tags')
        self.set_image_tags = add_flag('set image tags')

        # action
        self.gc_box = wx.BoxSizer(wx.HORIZONTAL)
        self.gc_button = wx.Button(self, -1, 'Go')
        self.ie_state = IEState.IE_IDLE
        self.gc_button.Bind(wx.EVT_BUTTON, self.on_go_cancel)
        self.gc_box.Add(self.gc_button)

        #self.gc_progress1 = wx.Gauge(self, -1, range = 24)
        #self.gc_progress1.SetValue(12)
        #self.gc_box.Add(self.gc_progress1)

        box.Add(self.gc_box)

        box.SetSizeHints(self)
        self.SetSizer(box)

    def on_source_type_set(self, event):
        cfg.ie.source_type = SourceType(self.source_types.GetSelection())

    def on_source_set(self, event):
        # TODO: dir-selection case
        self.source = self.source_picker.GetPath()
        drive = os.path.splitdrive(self.source)[0]
        try:
            volume_label = win32api.GetVolumeInformation(drive)[0]
        except:
            volume_label = '(unlabelled)'
        ps.set_status(volume_label)

    def on_go_cancel(self, event):
        cfg.save()
        if self.ie_state == IEState.IE_IDLE:
            self.ie_state = IEState.IE_GOING
            self.gc_button.SetLabel('Cancel')
            pub.subscribe(self.on_ie_begun, 'ie.begun')
            pub.subscribe(self.on_ie_step, 'ie.step')
            pub.subscribe(self.on_ie_done, 'ie.done')
            self.ie_thread = IEThread(self)
        elif self.ie_state == IEState.IE_GOING:
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

    def on_ie_done(self):
        self.gc_box.Remove(1)
        self.gc_box.Remove(1)
        self.ie_state = IEState.IE_IDLE
        self.gc_button.SetLabel('Go')
        self.gc_button.Enable()

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
        pub.sendMessage('ie.done')
