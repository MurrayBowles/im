""" database table viewers """

import jsonpickle
import wx

from tab_panel_gui import TabPanel, TabPanelStack
from tbl_query import TblQuery


class TblTP(TabPanel):
    tbl_query: TblQuery

    def __init__(self, parent: TabPanelStack, tbl_query: TblQuery):
        super().__init__(parent)
        self.tbl_query = tbl_query
        self.tps = parent
        self.notebook = parent.notebook
        # subclasses end initialization by calling self.push()

    def save(self):
        return {
            'subclass': self.__class__.__name__,
            'tbl_query': jsonpickle.encode(self.tbl_query)
        }

    @classmethod
    def restore(cls, tps, saved_panel):
        saved_tbl_query = saved_panel['tbl_query']
        try:
            tbl_query = jsonpickle.decode(saved_tbl_query)
        except Exception as ed:
            pass
        cls(parent=tps, tbl_query=tbl_query)

    @classmethod
    def cls_text(cls):
        return 'Table'

    def inst_text(self):
        return self.tbl_query.tbl_desc.menu_text()


class TblItemTP(TblTP):
    pass



