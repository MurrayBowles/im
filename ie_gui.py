import wx

class ImportExportTab(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        wx.StaticText(self, -1, 'the import/export tab')
