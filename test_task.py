''' test implementation of Task, without threading or pubsub '''

from collections import deque
import sys

class TestTask:

    def init_impl(self, **kwargs):
        self.deque = deque()
        self.pubs = {}
        sys.setrecursionlimit(3000)
        for msg, method in self.subs.items():
            self.pubs[msg] = 0

    def _enqueue(self, msg, data):
        self.deque.append((msg, data))
        while len(self.deque) > 0:
            msg, data = self.deque.popleft()
            if msg == 'Task.call':
                self._step(data)
            elif msg in self.pubs:
                self.pubs[msg] += 1
        pass

    def pub(self, msg, data=None):
        ''' publish msg, data '''
        self._enqueue(msg, data)

    def _queue(self, step):
        ''' queue <method> to be called with <data> '''
        self._enqueue('Task.call', step)

    def _spawn(self, step):
        ''' start a thread calling <method> with <data> '''
        self._enqueue('Task.call', step)
