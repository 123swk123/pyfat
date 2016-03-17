import pytest
import subprocess
import os
import sys
import StringIO
import shutil

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

    check_func(fat, len(out.getvalue()))

    fat2 = pyfat.PyFat()
    fat2.open(out, len(out.getvalue()) / 1024)
    check_func(fat2, len(out.getvalue()))
    fat2.close()

def test_hybrid_rmfile(tmpdir):
    indir = tmpdir.mkdir("nofiles")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    with open(os.path.join(str(indir), "foo"), "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), "foo", "::FOO"])

    fat = pyfat.PyFat()

    with open(str(outfile), 'rb') as fp:
        fat.open(fp, os.fstat(fp.fileno()).st_size / 1024)

        fat.rm_file("/FOO")

        do_a_test(fat, check_nofiles)

        fat.close()
