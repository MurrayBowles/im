''' contents of a GUI tab '''

from typing import Any, List, Tuple

import wx
import wx.aui as aui
#import wx.lib.agw.aui as aui


class TabbedNotebook(aui.AuiNotebook):
    tab_panel_stacks: List[Any]  # List[TabPanelStack]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tab_panel_stacks = []

    def tab_idx(self, tab_panel_stack):
        return self.tab_panel_stacks.index(tab_panel_stack)

    def remove_tab(self, tab_idx):
        self.RemovePage(tab_idx)
        self.DeletePage(tab_idx)
        self.tab_panel_stacks.pop(tab_idx)


class TabPanel(wx.Panel):
    ''' panel in a TabPanelStack '''
    def __init__(self, tab_panel_stack):  # parent is a TabPanelStack
        super().__init__(tab_panel_stack)
        self.tab_panel_stack = tab_panel_stack
        # at the end of initialization, the subclass should call self.push()

    @classmethod
    def cls_text(cls):  # returns text to display in the tab
        return cls.__name__

    def inst_text(self):  # returns text to display in the tab
        return self.__class__.cls_text()

    def tab_idx(self):
        return self.tab_panel_stack.tab_idx(self)

    def relative_stack(self, pos):
        # pos: -1 add a tab to the left, +1 add a tab to the right; 0 return my_panel's tab
        return self.tab_panel_stack.relative_stack(pos)

    def push(self):
        self.tab_panel_stack.push(self)


class TabPanelStack(wx.Panel):
    ''' stack of panels for a tab '''
    stk: List[TabPanel]
    stk_idx: int  # tab_idx of the TOS (-1 indicates an empty stack)
    sizer: wx.BoxSizer
    notebook: TabbedNotebook

    def __init__(self, notebook: TabbedNotebook, tab_idx):
        super().__init__(notebook)
        self.stk_idx = -1
        self.stk = []
        self.notebook = notebook
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.notebook.tab_panel_stacks.insert(tab_idx, self)
        self.notebook.InsertPage(tab_idx, self, '')
        pass

    def relative_stack(self, pos):
        # pos: -1 add a tab to the left, +1 add a tab to the right; 0 return my_panel's tab
        if pos == 0:
            return self
        else:
            my_idx = self.tab_idx()
            rel_idx = my_idx if pos == -1 else my_idx + 1
            return TabPanelStack(self.notebook, rel_idx)

    def __str__(self):
        return '[' + ', '.join([p.text() for p in self.stk]) + ']'

    def tab_idx(self):
        return self.notebook.tab_idx(self)

    def cur_panel(self) -> TabPanel:
        return None if self.stk_idx == -1 else self.stk[self.stk_idx]

    def panel_list(self) -> List[Tuple[int, str]]:
        ''' return a list of (stk_idx, panel.text()) for each non-current panel in the stack '''
        panels = []
        if len(self.stk) > 1:
            for stk_idx in range(len(self.stk) - 1, -1, -1):
                if stk_idx != self.stk_idx:
                    panels.append((stk_idx, self.stk[stk_idx].inst_text()))
        return panels

    def _mystery_stuff(self):
        cur_panel = self.cur_panel()
        #cur_panel.Layout()
        #cur_panel.Refresh()
        self.Layout()
        #self.Refresh()
        #self.notebook.Layout()
        #Layout()self.notebook.Refresh()
        pass

    def _show_cur_panel(self):
        self.sizer.Show(self.stk_idx)
        cur_panel = self.stk[self.stk_idx]
        self.notebook.SetPageText(self.tab_idx(), cur_panel.inst_text())
        self.notebook.SetSelection(self.tab_idx())
        pass

    def _hide_cur_panel(self):
        self.sizer.Hide(self.stk_idx)

    def _delete_panels(self, down_to):
        ''' Delete panels from TOS down to but not including down_to. '''
        x = len(self.stk)
        while x > down_to + 1:
            panel = self.stk.pop()
            panel.tab_panel_stack = None
            # TODO panel.destroy or something?
            self.sizer.Hide(x)
            x -= 1
        pass

    def push(self, panel: TabPanel):
        tab_idx = self.tab_idx()
        if self.stk_idx != -1:
            self._hide_cur_panel()
            self._delete_panels(self.stk_idx)
        self.sizer.Add(panel, 1, wx.EXPAND)
        self.stk.append(panel)
        self.stk_idx += 1
        self._show_cur_panel()
        self._mystery_stuff()
        pass

    def goto(self, stk_idx):
        tab_idx = self.tab_idx()
        self._hide_cur_panel()
        self.stk_idx = stk_idx
        self._show_cur_panel()
        self._mystery_stuff()
        pass

    def destroy(self):
        self._hide_cur_panel()
        self._delete_panels()
        pass