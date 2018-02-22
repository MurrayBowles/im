""" wxPython implementation of Task, using Python threads and wxPython pubsub """

from threading import Thread
import wx
from wx.lib.pubsub import pub

class WxTask:

    def init_impl(self, **kwargs):
        for msg, method in self.subsciptions.items():
            ps.subscribe(msg, method)
        pub.subscribe(self._call, 'Task.call')

    def pub(self, msg, data=None):
        """ publish msg, data """
        def do_pub(msg, data):
            pub.sendMessage(msg, data=data)
        wx.CallAfter(do_pub, msg, data=data)

    def _call(self, step):
        self._step(step)

    def _queue(self, step):
        """ queue <method> to be called with <data> """
        def do_pub(msg, data):
            pub.sendMessage(msg, step=step)
        wx.CallAfter(do_pub, 'Task.call', step)

    def _spawn(self, step):
        """ start a thread calling <method> with <data> """
        _WxThread(self, step)


class _WxThread(Thread):

    def __init__(self, itself, step):
        super().__init__()
        self.itself = itself
        self.step = step
        self.start()

    def run(self):
        self.itself._step(self.step)
