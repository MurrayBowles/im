''' empty-tab GUI '''

import wx

class EmptyTab(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)