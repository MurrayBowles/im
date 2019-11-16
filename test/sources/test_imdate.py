''' test IMDate[Pat] '''

from imdate import *

dates = [
    ([2019, 3, 10], '190310', '3/10/2019'),
    ([19, 3, 10], '190310', '3/10/2019'),
    ([0, 3, 10], '000310', '3/10/?'),
    ([2019, 3, 10], '190310', '3/10/2019', '3/10/19'),
    ([2019, 0, 10], '190010', '?/10/2019'),
    ([2019, 3, 0], '190300', '3/?/2019'),
    ([0, 0, 0], '000000', '?/?/?')
]


def test_dates():
    def check(d, yymmdd, s, ins = None):
        def ck(a, b):
            if a != b:
                assert a == b
        date = IMDate(*d)
        ds = str(date)
        ck(ds, s)
        dfs = IMDate.from_str(ds)
        ck(dfs, date)
        if ins != None:
            dfs2 = IMDate.from_str(ins)
            ck(dfs2, date)
        dyymmdd = date.yymmdd()
        ck(dyymmdd, yymmdd)
        dfy = IMDate.from_yymmdd(dyymmdd)
        ck(dfy, date)
        pass
    for d in dates:
        check(*d)
    pass


point_date_pats = [
    ([2019, 1, 10], '1/10/2019'),
    ([19, 1, 10], '1/10/2019'),
    ([0, 1, 10], '1/10/?'),
    ([2019, 1, 10], '1/10/2019', '1/10/19'),
    ([2019, 0, 10], '?/10/2019'),
    ([2019, 1, 0], '1/?/2019'),
    ([0, 0, 0], '?/?/?'),
]


def test_point_date_pats():
    def check(p, s, ins=None):
        def ck(a, b):
            if a != b:
                assert a == b
        pat = IMDatePat(*p)
        ps = str(pat)
        ck(ps, s)
        pfs = IMDatePat.from_str(ps)
        ck(pfs, pat)
        if ins != None:
            pfs2 = IMDatePat.from_str(ins)
            ck(pfs2, pat)
        pass
    for p in point_date_pats:
        check(*p)
    pass


slice_date_pats = [
    ([2019, 1, 10-12], '1/10-12/2019'),
    ([19, 1-3, 0], '1-3/?/2019'),
    ([0, 1-3, 0], '1-3/?/?'),
    ([2010-2019, 1, 10], '1/10/2010-2019')
]


def test_slice_date_pats():
    def check(p, s, ins=None):
        def ck(a, b):
            if a != b:
                assert a == b
        pat = IMDatePat(*p)
        ps = str(pat)
        ck(ps, s)
        pfs = IMDatePat.from_str(ps)
        ck(pfs, pat)
        if ins != None:
            pfs2 = IMDatePat.from_str(ins)
            ck(pfs2, pat)
        pass
    for p in point_date_pats:
        check(*p)
    pass


unk_cases = [
    (lambda x: x, True),
    (lambda x: 1, True),
    (lambda x: IMDatePat.wild, True)
]


normal_cases = [
    (lambda x: x, True),
    (lambda x: x + 1, False),
    (lambda x: (x - 1, x + 1), True),
    (lambda x: (x - 2, x - 1), False),
    (lambda x: (x + 1, x + 2), False),
    (lambda x: IMDatePat.wild, True),
    (lambda x: (x, IMDatePat.wild), True),
    (lambda x: (IMDatePat.wild, x), True)
]

num_tests = 0


def test_match():
    def check(d, p, exp):
        global num_tests
        num_tests += 1
        res = p.match(d)
        if res != exp:
            assert res == exp
    def gen_check(d):
        def g_check(d, val, args, exp):
            if len(val) == 0:
                p = IMDatePat(*args)
                check(d, p, exp)
            else:
                elt = val[0]
                for c in unk_cases if elt == IMDate.unk else normal_cases:
                    g_check(d, val[1:], args + [c[0](elt)], exp & c[1])
        g_check(d, d.val, [], True)
    for d in dates:
        gen_check(IMDate(*d[0]))
    pass
