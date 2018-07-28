""" tag editing GUI """

import wx
from wx.lib.agw import ultimatelistctrl as ulc

import gui_wrap
from sortedcontainers import SortedKeyList

class Table(ulc.UltimateListCtrl):

    def __init__(self, *pos, **kwd):
        super().__init__(*pos, **kwd)

        self.InsertColumn(0, 'key', width=100)
        self.InsertColumn(1, 'id', width=50)

        self.data = SortedKeyList(key=lambda x: x[0])
        self.next = 0
        self.selection = set() # set of keys

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._selected)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._deselected)

    def _insert(self, key):
        d = (key, self.next)
        self.next += 1

        row = self.data.bisect_left(key)
        self.data.add(d) # TOTO: is there a push?
        self._inserted_row(row)
        pass

    def _delete_key(self, key):
        try:
            row = self.data.bisect_key_left(key)
            self.data.pop(row)
        except:
            return
        self._deleted_row(row)
        pass

    def _delete_row(self, row):
        try:
            self.data.pop(row)
        except:
            return
        self._deleted_row(row)
        pass

    def _modified(self):
        self.SetItemCount(len(self.data))
        self.Refresh()
        pass

    def _inserted_row(self, row):
        self._modified()

    def _deleted_row(self, row):
        # grr this SetItemState shouldn't be necessary:
        self.SetItemState(row, 0, wx.LIST_STATE_SELECTED)
        self._modified()

    def _selected(self, event):
        idx = event.GetIndex()
        d = self.data[idx]
        self.selection.add(d[0])
        pass

    def _deselected(self, event):
        idx = event.GetIndex()
        d = self.data[idx]
        self.selection.remove(d[0])
        pass

    def OnGetItemText(self, row, col):
        try:
            d = self.data[row]
        except:
            return '?'
        if col == 0:
            return d[0]
        elif col == 1:
            return str(d[1])
        else:
            return '?'

    # weird: these methods really don't have defaults!

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
        sizer.Add(h, 1, 0) # wx.EXPAND)

        text_ctrl = gui_wrap.TextCtrl(
            self, sizer, 'insert', enter_fn=self.on_insert)
        self.text_ctrl = text_ctrl

        button = gui_wrap.Button(
            self, sizer, 'delete', self.on_delete)

        ul = Table(self, agwStyle = (
            ulc.ULC_REPORT | ulc.ULC_VRULES | ulc.ULC_HRULES | ulc.ULC_VIRTUAL))
        self.ul = ul
        ul.SetItemCount(0)

        ul._insert('a')
        ul._insert('b')
        ul._insert('c')

        #sizer.Add(ul, 1, wx.EXPAND).SetMinSize(20, 200)
        sizer.Add(ul, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def on_insert(self, key):
        self.ul._insert(key)
        self.text_ctrl.clear()
        pass

    def on_delete(self, evt):
        for key in self.ul.selection:
            self.ul._delete_key(key)
        self.ul.selection.clear()
        pass


