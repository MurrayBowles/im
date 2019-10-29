""" wrappers for wxPython widgets and sizers """

from bisect import *
import db
from enum import Enum
import wx

default_box=(200,100)
default_line=(200,20)

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

    def set_hidden(self, hidden):
        if hidden:
            self.button.Hide()
        else:
            self.button.Show()

    def set_label(self, text):
        self.button.SetLabel(text)


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
        self.check_box.SetValue(init_value)
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
            parent, sizer, label, init_value=getattr(obj, attr),
            on_click=self.attr_on_click)

    def attr_on_click(self, value):
        if self.attr_on_click_fn is not None:
            self.attr_on_click_fn(value)
        setattr(self.obj, self.attr, value)


class DirCtrl:

    def __init__(
        self, parent, sizer,
        size = default_box,
        label = None,
        init_path = '',
        select_fn = None,   # (db_name) called whenever the selection changes
        style = 0,
        sizer_idx = -1     # insertion index in sizer
    ):
        self.parent = parent
        self.label = label
        self.select_fn = select_fn
        self.multiple = (style & wx.DIRCTRL_MULTIPLE) != 0

        self.paths = []

        if label is not None:
            label_text = wx.StaticText(parent, label=label)
            sizer.Add(label_text)
        self.dir_ctrl = wx.GenericDirCtrl(
            parent, style=style, size=size, dir=init_path)
        if sizer_idx  != -1:
            sizer.Insert(sizer_idx, self.dir_ctrl)
        else:
            sizer.Add(self.dir_ctrl)
        tree_ctrl = self.dir_ctrl.GetTreeCtrl()
        self.dir_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_select, tree_ctrl)

    def _on_select(self, event):
        if self.multiple:
            def get_item_path(tree_ctrl, item):
                path = ''
                sep = ''
                while True:
                    try:
                        # GetItemParent doesn't return None
                        path = tree_ctrl.GetItemText(item) + sep + path
                    except:
                        break
                    item = tree_ctrl.GetItemParent(item)
                    sep = '/'
                # <label> (<drive letter>:)<db_name> => <drive letter>:<db_name>
                # FIXME: what if the label contains a paren?
                # searching from the right won't help
                # -- filenames CAN contain parens
                left_paren_idx = path.find('(')
                right_paren_idx = path.find(')')
                path = path[left_paren_idx + 1:right_paren_idx]\
                    + path[right_paren_idx + 1:]
                return path
            paths = []
            # self.dir_ctrl.GetPaths(paths) doesn't work
            tree_ctrl = self.dir_ctrl.GetTreeCtrl()
            items = tree_ctrl.GetSelections()
            for item in items:
                path = get_item_path(tree_ctrl, item)
                paths.append(path)
        else:
            paths = [self.dir_ctrl.GetPath()]
        if self.select_fn is not None:
            self.select_fn(paths)
        self.paths = paths

    def set_hidden(self, hidden):
        if hidden:
            self.dir_ctrl.Hide()
        else:
            self.dir_ctrl.Show()

    def get_paths(self):
        return self.paths


