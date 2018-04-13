""" wxPython implementation of Task """

from threading import Thread
from time import sleep
import wx
from wx.lib.pubsub import pub

from task import Slicer, Task2

class _WxThread(Thread):
    def __init__(self, itself, step):
        super().__init__()
        self.itself = itself
        self.step = step
        self.start()

    def run(self):
        self.itself._step(self.step)


wx_slicer = None


class WxSlicer(Slicer):
    def __init__(self, **kw):
        super().__init__(**kw)

    def sub(self, list):
        for function, topic in list:
            pub.subscribe(function, topic)

    def pub(self, topic, **kw):
        wx.CallAfter(lambda: pub.sendMessage(topic, **kw))

    def queue(self):
        wx.CallAfter(lambda: self.slice())

    def _subthread(self, fn):
        Thread(target=fn).start()

    @classmethod
    def get(cls, **kw):
        global wx_slicer
        if wx_slicer is None:
            wx_slicer = cls(**kw)
        return wx_slicer

class WxTask2(Task2):
    def __init__(self, slicer=None, **kw):
        if slicer is None:
            slicer = WxSlicer.get(**kw)
        super().__init__(slicer, **kw)
