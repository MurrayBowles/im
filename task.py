""" Framework for long-running tasks. """

from collections import deque
import datetime
from enum import Enum
import sys
import threading

debug_exc = True


class SlicerState(Enum):
    IDLE    = 0  # the slicer is not queued or running
    QUEUED  = 1  # the Slicer is queued for execution
    RUNNING = 2  # the Slicer is executing Task steps


class Slicer:
    def __init__(self, **kw):
        self.max_slice_ms = kw['max_slice_ms'] if 'max_slice_ms' in kw else 100
        self.suspended = kw['suspended'] if 'suspended' in kw else False
        num_queues = kw['num_queues'] if 'num_queues' in kw else 2
        # map: topic -> list of function

        self.queues = []
        for pri in range(num_queues):
            self.queues.append(deque())  # deque of Task
        self.state = SlicerState.IDLE

    def __repr__(self):
        return '<Slicer %s>' % self.state.name.lower()

    def suspend(self):
        """ Prevent future slice() calls from executing. """
        self.suspended = True

    def resume(self):
        """ Allow future slice() calls to execute. """
        if self.suspended:
            self.suspended = False
            if self.state == SlicerState.IDLE:
                # it's not guaranteed here that there are any queued Tasks,
                # but slice() deals with that case
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

    def subthread(self, fn):
        """ Run fn in a subthread.

            must be implemented by subclass
        """
        raise NotImplementedError

    def _queue(self):
        """ Queue the Slicer for execution. """
        self.state = SlicerState.QUEUED
        self.queue()

    def _schedule(self, task):
        """ Schedule a Task.

            called only from Task
        """
        assert task.pri < len(self.queues)
        self.queues[task.pri].append(task)
        if self.state == SlicerState.IDLE and not self.suspended:
            self._queue()

    def slice(self):
        """ Perform the next Slice of Task steps. """
        if self.suspended:
            self.state = SlicerState.IDLE
            return
        if self.state == SlicerState.IDLE:
            return
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

    def sub(self, list):
        """ Subscribe to the topics in list.

        <list> is a list of (function, topic) paits
        """
        raise NotImplementedError

    def pub(self, *args, **kw):
        """ Publish a message at the end of the current slice. """
        raise NotImplementedError


class Task2State(Enum):
    INIT        = 0 # task.start() has not yet been called
    READY       = 1 # the Task is ready to run
    RUNNING     = 2 # the Slicer is running a Step of the Task
    SUBTHREAD   = 3 # the Task is waiting for a Thread to complete
    DONE        = 4 # the Task has exited with a return
    EXCEPTION   = 5 # the task has executed with an exception


class Task2:
    def __init__(self, slicer, **kw):
        # task.on_done(None | exc_data) is called when the Task is finished
        self.slicer = slicer
        self.pri = kw['pri'] if 'pri' in kw else 0
        self.on_done = kw['on_done'] if 'on_done' in kw else None
        self.state = Task2State.INIT
        self.generator = None
        self.exc_data = None
        self.cancel_requested = False
        self.cancel_seen = False

    def start(self):
        """ Schedule the Task to begin running in its Slicer """
        assert self.state == Task2State.INIT
        self.generator = self.run()
        self.slicer._schedule(self)

    def overtime(self):
        return self.slicer.overtime()

    def cancel(self):
        """ cancel the current task """
        self.cancel_requested = True

    def cancelled(self):
        """ check whether the Task is cancel_seen """
        if self.cancel_requested:
            self.cancel_seen = True
        return self.cancel_seen

    def run(self):
        """ Run the Task's code. """
        raise NotImplementedError

    def sub(self, list):
        """ Subscribe to the topics in list.

        <list> is a list of (function, topic) pairs
        """
        self.slicer.sub(list)

    def pub(self, *args, **kw):
        """ Publish a message at the end of the current slice. """
        self.slicer.pub(*args, **kw)

    def step(self):
        """ Perform the next step of the Task. """
        return next(self.generator)

    def _step(self):
        """ Perform the next step of the Task.

            called only from the Slicer; calls self.step()
        """
        self.state = Task2State.RUNNING
        try:
            subthread_fn = self.step()
            if subthread_fn is not None:
                # start thread_fn in a subthread,
                # and block this Task until it's done
                def do_thread_fn():
                    subthread_fn()
                    self.slicer._schedule(self)
                self.state = Task2State.SUBTHREAD
                self.slicer._subthread(do_thread_fn)
            else:
                # finished a step, but there are more: reschedule
                self.state = Task2State.READY
                self.slicer._schedule(self)
        except StopIteration:
            self.state = Task2State.DONE
            if self.on_done is not None:
                self.on_done(None)
        except Exception as exc_data:
            self.state = Task2State.EXCEPTION
            self.exc_data = exc_data
            if self.on_done is not None:
                self.on_done(exc_data)

    def pname(self):
        s = '%s: %s' % (type(self).__name__, self.state.name.lower())
        if self.state == Task2State.EXCEPTION:
            s += '(%s)' % str(self.exc_data)
        if self.cancel_requested:
            s += '?c'
        if self.cancel_seen:
            s += '!c'
        return s

    def __repr__(self):
        return '<Task %s>' % self.pname()
