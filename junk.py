''' unused code fragments '''


class TabStack(object):
    ''' stack of panels for a tab '''
    stack: List[Tuple[wx.Panel, str]]  # panel, tab label
    current: int  # col_idx of the TOS (-1 indicates an empty stack)

    def __init__(self):
        self.current = -1
        self.stack = []

    def cur_panel(self):
        if self.current == -1:
            return None
        else:
            return self.stack[self.current][0]

    def _insert_current_panel(self, notebook, tab_idx):
        panel, text = self.stack[self.current]
        notebook.InsertPage(tab_idx, panel, text)
        #notebook.SetSelection(col_idx + 1)
        notebook.SetSelection(tab_idx)
        #notebook.HidePage(col_idx, True)
        #notebook.HidePage(col_idx, False)
        #panel.Layout()
        #panel.Refresh(eraseBackground=True)
        #panel.Update()
        #notebook.Layout()
        #notebook.Refresh(eraseBackground=True)
        #notebook.Update()
        pass

    def _delete_panels(self, notebook, tab_idx, down_to):
        x = len(self.stack)
        while x > down_to + 1:
            panel, text = self.stack.pop()
            notebook.InsertPage(tab_idx, panel, '')
            notebook.RemovePage(tab_idx)
            notebook.DeletePage(tab_idx)
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

    def goto(self, notebook, tab_idx, stk_idx):
        notebook.RemovePage(tab_idx)
        self.current = stk_idx
        self._insert_current_panel(notebook, tab_idx)

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
