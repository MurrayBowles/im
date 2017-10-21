''' top-level GUI '''

import wx
import wx.aui
from wx.lib.pubsub import pub

from cfg import *
from ie_gui import *
from tags_gui import *

class GuiApp(wx.App):

    def OnInit(self):
        self.SetAppName('ImageManagement')
        cfg.restore()
        frame = GuiTop()
        frame.Show()
        self.SetTopWindow(frame)
        return True

class GuiTop(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, -1, 'Image Manager', size=(1200, 800))

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
        # notebook = wx.Notebook(panel)
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

    def on_set_status(self, data):
        self.status_bar.SetStatusText(data)

    def on_exit(self, event):
        self.Close()

def gui_test():
    app = GuiApp(False)
    app.MainLoop()
    cfg.save()