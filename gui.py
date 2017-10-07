import wx
from ie_gui import *
from tags_gui import *

class GuiApp(wx.App):

    def OnInit(self):
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
        notebook = wx.Notebook(panel)
        ie_tab = ImportExportTab(notebook)
        notebook.AddPage(ie_tab, 'Import/Export')
        tags_tab = TagsTab(notebook)
        notebook.AddPage(tags_tab, 'Tags')
        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sizer)

        # status bar
        status_bar = self.CreateStatusBar()

    def on_exit(self, event):
        self.Close()

def gui_test():
    app = GuiApp(False)
    app.MainLoop()