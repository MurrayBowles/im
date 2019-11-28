""" top-level GUI """

import copy
import logging
from typing import Any, List, Tuple
import wx
import wx.aui
from wx.lib.pubsub import pub

from cfg import cfg
import db
from empty_gui import EmptyTP
from ie_gui import ImportExportTP
from tab_panel_gui import TabbedNotebook, TabPanel, TabPanelStack
from tags_gui import TagsTP
from tbl_desc import TblDesc
from tbl_view import TblTP
import tbl_view_factory
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
        panel = self.panel = wx.Panel(self, -1)

        # notebook
        notebook = self.notebook = TabbedNotebook(
            panel, style = wx.aui.AUI_NB_CLOSE_ON_ALL_TABS)

        tpsA2 = TabPanelStack(notebook, 0)
        empty_tp = EmptyTP(tpsA2)

        tpsB0 = empty_tp.relative_stack(-1)
        ie_tp = ImportExportTP(tpsB0)

        tpsC1 = ie_tp.relative_stack(1)
        ie_tab2 = ImportExportTP(tpsC1)
        tags_tp = TagsTP(tpsC1)

        notebook.Bind(wx.aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.on_tab_right_click)
        notebook.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_tab_close)

        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sizer)

        # status bar
        self.status_bar = self.CreateStatusBar()
        pub.subscribe(self.on_set_status, 'top.status')

    def on_moved(self, data):
        cfg.gui.pos = data.GetPosition()

    def on_sized(self, data):
        cfg.gui.size = data.GetSize()

    def on_set_status(self, data):
        logging.info('status := %s', data)
        self.status_bar.SetStatusText(data)

    def _push_menu(self, tab_idx, pos, fn):
        def lll(obj):
            return lambda event: fn(event, tab_idx, pos, obj)
        menu = wx.Menu()
        choices = (
            [(td.menu_text(), td) for td in TblDesc.objs]
          + [(tp.cls_text(), tp) for tp in TabPanel.__subclasses__()]
        )
        choices.sort(key=lambda c: c[0])
        for x in range(len(choices)):
            c = choices[x]
            if c[1] is EmptyTP or c[1] is TblTP:
                continue
            item = menu.Append(-1, c[0])
            self.Bind(wx.EVT_MENU, lll(c[1]), item)
        return menu

    def on_tab_right_click(self, data):
        # data.Selection is the tab tab_idx

        def add_item(tab_idx, x, text, fn):
            item = menu.Append(-1, text)
            self.Bind(wx.EVT_MENU, lambda event: fn(event, tab_idx, x), item)

        def add_stk_item(tab_idx, stk_idx, text):
            add_item(tab_idx, stk_idx, text, self.on_stk_item_select)

        def add_ins_item(tab_idx, pos, text):
            add_item(tab_idx, pos, text, self.on_ins_item_select)

        def add_push_item(tab_idx, pos, text):
            push_menu = self._push_menu(tab_idx, pos, self.on_push_item_select)
            item = menu.Append(-1, text, push_menu)

        tab_idx = data.Selection
        self.notebook.SetSelection(tab_idx)
        event = data.EventObject
        pos = event.GetPosition()
        cli_pos = self.panel.ScreenToClient(pos)
        tab_panel_stack = self.notebook.tab_panel_stacks[tab_idx]
        if tab_idx == len(self.notebook.tab_panel_stacks) - 1:
            # the right tab is the special '+' tab
            menu = self._push_menu(tab_idx, -1, self.on_push_item_select)
            pass
        else:
            menu = wx.Menu()
            panel_list = tab_panel_stack.panel_list()
            if len(panel_list) > 0:
                for (stk_idx, text) in panel_list:
                    add_stk_item(tab_idx, stk_idx, text)
                menu.AppendSeparator()
            add_push_item(tab_idx, -1, 'insert left')
            add_push_item(tab_idx, 0, 'push')
            add_push_item(tab_idx, 1, 'insert right')
        self.panel.PopupMenu(menu)
        pass

    def on_stk_item_select(self, event, tab_idx, stk_idx):
        tab_panel_stack = self.notebook.tab_panel_stacks[tab_idx]
        tab_panel_stack.goto(stk_idx)
        pass

    def on_push_item_select(self, event, tab_idx, pos, obj):
        add_tps = self.notebook.tab_panel_stacks[tab_idx]
        new_tps = add_tps.relative_stack(pos)
        if isinstance(obj, TblDesc):
            tbl_view_factory.get(new_tps, obj)
        else:
            obj(new_tps)

    def on_std_tab_push_item_select(self, event, tab_idx, pos, obj):
        pass

    def on_tab_close(self, data):
        # data.Selection is the tab tab_idx
        self.notebook.remove_tab(data.Selection)

    def on_exit(self, event):
        self.Close()

def gui_test():
    app = GuiApp(False)
    app.MainLoop()
    cfg.save()

if __name__== '__main__':
    import tbl_descs
    db.open_preloaded_mem_db()
    gui_test()
