''' framework for long-running tasks '''

import datetime


class Task:

    def __init__(self, **kwargs):
        self.subs = kwargs['subs'] if 'subs' in kwargs else {}
        self.max_step_ms = kwargs['max_step_ms'] if 'max_step_ms' in kwargs else '200'
        self.cancel_requested = False
        self.cancel_seen = False

    def pub(self, msg, data=None):
        ''' publish msg, data '''
        raise NotImplementedError

    def queue(self, method, data=None):
        ''' queue <method> to be called with <data> '''
        raise NotImplementedError

    def _step_begun(self):
        ''' start the overtime timer
            called by subclasses when a queued step is begun
        '''
        self.step_begun = datetime.datetime.now()

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


    def spawn(self, method, data=None):
        ''' start a thread calling <method> with <data> '''
        raise NotImplementedError

    def __repr__(self):
        return '<%s %u>' % (self.__class__.__name__, id(self))

