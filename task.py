''' framework for long-running tasks '''

import datetime
from enum import Enum
import sys
import threading

debug_exc = True


class TaskStepState(Enum):

    QUEUED      = 1
    SPAWNED     = 2
    BEGUN       = 3
    DONE        = 4
    EXCEPTION   = 5


class Task:

    def __init__(self, **kwargs):
        self.subs = kwargs['subs'] if 'subs' in kwargs else {}
        self.max_step_ms = kwargs['max_step_ms'] if 'max_step_ms' in kwargs else 200
        self.cancel_requested = False
        self.cancel_seen = False
        self.init_impl(**kwargs)
        self.done = False
        self.steps = []             # appended to by self._step
        self.num_done_steps = 0

    def start(self, method, data=None):
        ''' called by the subclass, e.g. IETask, at the end of its initialization '''
        self.queue(method, data)
        self.run_impl()

    def init_impl(self):
        ''' perform initialization for the slice/thread implementation mixin '''
        raise NotImplementedError

    def run_impl(self):
        ''' in a test case, simulate the message loop '''
        pass

    def pub(self, msg, data=None):
        ''' publish msg, data (supplied by implementation mixin) '''
        raise NotImplementedError

    def _queue(self, step):
        ''' queue <method> to be called with <data> (supplied by implementation mixin) '''
        raise NotImplementedError

    def queue(self, method, data=None):
        ''' queue <method> to be called with <data> '''
        step = {'state': TaskStepState.QUEUED, 'method': method, 'data': data}
        self.steps.append(step)
        self._queue(step)

    def _spawn(self, step):
        ''' start a thread calling <method> with <data> (supplied by implementation mixin) '''
        raise NotImplementedError

    def spawn(self, method, data=None):
        ''' start a thread calling <method> with <data> '''
        step = {'state': TaskStepState.SPAWNED, 'method': method, 'data': data}
        self.steps.append(step)
        self._spawn(step)

    def _step(self, step):
        ''' call the method for a slice or thread '''
        self.step_begun = datetime.datetime.now()
        step['state'] = TaskStepState.BEGUN
        step['thread'] = threading.current_thread()
        if debug_exc:
            step['method'](step['data'])
            step['state'] = TaskStepState.DONE
        else:
            try:
                step['method'](step['data'])
                step['state'] = TaskStepState.DONE
            except:
                step['exc_info'] = sys.exc_info()
                step['state'] = TaskStepState.EXCEPTION
                pass
        now = datetime.datetime.now()
        ms = (now - self.step_begun).total_seconds() * 1000
        step['ms'] = int(ms)
        self.num_done_steps += 1
        if self.num_done_steps == len(self.steps):
            self.done = True
            self._done()

    def overtime(self):
        ''' check whether the current Task step is overtime '''
        now = datetime.datetime.now()
        return (now - self.step_begun).total_seconds() * 1000 > self.max_step_ms

    def cancel(self):
        ''' cancel the current task '''
        self.cancel_requested = True

    def cancelled(self):
        ''' check whether the Task is cancel_seen '''
        if self.cancel_requested:
            self.cancel_seen = True
        return self.cancel_seen

    def _done(self):
        ''' note the end of a Task '''
        pass

    def __repr__(self):
        return '<%s %u>' % (self.__class__.__name__, id(self))

