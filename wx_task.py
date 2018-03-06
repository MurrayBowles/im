""" wxPython implementation of Task, using Python threads and wxPython pubsub """

from threading import Thread
import wx
from wx.lib.pubsub import pub

from task import Slicer, Task2

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


class WxSlicer(Slicer):
    def __init__(self, num_queues=2, max_slice_ms=100, suspended=False, msg=None):
        # <msg> is the pubsub message string used to queue slices in the
        # wxpython message queue
        self._msg = msg
        pub.subscribe(self._on_slice, msg)
        super().__init__(num_queues, max_slice_ms, suspended)
        if not suspended:
            self._queue()

    def queue(self):
        wx.callAfter(lambda: pub.sendMessage(self._msg, None))

    def _on_slice(self):
        self.slice()

    def _subthread(self, fn):
        Thread(target=fn)
