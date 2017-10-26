''' tag editing GUI '''

import wx

class TagsTab(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        wx.StaticText(self, -1, 'the tags tab')
