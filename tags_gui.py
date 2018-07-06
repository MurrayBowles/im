""" tag editing GUI """

import wx
from wx.lib.agw import ultimatelistctrl as ulc


class Table(ulc.UltimateListCtrl):

    def __init__(self, *pos, **kwd):
        super().__init__(*pos, **kwd)

        self.InsertColumn(0, 'col0', width=100)
        self.InsertColumn(1, 'col1', width=50)


    def OnGetItemText(self, row, col):
        if row != 0 or col != 0:
            pass
        s = '%d/%d' % (row, col)
        return s

    # weird: these methods don't have defaults!

    def OnGetItemTextColour(self, row, col):
        return None

    def OnGetItemToolTip(self, row, col):
        s = 'tooltip[%d/%d]' % (row, col)
        return s


class TagsTab(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        h = wx.StaticText(self, -1, 'the tags tab')
        sizer.Add(h, 1, wx.EXPAND)

        ul = Table(self, agwStyle = (
            ulc.ULC_REPORT | ulc.ULC_VRULES | ulc.ULC_HRULES | ulc.ULC_VIRTUAL))

        ul.SetItemCount(2)

        sizer.Add(ul, 1, wx.EXPAND)
        self.SetSizer(sizer)