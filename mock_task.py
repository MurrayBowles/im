""" mock implementation of Task, without threading or pubsub """

from collections import deque
import sys

from task import SlicerState, Slicer, Task2State, Task2


class MockTask:

    def init_impl(self, **kwargs):
        self.deque = deque()
        self.pubs = {}
        for msg, method in self.subscriptions.items():
            self.pubs[msg] = 0

    def run_impl(self):
        while len(self.deque) > 0:
            msg, data = self.deque.popleft()
            if msg == 'Task.call':
                self._step(data)
            elif msg in self.pubs:
                self.pubs[msg] += 1
        pass

    def _enqueue(self, msg, data):
        self.deque.append((msg, data))

    def pub(self, msg, data=None):
        """ publish msg, data """
        self._enqueue(msg, data)

    def _queue(self, step):
        """ queue <method> to be called with <data> """
        self._enqueue('Task.call', step)

    def _spawn(self, step):
        """ start a thread calling <method> with <data> """
        self._enqueue('Task.call', step)


class MockSlicer(Slicer):
    def __init__(self, num_queues=2, max_slice_ms=100, suspended=False):
        super().__init__(num_queues, max_slice_ms, suspended)
        if not suspended:
            self._run()

    def resume(self):
        super().resume()
        self._run()

    def _run(self):
        while self.state == SlicerState.QUEUED:
            self.slice()

    def queue(self):
        pass

    def _subthread(self, fn):
        fn()
