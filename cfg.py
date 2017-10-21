''' configuration: stored as 'config' in UserConfigDir '''

import jsonpickle
import os
import wx
from ie_cfg import *

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
        what = 'Image Management configuration'

    def save(self):
        config_file = _config_file('w')
        config_str = jsonpickle.encode(self)
        config_file.write(config_str)
        config_file.close()

    def restore(self):
        ''' called once on initialization to restore the configuration settings '''
        config_file = _config_file('r')
        if config_file is not None:
            config_str = config_file.read()
            c = jsonpickle.decode(config_str)
            self.ie = c.ie
        else:
            self.ie = IECfg()

cfg = Cfg()