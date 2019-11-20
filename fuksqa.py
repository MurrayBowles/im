''' I wish I'd never heard of SQLAlchemy -- debugging with print statements '''

fuksqa_step = 0
fuksqa_stop = 24333

def fuksqa():
    global fuksqa_stop
    global fuksqa_step
    fuksqa_step += 1
    print('FUKSQA %u' % fuksqa_step)
    if fuksqa_step == fuksqa_stop:
        print('STOP')
