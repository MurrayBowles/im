""" top-level GUI """

import logging
from typing import Any, List, Tuple
import wx
import wx.aui
from wx.lib.pubsub import pub

from cfg import cfg
import db
from empty_gui import EmptyTab
from ie_gui import ImportExportTab
from tags_gui import TagsTab
from wx_task import WxSlicer

slicer = None # initialized in GuiApp.OnInit()


class GuiApp(wx.App):

    def OnInit(self):
        self.SetAppName('ImageManagement')
        cfg.restore()
        frame = GuiTop()
        frame.Show()
        self.SetTopWindow(frame)

        # pseudo-thread scheduling
        global slicer
        slicer = WxSlicer(num_queues=2, max_slice_ms=100)
        pass

        # logging
        handler = logging.FileHandler(
            wx.StandardPaths.Get().GetUserDataDir() + '\\im-log', 'w')
        #FIXME: this fails if the ImageManagement directory doesn't already exist
        handler.setLevel(logging.DEBUG)
        log_format = '%(thread)5d  %(module)-8s %(levelname)-8s %(message)s'
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.info('log file started')

        return True


class TabStack(object):
    ''' stack of panels for a tab '''
    stack: List[Tuple[wx.Panel, str]]  # panel, tab label
    current: int  # index of the TOS (-1 indicates an empty stack)

    def __init__(self):
        self.current = -1
        self.stack = []

    def cur_panel(self):
        if self.current == -1:
            return None
        else:
            return self.stack[self.current][0]

    def _insert_current_panel(self, notebook, index):
        panel, text = self.stack[self.current]
        notebook.InsertPage(index, panel, text)
        pass

    def _delete_panels(self, notebook, index, down_through):
        x = len(self.stack)
        if x != 0:
            while True:
                self.stack.pop()
                notebook.DeletePage(index)
                if x == down_through:
                    break
                x -= 1
        pass

    def push(self, notebook, index, new_panel, text):
        if self.current != -1:
            notebook.RemovePage(index)
        self._delete_panels(notebook, index, self.current)
        self.stack.append((new_panel, text))
        self.current += 1
        self._insert_current_panel(notebook, index)
        pass

    def back_possible(self):
        return self.current > 0

    def back(self, notebook, index):
        if self.back_possible():
            notebook.RemovePage(index)
            self.current -= 1
            self._insert_current_panel()

    def forward_possible(self):
        return self.current < len(self.stack) - 1

    def forward(self, notebook, index):
        if self.forward_possible:
            notebook.RemovePage(index)
            self.current += 1
            self._insert_current_panel()

    def delete(self, notebook, index):
        notebook.RemovePage(index)
        self._delete_panels(notebook, index, 0)
        pass


class GuiTop(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(
            self, None, -1, 'Image Manager', pos=cfg.gui.pos, size=cfg.gui.size)
        self.Bind(wx.EVT_MOVE, self.on_moved)
        self.Bind(wx.EVT_SIZE, self.on_sized)

        # menu bar
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu();
        file_menu.Append(-1, 'Settings', 'Edit settings')
        exit = file_menu.Append(-1, 'Exit', 'Exit app')
        self.Bind(wx.EVT_MENU, self.on_exit, exit)
        menu_bar.Append(file_menu, 'File')
        self.SetMenuBar(menu_bar)

        # panel
        panel = wx.Panel(self, -1)

        # notebook
        notebook = self.notebook = wx.aui.AuiNotebook(panel, style = wx.aui.AUI_NB_CLOSE_ON_ALL_TABS)

        self.tab_stacks = []    # List[TabStack]

        empty_tab = EmptyTab(notebook)
        self.tab_stacks.append(TabStack())
        self.tab_stacks[0].push(notebook, 0, empty_tab, '+')

        ie_tab = ImportExportTab(notebook)
        self.add_tab(empty_tab, ie_tab, -1, 'Import/Export')

        tags_tab = TagsTab(notebook)
        self.add_tab(ie_tab, tags_tab, 1, 'Tags')

        notebook.Bind(wx.aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.on_tab_right_click)
        notebook.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_tab_close)

        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sizer)

        # status bar
        self.status_bar = self.CreateStatusBar()
        pub.subscribe(self.on_set_status, 'top.status')

    def _tab_index(self, panel):
        for x in range(len(self.tab_stacks)):
            if self.tab_stacks[x].cur_panel() == panel:
                return x
        raise KeyError('panel not found')

    def add_tab(self, my_panel, new_panel, pos, new_text):
        notebook = self.notebook
        my_idx = self._tab_index(my_panel)
        if pos == 0:
            # push new_panel where my_panel currently is
            new_idx = my_idx
        else:
            # insert new_panel in a new tab to the left or right of my_idx
            new_idx = my_idx if pos == -1 else my_idx + 1
            self.tab_stacks.insert(new_idx, TabStack())
        self.tab_stacks[new_idx].push(notebook, new_idx, new_panel, new_text)
        notebook.SetSelection(new_idx)

    def on_moved(self, data):
        cfg.gui.pos = data.GetPosition()

    def on_sized(self, data):
        cfg.gui.size = data.GetSize()

    def on_set_status(self, data):
        logging.info('status := %s', data)
        self.status_bar.SetStatusText(data)

    def on_tab_right_click(self, data):
        # data.Selection is the tab index
        pass

    def on_tab_close(self, data):
        # data.Selection is the tab index
        my_idx = data.Selection
        self.notebook.RemovePage(data.Selection)
        self.notebook.DeletePage(data.Selection)
        pass

    def on_exit(self, event):
        self.Close()

def gui_test():
    app = GuiApp(False)
    app.MainLoop()
    cfg.save()

if __name__== '__main__':
    db.open_preloaded_mem_db()
    gui_test()
