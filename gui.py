''' top-level GUI '''

import logging
import wx
import wx.aui
from wx.lib.pubsub import pub

from cfg import cfg
import db
from ie_gui import ImportExportTab
from tags_gui import TagsTab

from task import Task
import time
from wx_task import WxTask
from test_task import TestTask

class MyTask(Task):
    def __init__(self):
        super().__init__()
        self.queue(self.first, '1')

    def first(self, data):
        print('first ' + data)
        while not self.overtime():
            print('time')
            time.sleep(.05)
        print('overtime!')
        self.queue(self.second, '2')

    def second(self, data):
        print('second ' + data)
        while not self.cancelled():
            print('uncancelled')
            self.cancel()
        print('cancelled')
        self.spawn(self.third, '3')

    def third(self, data):
        print('third ' + data)
        print("i'm in another thread")
        if self.cancelled():
            print("i've been cancelled")
        self.queue(self.fourth, '4')

    def fourth(self, data):
        print('fourth ' + data)

class WxMyTask(WxTask, MyTask):
    pass

class TestMyTask(TestTask, MyTask):
    pass

class GuiApp(wx.App):

    def OnInit(self):
        self.SetAppName('ImageManagement')
        cfg.restore()
        frame = GuiTop()
        frame.Show()
        self.SetTopWindow(frame)

        # logging
        handler = logging.FileHandler(
            wx.StandardPaths.Get().GetUserDataDir() + '\\im-log', 'w')
        handler.setLevel(logging.DEBUG)
        format = '%(thread)5d  %(module)-8s %(levelname)-8s %(message)s'
        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.info('log file started')

        WxMyTask()

        return True

class GuiTop(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(
            self, None, -1, 'Image Manager', pos=cfg.gui.pos, size=cfg.gui.size)
        self.Bind(wx.EVT_MOVE, self.on_moved)
        self.Bind(wx.EVT_SIZE, self.on_sized)

        # menu bar
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu();
        file_menu.Append(wx.NewId(), 'Settings', 'Edit settings')
        exit = file_menu.Append(wx.NewId(), 'Exit', 'Exit app')
        self.Bind(wx.EVT_MENU, self.on_exit, exit)
        menu_bar.Append(file_menu, 'File')
        self.SetMenuBar(menu_bar)

        # panel
        panel = wx.Panel(self, -1)

        # notebook
        notebook = wx.aui.AuiNotebook(panel)
        ie_tab = ImportExportTab(notebook)
        notebook.AddPage(ie_tab, 'Import/Export')
        tags_tab = TagsTab(notebook)
        notebook.AddPage(tags_tab, 'Tags')

        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sizer)

        # status bar
        self.status_bar = self.CreateStatusBar()
        pub.subscribe(self.on_set_status, 'top.status')

    def on_moved(self, data):
        cfg.gui.pos = data.GetPosition()

    def on_sized(self, data):
        cfg.gui.size = data.GetSize()

    def on_set_status(self, data):
        logging.info('status := %s', data)
        self.status_bar.SetStatusText(data)

    def on_exit(self, event):
        self.Close()

def gui_test():
    TestMyTask()
    app = GuiApp(False)
    app.MainLoop()
    cfg.save()

if __name__=='__main__':
    db.open_preloaded_mem_db()
    gui_test()
