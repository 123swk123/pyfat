import pytest
import subprocess
import os
import sys

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyfat.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyfat

from common import *

def do_a_test(tmpdir, outfile, check_func):
    testout = tmpdir.join("writetest.img")

    # Now open up the floppy with pyfat and check some things out.
    fat = pyfat.PyFat()
    fat.open(outfile)
    check_func(fat, tmpdir, os.stat(outfile).st_size)
    fat.write(str(testout))
    fat.close()

    # Now round-trip through write.
    fat2 = pyfat.PyFat()
    fat2.open(str(testout))
    check_func(fat2, tmpdir, os.stat(str(testout)).st_size)
    fat2.close()

def test_parse_nofiles(tmpdir):
    indir = tmpdir.mkdir("nofiles")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])

    do_a_test(tmpdir, outfile, check_nofiles)

def test_parse_onefile(tmpdir):
    indir = tmpdir.mkdir("onefile")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile)

def test_parse_onedir(tmpdir):
    indir = tmpdir.mkdir("onedir")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    subprocess.call(["mmd", "-i", str(outfile), "DIR1"])

    do_a_test(tmpdir, outfile, check_onedir)

def test_parse_onefile_system(tmpdir):
    indir = tmpdir.mkdir("onefilesystem")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])
    subprocess.call(["mattrib", "+s", "-i", str(outfile), "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile_system)

def test_parse_onefile_archive(tmpdir):
    indir = tmpdir.mkdir("onefilearchive")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])
    subprocess.call(["mattrib", "+a", "-i", str(outfile), "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile_archive)

def test_parse_onefile_hidden(tmpdir):
    indir = tmpdir.mkdir("onefilehidden")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])
    subprocess.call(["mattrib", "+h", "-i", str(outfile), "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile_hidden)

def test_parse_onefile_read_only(tmpdir):
    indir = tmpdir.mkdir("onefileread_only")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])
    subprocess.call(["mattrib", "+r", "-i", str(outfile), "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile_read_only)

def test_parse_onefile_all_attr(tmpdir):
    indir = tmpdir.mkdir("onefileallattr")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])
    subprocess.call(["mattrib", "+r", "-i", str(outfile), "::FOO"])
    subprocess.call(["mattrib", "+h", "-i", str(outfile), "::FOO"])
    subprocess.call(["mattrib", "+s", "-i", str(outfile), "::FOO"])
    subprocess.call(["mattrib", "+a", "-i", str(outfile), "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile_all_attr)

def test_parse_onefile_no_attr(tmpdir):
    indir = tmpdir.mkdir("onefilenoattr")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("foo\n")
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])
    subprocess.call(["mattrib", "-r", "-i", str(outfile), "::FOO"])
    subprocess.call(["mattrib", "-h", "-i", str(outfile), "::FOO"])
    subprocess.call(["mattrib", "-s", "-i", str(outfile), "::FOO"])
    subprocess.call(["mattrib", "-a", "-i", str(outfile), "::FOO"])

    do_a_test(tmpdir, outfile, check_onefile_no_attr)

def test_parse_manyfiles(tmpdir):
    indir = tmpdir.mkdir("manyfiles")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    for i in range(1, 18):
        num = "{:0>2}".format(str(i))
        numfile = os.path.join(str(indir), "file"+num)
        with open(numfile, "wb") as outfp:
            outfp.write("file" + num + "\n")
        subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), numfile, "::FILE"+num])

    do_a_test(tmpdir, outfile, check_manyfiles)

def test_parse_manyfiles_subdir(tmpdir):
    indir = tmpdir.mkdir("manyfilessubdir")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    subprocess.call(["mmd", "-i", str(outfile), "DIR1"])
    for i in range(1, 18):
        num = "{:0>2}".format(str(i))
        numfile = os.path.join(str(indir), "file"+num)
        with open(numfile, "wb") as outfp:
            outfp.write("file" + num + "\n")
        subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), numfile, "::DIR1/FILE"+num])

    do_a_test(tmpdir, outfile, check_manyfiles_subdir)

def test_parse_manydirs(tmpdir):
    indir = tmpdir.mkdir("manydirs")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    for i in range(1, 18):
        num = "{:0>2}".format(str(i))
        subprocess.call(["mmd", "-i", str(outfile), "DIR"+num])

    do_a_test(tmpdir, outfile, check_manydirs)

def test_parse_manydirs_subdir(tmpdir):
    indir = tmpdir.mkdir("manydirssubdir")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    subprocess.call(["mmd", "-i", str(outfile), "DIR1"])
    for i in range(1, 18):
        num = "{:0>2}".format(str(i))
        subprocess.call(["mmd", "-i", str(outfile), "DIR1/DIR"+num])

    do_a_test(tmpdir, outfile, check_manydirs_subdir)

def test_parse_multiple_cluster_file(tmpdir):
    indir = tmpdir.mkdir("multipleclusterfile")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    foofile = os.path.join(str(indir), "foo")
    with open(foofile, "wb") as outfp:
        outfp.write("0"*513)
    subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), foofile, "::FOO"])

    do_a_test(tmpdir, outfile, check_multiple_cluster_file)

def test_parse_manyfiles2_subdir(tmpdir):
    indir = tmpdir.mkdir("manyfiles2subdir")
    outfile = str(indir) + ".img"
    subprocess.call(["mkfs.msdos", "-C", str(outfile), "1440"])
    subprocess.call(["mmd", "-i", str(outfile), "DIR1"])
    for i in range(1, 32):
        num = "{:0>2}".format(str(i))
        numfile = os.path.join(str(indir), "file"+num)
        with open(numfile, "wb") as outfp:
            outfp.write("file" + num + "\n")
        subprocess.call(["mcopy", "-n", "-o", "-i", str(outfile), numfile, "::DIR1/FILE"+num])

    do_a_test(tmpdir, outfile, check_manyfiles2_subdir)
