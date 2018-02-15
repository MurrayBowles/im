""" Framework for long-running tasks. """

from collections import deque
import datetime
from enum import Enum
import sys
import threading

debug_exc = True


class TaskStepState(Enum):
    QUEUED = 1
    SPAWNED = 2
    BEGUN = 3
    DONE = 4
    EXCEPTION = 5

    def qq__repr__(self):
        return ['queued', 'spawned', 'begun', 'done', 'exception'][self.value]


class TaskStep:
    def __init__(self, method, data, state):
        self.method = method
        self.data = data
        self.state = state

    def __repr__(self):
        return '<TaskStep %s>' % str(self.state)


class Task:
    def __init__(self, **kwargs):
        self.subscriptions = kwargs['subscriptions'] if 'subscriptions' in kwargs else {}
        # list of (msg, method) tuples
        self.max_step_ms = kwargs['max_step_ms'] if 'max_step_ms' in kwargs else 200
        self.cancel_requested = False
        self.cancel_seen = False
        self.init_impl(**kwargs)
        self.done = False
        self.steps = []  # list of TaskStep, appended to by self._step
        self.num_done_steps = 0

    def start(self, method, data=None):
        """ called by the subclass, e.g. IETask, at the end of its initialization """
        self.queue(method, data)
        self.run_impl()

    def init_impl(self):
        """ perform initialization for the slice/thread implementation mixin """
        raise NotImplementedError

    def run_impl(self):
        """ in a test case, simulate the message loop """
        pass

    def pub(self, msg, data=None):
        """ publish msg, data (supplied by implementation mixin) """
        raise NotImplementedError

    def _queue(self, step):
        """ queue <method> to be called with <data> (supplied by implementation mixin) """
        raise NotImplementedError

    def queue(self, method, data=None):
        """ queue <method> to be called with <data> """
        step = TaskStep(state=TaskStepState.QUEUED, method=method, data=data)
        self.steps.append(step)
        self._queue(step)

    def _spawn(self, step):
        """ start a thread calling <method> with <data> (supplied by implementation mixin) """
        raise NotImplementedError

    def spawn(self, method, data=None):
        """ start a thread calling <method> with <data> """
        step = TaskStep(state=TaskStepState.SPAWNED, method=method, data=data)
        self.steps.append(step)
        self._spawn(step)

    def _step(self, step):
        """ call the method for a slice or thread """
        self.step_begun = datetime.datetime.now()
        step.state = TaskStepState.BEGUN
        step.thread = threading.current_thread()
        if debug_exc:
            step.method(step.data)
            step.state = TaskStepState.DONE
        else:
            try:
                step.method(step.data)
                step.state = TaskStepState.DONE
            except:
                step.exc_info = sys.exc_info()
                step.state = TaskStepState.EXCEPTION
                pass
        now = datetime.datetime.now()
        ms = (now - self.step_begun).total_seconds() * 1000
        step.ms = int(ms)
        self.num_done_steps += 1
        if self.num_done_steps == len(self.steps):
            self.done = True
            self._done()

    def overtime(self):
        """ check whether the current Task step is overtime """
        now = datetime.datetime.now()
        return (now - self.step_begun).total_seconds() * 1000 > self.max_step_ms

    def cancel(self):
        """ cancel the current task """
        self.cancel_requested = True

    def cancelled(self):
        """ check whether the Task is cancel_seen """
        if self.cancel_requested:
            self.cancel_seen = True
        return self.cancel_seen

    def _done(self):
        """ note the end of a Task """
        pass

    def __repr__(self):
        return '<%s %u>' % (self.__class__.__name__, id(self))


class SlicerState(Enum):
    IDLE    = 0  # the slicer is not queued or running
    QUEUED  = 1  # the Slicer is queued for execution
    RUNNING = 2  # the Slicer is executing Task steps


