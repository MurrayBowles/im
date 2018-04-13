""" per-user persistent app data, stored jsonpicked in UserDataDir/im-config """

import copy
import jsonpickle
import os
import wx

from gui_cfg import GuiCfg
from ie_cfg import IECfg

def _config_file(mode):
    user_data_path = wx.StandardPaths.Get().GetUserDataDir()
    if not os.path.exists(user_data_path):
        if mode == 'r':
            return None
        os.mkdir(user_data_path)
    config_path = user_data_path + '\\im-config'
    if not os.path.exists(config_path) and mode == 'r':
        return None
    config_file = open(config_path, mode)
    return config_file

class Cfg(object):

    def __init__(self):
        self.what = 'Image Management configuration'

    def save(self):
        config_file = _config_file('w')
        config_str = jsonpickle.encode(self)
        config_file.write(config_str)
        config_file.close()

    def restore(self):
        """ Restore the configuration settings.

            called once on initialization
        """
        config_file = _config_file('r')
        if config_file is not None:
            config_str = config_file.read()
            try:
                # restore saved configuration
                c = jsonpickle.decode(config_str)
                self.gui = c.gui
                self.ie = c.ie
                return
            except:
                pass
        # build default configuration
        self.gui = GuiCfg()
        self.ie = IECfg()
        pass

    def snapshot(self):
        """ used when passing cfg to background threads """
        return copy.deepcopy(self)

cfg = Cfg() # per-user persistent app data