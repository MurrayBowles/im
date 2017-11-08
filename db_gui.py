''' classes for wxPython / database interaction '''

from bisect import *
import db
from enum import Enum
import wx

default_box=(200,100)
default_line=(150,20)

class Button:

    def __init__(
        self, parent, sizer,
        label, push_fn
    ):
        self.parent = parent
        self.push_fn = push_fn

        if self.push_fn is push_fn:
            pass

        self.button = wx.Button(parent, label=label)
        sizer.Add(self.button)
        self.button.Bind(wx.EVT_BUTTON, push_fn)

    def set_enabled(self, enabled):
        if enabled:
            self.button.Enable()
        else:
            self.button.Disable()


class DialogButtons:

    def __init__(
        self, parent, sizer, on_ok=None,
        ok_label='Ok', cancel_label='Cancel', ok_disabled=False
    ):
        self.parent  = parent
        self.on_ok_fn = on_ok

        button_box = wx.BoxSizer(wx.HORIZONTAL)
        cancel_button = wx.Button(parent, id=wx.ID_CANCEL, label=cancel_label)
        button_box.Add(cancel_button)
        self.ok_button = wx.Button(parent, id=wx.ID_OK, label=ok_label)
        self.ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        if ok_disabled:
            self.ok_button.Disable()
        self.ok_button.SetDefault() # FIXME: doesn't work
        button_box.Add(self.ok_button)
        sizer.Add(button_box, wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)

    def on_ok(self, event):
        if self.on_ok_fn is not None:
            self.on_ok_fn()
        event.Skip()

    def set_ok_enabled(self, enabled):
        if enabled:
            self.ok_button.Enable()
        else:
            self.ok_button.Disable()


class CheckBox:

    def __init__(
        self, parent, sizer,
        label, init_value=False, on_click=None
    ):
        self.parent = parent
        self.value = init_value
        self.on_click_fn=on_click

        self.check_box = wx.CheckBox(parent, label=label)
        self.check_box.Bind(wx.EVT_CHECKBOX, self.on_click)
        sizer.Add(self.check_box)

    def on_click(self, event):
        self.value = event.GetEventObject().GetValue()
        if self.on_click_fn is not None:
            self.on_click_fn(self.value)

    def set_enabled(self, enabled):
        if enabled:
            self.check_box.Enable()
        else:
            self.check_box.Disable()


class AttrCheckBox(CheckBox):

    def __init__(
        self, parent, sizer,
        label,
        obj, attr, on_click=None
    ):
        self.obj = obj
        self.attr = attr
        self.attr_on_click_fn = on_click

        super().__init__(
            parent, sizer, label, init_value=getattr(obj, attr), on_click=self.attr_on_click)

    def attr_on_click(self, value):
        if self.attr_on_click_fn is not None:
            self.attr_on_click_fn(value)
        setattr(self.obj, self.attr, value)


class DirCtrl:

    def __init__(
        self, parent, sizer,
        size = default_box,
        label = None,
        select_fn = None    # (path) called whenever the selection changes
    ):
        self.parent = parent
        self.label = label
        self.select_fn = select_fn

        self.selection = None

        if label is not None:
            label_text = wx.StaticText(parent, label=label)
            sizer.Add(label_text)
        self.dir_ctrl = wx.GenericDirCtrl(
            parent, style=wx.DIRCTRL_DIR_ONLY, size=size)
        sizer.Add(self.dir_ctrl)
        tree_ctrl = self.dir_ctrl.GetTreeCtrl()
        self.dir_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_select, tree_ctrl)

    def _on_select(self, event):
        path = self.dir_ctrl.GetPath()
        if self.select_fn is not None:
            self.select_fn(path)
        self.selection = path


class ListBox:

    def __init__(
        self, parent, sizer,
        size = default_box,
        id_fn = lambda x: x.id,
        name_fn = lambda x: x.name,
        add_fn = None,      # called to add an item
        select_fn = None,   # called initially, and when the current selection changes
        edit_fn = None,     # called when an item is double-clicked
        label = None,
        init_id = -1,       # object ID to select initially
        init_list = None    # initial list to display
    ):
        self.parent = parent
        self.id_fn = id_fn
        self.name_fn = name_fn
        self.add_fn = add_fn
        self.edit_fn = edit_fn
        self.select_fn = select_fn

        self.selection = None

        if label is not None:
            label_text = wx.StaticText(parent, label=label)
            sizer.Add(label_text)
        if init_list is None:
            init_list = []
        choices, init_sel_idx = self._get_choices(init_id, init_list)
        self.list_box = wx.ListBox(parent, size=size, choices=choices)
        sizer.Add(self.list_box)
        self.list_box.SetSelection(init_sel_idx)
        self.list_box.Bind(wx.EVT_LISTBOX, self._on_select)
        if edit_fn is not None:
            self.list_box.Bind(wx.EVT_LISTBOX_DCLICK, self._on_edit)
        if init_sel_idx != -1:
            self.selection = self.objs[init_sel_idx]
            if self.select_fn:
                self.select_fn(self.selection)

    def _get_choices(self, init_id, init_list):
        # return choices-list, selection-index
        self.objs = init_list
        self.objs.sort(key=lambda x: self.name_fn(x))
        self.names = []
        init_idx = -1
        for x in range(len(self.objs)):
            obj = self.objs[x]
            self.names.append(self.name_fn(obj))
            if self.id_fn(obj) == init_id:
                init_idx = x
        if self.add_fn is not None:
            self.names.append('(click to add)')
        return self.names, init_idx

    def _on_select(self, event): # single-click on an item
        # select the item
        sel_idx = self.list_box.GetSelection()
        if sel_idx < len(self.objs):
            # selecting an existing object
            sel_obj = self.objs[sel_idx]
            if self.select_fn is not None:
                self.select_fn(sel_obj)
        else:
            # adding a new object
            self,add_fn(parent)

    def _on_edit(self, event): # double-click on an item
        # call self.edit_fn on the item
        if self.edit_fn is not None:
            edit_idx = self.list_box.GetSelection()
            if edit_idx < len(self.objs):
                edit_obj = self.objs[edit_idx]
                self.edit_fn(edit_obj)

    def add(self, obj):
        # add <obj> to the list
        name = self.name_fn(obj)
        obj_idx = bisect_left(self.names, name, hi = len(self.objs))
        self.objs.insert(obj_idx, obj)
        self.names.insert(obj_idx, name)
        self.list_box.InsertItems([name], obj_idx)

    def delete(self, obj):
        # delete <obj> from the list
        obj_idx = self.objs.index(obj) # TODO: use bisect?
        self.objs.pop(obj_idx)
        self.names.pop(obj_idx)
        self.list_box.Delete(obj_idx)
        if obj is self.selection:
            if self.select_fn is not None:
                self.select_fn(None)


