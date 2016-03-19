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

def do_a_test(fat, tmpdir, check_func):
    testout = tmpdir.join("writetest.img")

    fat.write(str(testout))

    check_func(fat, tmpdir, os.stat(str(testout)).st_size)

    # Now make sure we can re-open the written ISO.
    pyfat.PyFat().open(str(testout))

    fat2 = pyfat.PyFat()
    fat2.open(str(testout))
    check_func(fat2, tmpdir, os.stat(str(testout)).st_size)
    fat2.close()

def test_new_nofiles(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    do_a_test(fat, tmpdir, check_nofiles)

def test_new_rmfile(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO.TXT", str(foo))

    fat.rm_file("/FOO.TXT")

    do_a_test(fat, tmpdir, check_nofiles)

def test_new_rmfile_no_ext(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))

    fat.rm_file("/FOO")

    do_a_test(fat, tmpdir, check_nofiles)

def test_new_onefile(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))

    do_a_test(fat, tmpdir, check_onefile)

def test_new_onedir(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    fat.add_dir("/DIR1")

    do_a_test(fat, tmpdir, check_onedir)

def test_new_rmdir(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    fat.add_dir("/DIR1")
    fat.rm_dir("/DIR1")

    do_a_test(fat, tmpdir, check_nofiles)

def test_new_onefile_system(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))
    fat.set_system("/FOO")

    do_a_test(fat, tmpdir, check_onefile_system)

def test_new_onefile_archive(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))
    fat.set_archive("/FOO")

    do_a_test(fat, tmpdir, check_onefile_archive)

def test_new_onefile_hidden(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))
    fat.set_hidden("/FOO")

    do_a_test(fat, tmpdir, check_onefile_hidden)

def test_new_onefile_read_only(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))
    fat.set_read_only("/FOO")

    do_a_test(fat, tmpdir, check_onefile_read_only)

def test_new_onefile_all_attr(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))
    fat.set_read_only("/FOO")
    fat.set_hidden("/FOO")
    fat.set_system("/FOO")
    fat.set_archive("/FOO")

    do_a_test(fat, tmpdir, check_onefile_all_attr)

def test_new_onefile_no_attr(tmpdir):
    fat = pyfat.PyFat()
    fat.new()

    foo = tmpdir.join("foo")
    foo.write("foo\n")

    fat.add_file("/FOO", str(foo))
    fat.clear_read_only("/FOO")
    fat.clear_hidden("/FOO")
    fat.clear_system("/FOO")
    fat.clear_archive("/FOO")

    do_a_test(fat, tmpdir, check_onefile_no_attr)

def test_hybrid_manyfiles_subdir(tmpdir):
    indir = tmpdir.mkdir("manyfilessubdir")

    fat = pyfat.PyFat()

    fat.new()

    fat.add_dir("/DIR1")

    for i in range(1, 18):
        num = "{:0>2}".format(str(i))
        numfile = os.path.join(str(indir), "file"+num)
        with open(numfile, "wb") as outfp:
            outfp.write("file" + num + "\n")
        fat.add_file("/DIR1/FILE" + num, numfile)

    do_a_test(fat, tmpdir, check_manyfiles_subdir)

    fat.close()
