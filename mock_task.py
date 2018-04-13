""" mock implementation of Task, without threading or pubsub """

from collections import deque
import sys

from task import SlicerState, Slicer, TaskState, Task


class MockSlicer(Slicer):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.subs = {} # map: topic -> list(function)
        if not self.suspended:
            self._run()

    def resume(self):
        super().resume()
        self._run()

    def _run(self):
        while self.state == SlicerState.QUEUED:
            self.slice()

    def sub(self, list):
        for function, topic in list:
            if topic in self.subs:
                self.subs[topic].append(function)
            else:
                self.subs[topic] = [function]

    def pub(self, topic, **kw):
        # TODO: queue these and invoke them at the end of a slice
        if topic in self.subs:
            for function in self.subs[topic]:
                function(**kw)

    def queue(self):
        pass

    def _subthread(self, fn):
        fn()
