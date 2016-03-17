import pytest
import subprocess
import os
import sys
import StringIO

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyfat.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyfat

from common import *

def do_a_test(fat, check_func):
    out = StringIO.StringIO()
    fat.write(out)

    with open('/home/clalancette/upstream/pyfat/debug.flop', 'w') as fp:
        fp.write(out.getvalue())

    check_func(fat, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyfat.PyFat().open(out, len(out.getvalue()) / 1024)

    fat2 = pyfat.PyFat()
    fat2.open(out, len(out.getvalue()) / 1024)
    check_func(fat2, len(out.getvalue()))
    fat2.close()

def test_new_nofiles():
    fat = pyfat.PyFat()
    fat.new()

    do_a_test(fat, check_nofiles)
