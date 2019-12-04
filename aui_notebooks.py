import wx
import wx.aui as aui
#import wx.lib.agw.aui as aui

class NbApp(wx.App):

    def OnInit(self):
        frame = NbFrame()
        frame.Show()
        self.SetTopWindow(frame)
        return True

class NbPage(wx.Panel):
    class EmptyTP(wx.Panel):

        def __init__(self, parent):
            super().__init__(parent)


class NbFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(
            self, None, -1, 'NB', pos=(100,100), size=(400,400))

        panel = self.panel = wx.Panel(self, -1)
        notebook = self.notebook = aui.AuiNotebook(panel, style=aui.AUI_NB_CLOSE_ON_ALL_TABS)

        notebook.InsertPage(0, wx.Panel(notebook), 'a')
        notebook.InsertPage(1, wx.Panel(notebook), 'b')

        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sizer)

if __name__== '__main__':
    app = NbApp(False)
    app.MainLoop()