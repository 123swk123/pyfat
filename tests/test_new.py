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

def test_new_rmfile():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO.TXT", StringIO.StringIO(mystr), len(mystr))

    fat.rm_file("/FOO.TXT")

    do_a_test(fat, check_nofiles)

def test_new_rmfile_no_ext():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))

    fat.rm_file("/FOO")

    do_a_test(fat, check_nofiles)

def test_new_onefile():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))

    do_a_test(fat, check_onefile)

def test_new_onedir():
    fat = pyfat.PyFat()
    fat.new()

    fat.add_dir("/DIR1")

    do_a_test(fat, check_onedir)

def test_new_rmdir():
    fat = pyfat.PyFat()
    fat.new()

    fat.add_dir("/DIR1")
    fat.rm_dir("/DIR1")

    do_a_test(fat, check_nofiles)

def test_new_onefile_system():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))
    fat.set_system("/FOO")

    do_a_test(fat, check_onefile_system)

def test_new_onefile_archive():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))
    fat.set_archive("/FOO")

    do_a_test(fat, check_onefile_archive)

def test_new_onefile_hidden():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))
    fat.set_hidden("/FOO")

    do_a_test(fat, check_onefile_hidden)

def test_new_onefile_read_only():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))
    fat.set_read_only("/FOO")

    do_a_test(fat, check_onefile_read_only)

def test_new_onefile_all_attr():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))
    fat.set_read_only("/FOO")
    fat.set_hidden("/FOO")
    fat.set_system("/FOO")
    fat.set_archive("/FOO")

    do_a_test(fat, check_onefile_all_attr)

def test_new_onefile_no_attr():
    fat = pyfat.PyFat()
    fat.new()

    mystr = "foo\n"
    fat.add_fp("/FOO", StringIO.StringIO(mystr), len(mystr))
    fat.clear_read_only("/FOO")
    fat.clear_hidden("/FOO")
    fat.clear_system("/FOO")
    fat.clear_archive("/FOO")

    do_a_test(fat, check_onefile_no_attr)
