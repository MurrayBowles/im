''' dates with wildcards

The types are called IMDate[Pat] to avoid confusion with SQLAlchemy's Date
'''

import datetime
from typing import NewType, Tuple, Union


class IMDate(object):
    val: Tuple[int, int, int]   # year, month, date

    unk = 0     # value for an unknown year, month, or day

    @staticmethod
    def y2k(year):
        if year in range(1, 99):
            if year > 70:
                year += 1900
            else:
                year += 2000
        return year

    def __init__(self, year, month, day):
        self.val = (IMDate.y2k(year), month, day)

    def __repr__(self):
        return 'IMDate(%u, %u, %u)' % (self.val[0], self.val[1], self.val[2])

    def __str__(self):
        def elt_str(elt):
            return '?' if elt == IMDate.unk else str(elt)
        return '%s/%s/%s' % (elt_str(self.val[1]), elt_str(self.val[2]), elt_str(self.val[0]))

    @staticmethod
    def from_str(s):
        elts = s.split('/')
        if len(elts) in range(2, 4):
            if len(elts) == 2:
                year = datetime.date.today().year
            else:
                if elts[2] == '?':
                    year = IMDate.unk
                else:
                    year = IMDate.y2k(int(elts[2]))
            num_elts = [0 if e == '?' else int(e) for e in elts[0:2]]
            return IMDate(year, num_elts[0], num_elts[1])
        else:
            raise ValueError('invalid date string: %s' % s)

    def yymmdd(self):
        return '%.2u%.2u%.2u' % (self.val[0] % 100, self.val[1], self.val[2])

    @staticmethod
    def from_yymmdd(yymmdd):
        year = IMDate.y2k(int(yymmdd[0:2]))
        return IMDate(int(year), int(yymmdd[2:4]), int(yymmdd[4:6]))

    def __eq__(self, other):
        for e1, e2 in zip(self.val, other.val):
            if e1 == IMDate.unk or e1 == IMDate.unk:
                continue
            if e1 != e2:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __composite_values__(self):
        return self.val


IntRange = NewType('IntRange', Union[int, Tuple[int, int]])


class IMDatePat(object):
    val: Tuple[IntRange, IntRange, IntRange]

    wild = 0     # value for an unknown year, month, or day

    def __init__(self, years: IntRange, months: IntRange, days: IntRange):
        years2 = IntRange((tuple([IMDate.y2k(years[0]), IMDate.y2k(years[1])]) if type(years) is tuple
            else IMDate.y2k(years)))
        self.val = tuple([years2, months, days])  # PyCharm is whining about something here

    def __repr__(self):
        def t_str(t):
            if type(t) is tuple:
                return '(%s, %s)' % (t[0], t[1])
            else:
                return str(t)
        return 'DatePat(' + ', '.join(t_str(t) for t in self.val) + ')'

    def __str__(self):
        def elt_str(elt):
            return '?' if elt == IMDatePat.wild else str(elt)
        def t_str(t):
            if type(t) is tuple:
                return '-'.join([elt_str(e) for e in t])
            else:
                return elt_str(t)
        v = self.val
        return '%s/%s/%s' % (t_str(v[1]), t_str(v[2]), t_str(v[0]))

    @staticmethod
    def from_str(s):
        def end_val(end, cv):
            return IMDatePat.wild if end == '?' else cv(int(end))
        def elt_val(elt, cv):
            ends = elt.split('-')
            if len(ends) == 1:
                return end_val(ends[0], cv)
            elif len(ends) == 2:
                return (end_val(ends[0], cv), end_val(ends[1], cv))
            else:
                raise ValueError('malformed year, month, or date: %s' % elt)
        elts = s.split('/')
        if len(elts) in range(2, 4):
            args = []
            if len(elts) == 2:
                args.append(datetime.date.today().year)
            else:
                args.append(elt_val(elts[2], lambda x: IMDate.y2k(x)))
            for elt in elts[0:2]:
                args.append(elt_val(elt, lambda x: x))
            return IMDatePat(*args)
        else:
            raise ValueError('invalid date string: %s' % s)

    def __eq__(self, other):
        return self.val == other.val

    def match(self, date: IMDate):
        for p, d in zip(self.val, date.val):
            if d is IMDate.unk:
                continue
            if type(p) is tuple:
                if p[0] != IMDatePat.wild and p[0] > d:
                    return False
                if p[1] != IMDatePat.wild and p[1] < d:
                    return False
            else:
                if p != IMDatePat.wild and p != d:
                    return False
        return True

if __name__ == '__main__':
    import jsonpickle
    d = IMDate(2014, 3, IMDate.unk)
    dj = jsonpickle.encode(d)
    jd = jsonpickle.decode(dj)
    sd = str(d)
    ds = IMDate.from_str(sd)
    d2 = IMDate(14, 3, IMDate.unk)
    yd2 = d2.yymmdd()
    d2y = IMDate.from_yymmdd(yd2)
    sd2y = str(d2y)
    d3 = IMDate(14, IMDate.unk, 3)
    yd3 = d3.yymmdd()
    d3y = IMDate.from_yymmdd(yd3)
    sd3y = str(d3y)
    ttt = d == IMDate(2014, 3, 11)
    fff = d == IMDate(2014, 2, 11)
    cv = d.__composite_values__()
    p = IMDatePat(2014, IMDatePat.wild, (1, 3))
    pj = jsonpickle.encode(p)
    jp = jsonpickle.decode(pj)
    pr = repr(p)
    ps = str(p)
    sp = IMDatePat.from_str(ps)
    ttt = p.match(d)
    fff = p.match(IMDate(2011, 7, 11))
    pass