class Slicer:
    def __init__(self, num_queues=2, max_slice_ms=100, suspended=False):
        self.queues = []
        for pri in range(num_queues):
            self.queues.append(deque())  # deque of Task
        self.state = SlicerState.IDLE
        self.max_slice_ms = max_slice_ms
        self.suspended = suspended

    def __repr__(self):
        return '<Slicer %s>' % self.state.name.lower()

    def suspend(self):
        self.suspended = True

    def resume(self):
        if self.suspended:
            self.suspended = False
            if self.state == SlicerState.IDLE:
                # it's not guaranteed here that there are any queued Tasks, but slice() deals with that
                self._queue()

    def _pop_task(self):
        """ Pop and return the highest-priority queued Task. """
        for q in self.queues:
            try:
                return q.pop()
            except:
                continue
        else:
            return None

    def queue(self):
        """ Queue the Slicer for execution.

            must be implemented by subclass
        """
        raise NotImplementedError

    def _queue(self):
        """ Queue the Slicer for execution. """
        self.queue()
        self.state = SlicerState.QUEUED

    def _schedule(self, task, pri):
        """ Schedule a Task.

            called only from Task
        """
        assert pri < len(self.queues)
        self.queues[pri].append(task)
        if self.state == SlicerState.IDLE and not self.suspended:
            self._queue()

    def slice(self):
        """ Perform the next Slice of Task steps. """
        if self.suspended:
            self.state = SlicerState.IDLE
            return
        assert self.state == SlicerState.QUEUED
        self.state = SlicerState.RUNNING
        self.slice_begun = datetime.datetime.now()
        while True:
            task = self._pop_task()
            if task is None:  # no more ready Tasks
                self.state = SlicerState.IDLE
                break
            task._step()
            if self.overtime():  # no time left in this Slice
                if sum(len(x) for x in self.queues) != 0:
                    self._queue()
                else:
                    self.state = SlicerState.IDLE
                break

    def overtime(self):
        """ Check whether the current Slice is overtime. """
        now = datetime.datetime.now()
        ms = (now - self.slice_begun).total_seconds() * 1000
        if ms > self.max_slice_ms:
            pass
        return ms > self.max_slice_ms


class Task2State(Enum):
    READY       = 0 # the Task is ready to run
    RUNNING     = 1 # the Slicer is running a Step of the Task
    BLOCKED     = 2 # the Task is blocked (needs to be re-scheduled)
    DONE        = 3 # the Task has exited with a return
    EXCEPTION   = 4 # the task has executed with an exception


class Task2:
    def __init__(self, generator, slicer, pri=0, on_done=None):
        self.generator = generator
        self.name = generator.gi_code.co_name # generator function name
        self.slicer = slicer
        self.pri = pri
        self.on_done = on_done
        self.state = Task2State.READY
        self.exc_data = None
        s = str(self)
        slicer._schedule(self, pri)

    def __repr__(self):
        s = 'Task %s: %s' % (self.name, self.state.name.lower())
        if self.state == Task2State.EXCEPTION:
            s += '(%s)' % str(self.exc_data)
        return '<%s>' % s

    def overtime(self):
        return self.slicer.overtime()

    def step(self):
        """ Perform the next step of the Task. """
        return next(self.generator)

    def _step(self):
        """ Perform the next step of the Task.

            called only from the Slicer
        """
        self.state = Task2State.RUNNING
        try:
            res = self.step()
            if res is not None:
                # currently the only case is if the step did 'yield Task.thread()'
                self.state = Task2State.BLOCKED
            else:
                # finished a step, but there are more: reschedule
                self.state = Task2State.READY
                self.slicer._schedule(self, self.pri)
        except StopIteration:
            self.state = Task2State.DONE
            if self.on_done is not None:
                self.on_done(None)
        except Exception as exc_data:
            self.state = Task2State.EXCEPTION
            self.exc_data = exc_data
            if self.on_done is not None:
                self.on_done(exc_data)

    def subthread(self, method, data):
        """ Execute method(data) in a subthread. """
        raise NotImplementedError