class ListBoxAED:
    ''' a list box plus ADD, EDIT, DELETE buttons '''

    def __init__(
        self, parent, sizer,
        size = default_box,
        id_fn = lambda x: x.id,
        name_fn = lambda x: x.name,
        select_fn = None,   # called initially, and when the current selection changes
        add_fn = None,      # called to add an object
        edit_fn = None,     # called to edit an object
        del_fn = None,      # called to delete an object
        label = None,
        init_id = -1,       # object ID to select initially
        init_list = None    # initial list to display
    ):
        self.add_fn = add_fn
        self.edit_fn = edit_fn
        self.del_fn = del_fn
        self.select_fn = select_fn

        self.selection = None

        outer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_box = ListBox(
            parent, list_sizer, size=size, label=label,
            init_id=init_id, init_list=init_list,
            id_fn=id_fn, name_fn=name_fn,
            select_fn=self.on_select
        )
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        if add_fn is not None:
            Button(parent, button_sizer, 'Add', self.on_add)
        if edit_fn is not None:
            self.edit_button = Button(parent, button_sizer, 'Edit', self.on_edit)
        if del_fn is not None:
            self.del_button = Button(parent, button_sizer, 'Delete', self.on_del)
        self._fix_buttons()
        outer_sizer.Add(list_sizer)
        outer_sizer.Add(button_sizer)
        sizer.Add(outer_sizer)

    def _fix_buttons(self):
        self.edit_button.set_enabled(self.selection is not None)
        self.del_button.set_enabled(self.selection is not None)

    def on_select(self, obj):
        # called by db_gui.ListBox and our on_add method
        self.selection = obj
        self._fix_buttons()
        if self.select_fn is not None:
            self.select_fn(obj)

    def on_add(self, event):
        # called by our Add button
        obj = self.add_fn()
        if obj is not None:
            self.on_select(obj)

    def on_edit(self, event):
        # called by our Edit button
        if self.selection is not None: # it shouldn't be!
            self.edit_fn(self.selection)

    def on_del(self, event):
        # called by our Delete button
        if self.selection is not None: # it shouldn't be!
            self.del_fn(self.selection)
            self.list_box.delete(self.selection)
            self.selection = None
            self._fix_buttons()


class TextCtrl:

    def __init__(
        self, parent, sizer,
        label,
        size = default_line, init_value='', on_enter=None
    ):
        self.parent = parent
        self.value = init_value
        self.on_enter_fn=on_enter

        text_sizer=wx.BoxSizer(wx.HORIZONTAL)

        self.label = wx.StaticText(parent, label=label + ': ')
        text_sizer.Add(self.label)

        if on_enter is not None:
            self.text_ctrl = wx.TextCtrl(
                parent, size=size, value=init_value, style=wx.TE_PROCESS_ENTER)
            self.text_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        else:
            self.text_ctrl = wx.TextCtrl(parent, value=init_value)
        text_sizer.Add(self.text_ctrl)

        sizer.Add(text_sizer)

    def on_enter(self, event):
        self.value = event.GetEventObject().GetValue()
        if self.on_enter_fn is not None: # it shouldn't be
            self.on_enter_fn(self.value)

    def set_enabled(self, enabled):
        if enabled:
            self.text_ctrl.Enable()
        else:
            self.text_ctrl.Disable()


class AttrTextCtrl(TextCtrl):

    def __init__(
        self, parent, sizer,
        label, obj, attr,
        size = default_line, on_enter=None
    ):
        self.obj = obj
        self.attr = attr
        self.attr_on_enter_fn = on_enter

        super().__init__(
            parent, sizer, label, size=size,
            init_value=getattr(obj, attr), on_enter=self.attr_on_enter)
        self.text_ctrl.Bind(wx.EVT_TEXT, self.attr_on_text)

    def attr_on_text(self, event):
        setattr(self.obj, self.attr, event.GetEventObject().GetValue())

    def attr_on_enter(self, event):
        if self.attr_on_enter_fn is not None:
            self.attr_on_enter_fn(event.GetEventObject.GetValue())

