''' test IMDate[Pat] '''

from imdate import *

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

    check([2019, 1, 10], '190110', '1/10/2019')
    check([19, 1, 10], '190110', '1/10/2019')
    check([0, 1, 10], '000110', '1/10/?')
    check([2019, 1, 10], '190110', '1/10/2019', '1/10/19')
    check([2019, 0, 10], '190010', '?/10/2019')
    check([2019, 1, 0], '190100', '1/?/2019')
    check([0, 0, 0], '000000', '?/?/?')
    pass