class ListBox:

    def __init__(
        self, parent, sizer,
        size = default_box,
        id_fn = lambda x: x.id,
        name_fn = lambda x: x.name,
        select_fn = None,   # called initially, and when the selection changes
        edit_fn = None,     # called when an item is double-clicked
        label = None,
        init_id = -1,       # object ID to select initially
        init_list = None    # initial list to display
    ):
        self.parent = parent
        self.id_fn = id_fn
        self.name_fn = name_fn
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
        if init_sel_idx != -1:
            self.list_box.SetSelection(init_sel_idx)
            self.selection = self.objs[init_sel_idx]
        self.list_box.Bind(wx.EVT_LISTBOX, self._on_select)
        if edit_fn is not None:
            self.list_box.Bind(wx.EVT_LISTBOX_DCLICK, self._on_edit)

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
        return self.names, init_idx

    def _on_select(self, event): # single-click on an item
        # select the item
        sel_idx = self.list_box.GetSelection()
        sel_obj = self.objs[sel_idx]
        if sel_obj != self.selection:
            if self.select_fn is not None:
                if self.select_fn(sel_obj) is None:
                    self.list_box.SetSelection(wx.NOT_FOUND)
                else:
                    self.selection = sel_obj

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
    """ a list box plus ADD, EDIT, DELETE buttons """

    def __init__(
        self, parent, sizer,
        size = default_box,
        id_fn = lambda x: x.id,
        name_fn = lambda x: x.name,
        select_fn = None,   # called initially, and when the selection changes
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
            self.edit_button = Button(
                parent, button_sizer, 'Edit', self.on_edit)
        if del_fn is not None:
            self.del_button = Button(
                parent, button_sizer, 'Delete', self.on_del)
        self._fix_buttons()
        outer_sizer.Add(list_sizer)
        outer_sizer.Add(button_sizer)
        sizer.Add(outer_sizer)

    def _fix_buttons(self):
        self.edit_button.set_enabled(self.selection is not None)
        self.del_button.set_enabled(self.selection is not None)

    def on_select(self, obj):
        # called by db_gui.ListBox and our on_add method
        if self.select_fn is not None:
            if self.select_fn(obj) is None:
                return None
        self.selection = obj
        self._fix_buttons()
        return self.selection


    def on_add(self, event):
        # called by our Add button
        obj = self.add_fn()
        if obj is not None:
            self.list_box.add(obj)
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

    def set_item_color(self, rgb):
        self.list_box.SetItemColour(rgb)


class RadioButton:

    def __init__(
        self, parent, sizer,
        label = '', choices = [], change_fn = None,
        init_value = 0
    ):
        self.parent = parent
        self.value = init_value
        self.change_fn = change_fn

        self.radio_box = wx.RadioBox(parent, label=label, choices=choices)
        self.radio_box.SetSelection(init_value)
        self.radio_box.Bind(wx.EVT_RADIOBOX, self.on_click)
        sizer.Add(self.radio_box)

    def on_click(self, event):
        new_value = self.radio_box.GetSelection()
        if new_value != self.value:
            self.value = new_value
            if self.change_fn is not None:
                self.change_fn(new_value)

    def set_enabled(self, enabled):
        if enabled:
            self.radio_box.Enable()
        else:
            self.radio_box.Disable()

    def set_selection(self, value):
        self.value = value
        self.radio_box.SetSelection(value)

    def set_item_label(self, idx, label):
        self.radio_box.SetItemLabel(idx, label)


class StaticText:

    def __init__(
        self, parent, sizer,
        text, size=default_line
    ):
        self.parent = parent
        self.static_text = wx.StaticText(parent, label=text, size=size)
        sizer.Add(self.static_text)

    def set_text(self, text):
        self.static_text.SetLabel(text)

    def set_hidden(self, hidden):
        if hidden:
            self.static_text.Hide()
        else:
            self.static_text.Show()


class TextCtrl:

    def __init__(
        self, parent, sizer,
        label,
        size = default_line, init_value='', change_fn = None, enter_fn=None
    ):
        self.parent = parent
        self.value = init_value
        self.change_fn = change_fn
        self.enter_fn = enter_fn

        text_sizer=wx.BoxSizer(wx.HORIZONTAL)

        self.label = wx.StaticText(parent, label=label + ': ')
        text_sizer.Add(self.label)

        if enter_fn is not None:
            self.text_ctrl = wx.TextCtrl(
                parent, size=size, value=init_value, style=wx.TE_PROCESS_ENTER)
            self.text_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        else:
            self.text_ctrl = wx.TextCtrl(parent, size=size, value=init_value)
        if self.change_fn is not None:
            self.text_ctrl.Bind(wx.EVT_TEXT, self.on_text)

        text_sizer.Add(self.text_ctrl)

        sizer.Add(text_sizer)

    def on_text(self, event):
        self.value = event.GetEventObject().GetValue()
        if self.change_fn is not None: # it shouldn't be
            self.change_fn(self.value)

    def on_enter(self, event):
        self.value = event.GetEventObject().GetValue()
        if self.enter_fn is not None: # it shouldn't be
            self.enter_fn(self.value)

    def set_enabled(self, enabled):
        if enabled:
            self.text_ctrl.Enable()
        else:
            self.text_ctrl.Disable()

    def set_hidden(self, hidden):
        # FIXME: this doesn't hide the label!
        if hidden:
            pass # self.text_ctrl.Hide()
        else:
            self.text_ctrl.Show()

    def clear(self):
        self.text_ctrl.Clear()


class AttrTextCtrl(TextCtrl):

    def __init__(
        self, parent, sizer,
        label, obj, attr,
        size = default_line, change_fn=None, enter_fn=None
    ):
        self.obj = obj
        self.attr = attr
        self.attr_change_fn = change_fn
        self.attr_enter_fn = enter_fn

        super().__init__(
            parent, sizer, label, size=size,
            init_value=getattr(obj, attr),
            change_fn=self.attr_on_text, enter_fn=self.attr_on_enter)

    def attr_on_text(self, text):
        setattr(self.obj, self.attr, text)
        if self.attr_change_fn is not None:
            self.attr_change_fn(text)

    def attr_on_enter(self, text):
        if self.attr_enter_fn is not None:
            self.attr_enter_fn(text)

