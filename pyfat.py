# Copyright (C) 2016  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import struct
import collections
import os
import time

# FIXME: add a custom exception type
# FIXME: document all methods
# FIXME: add tests
# FIXME: add support for FAT16
# FIXME: add support for FAT32

def hexdump(st):
    '''
    A utility function to print a string in hex.

    Parameters:
     st - The string to print.
    Returns:
     A string containing the hexadecimal representation of the input string.
    '''
    return ':'.join(x.encode('hex') for x in st)

def ceiling_div(numer, denom):
    '''
    A function to do ceiling division; that is, dividing numerator by denominator
    and taking the ceiling.

    Parameters:
     numer - The numerator for the division.
     denom - The denominator for the division.
    Returns:
     The ceiling after dividing numerator by denominator.
    '''
    # Doing division and then getting the ceiling is tricky; we do upside-down
    # floor division to make this happen.
    # See https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python.
    return -(-numer // denom)

class FATDirectoryEntry(object):
    def __init__(self):
        self.initialized = False

    def parse(self, instr, parent, data_fp):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        if len(instr) != 32:
            raise Exception("Expected 32 bytes for the directory entry")

        (self.filename, self.extension, self.attributes, unused1,
         self.creation_time, self.creation_date, self.last_access_date, unused2,
         self.last_write_time, self.last_write_date, self.first_logical_cluster,
         self.file_size) = struct.unpack("=8s3sBHHHHHHHHL", instr)

        self.parent = parent
        self.children = []

        self.data_fp = data_fp

        self.initialized = True

    def _new(self, filename, extension, is_dir, first_logical_cluster, file_size, parent):
        if len(filename) > 8:
            raise Exception("Filename is too long (must be 8 or shorter)")

        if len(extension) > 3:
            raise Exception("Extension is too long (must be 3 or shorter)")

        tm = time.time()
        local = time.localtime(tm)
        year = local.tm_year - 1980
        month = local.tm_mon
        day = local.tm_mday

        date = (year << 9) | (month << 5) | (day & 0x1f)

        self.filename = filename
        self.extension = extension
        if is_dir:
            self.attributes = 0x10
        else:
            self.attributes = 0x20
        self.creation_time = 0
        self.creation_date = date
        self.last_access_date = date
        self.last_write_time = 0
        self.last_write_date = date
        self.first_logical_cluster = first_logical_cluster
        self.file_size = file_size

        self.parent = parent
        self.children = []

        self.initialized = True

    def new_root(self):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        self._new('        ', '   ', True, 0, 0, None)

    def new_file(self, data_fp, length, parent, filename, extension, first_logical_cluster):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        self.data_fp = data_fp
        self._new(filename, extension, False, first_logical_cluster, length, parent)


    def new_dir(self, parent, filename, extension, first_logical_cluster):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        self._new(filename, extension, True, first_logical_cluster, 0, parent)

    def new_dot(self, parent, first_logical_cluster):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        self._new('.', '', True, first_logical_cluster, 0, parent)

    def new_dotdot(self, parent):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        self._new('..', '', True, 0, 0, parent)

    def is_dir(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return self.attributes & 0x10

    def is_dot(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return self.filename == '.'

    def is_dotdot(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return self.filename == '..'

    def add_child(self, child):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        if not self.is_dir():
            raise Exception("Can only add children to directories")

        if self.is_dot() or self.is_dotdot():
            raise Exception("Cannot add children to dot or dotdot")

        self.children.append(child)

    def remove_child(self, name, ext):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        expandname = "{:<8}".format(name)
        expandext = "{:<3}".format(ext)

        foundindex = None
        for index,child in enumerate(self.children):
            if child.filename == expandname and child.extension == expandext:
                foundindex = index
                break

        if foundindex is None:
            raise Exception("Could not find child")

        del self.children[foundindex]

    def directory_record(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return struct.pack("=8s3sBHHHHHHHHL", "{:<8}".format(self.filename),
                           "{:<3}".format(self.extension),
                           self.attributes, 0, self.creation_time,
                           self.creation_date, self.last_access_date, 0,
                           self.last_write_time, self.last_write_date,
                           self.first_logical_cluster, self.file_size)

    def get_data_fp(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return self.data_fp

class FAT12(object):
    def __init__(self):
        self.initialized = False

    def parse(self, fatstring):
        if self.initialized:
            raise Exception("This object is already initialized")

        total_entries = 512 * 9 / 1.5 # Total bytes in FAT (512*9) / bytes per entry (1.5)

        self.fat = [0x0]*int(total_entries)
        self.fat[0] = 0xf0
        self.fat[1] = 0xff

        curr = 2
        while curr < total_entries:
            offset = (3*curr)/2
            low,high = struct.unpack("=BB", fatstring[offset:offset+2])
            if curr % 2 == 0:
                # even
                fat_entry = ((high & 0x0f) << 8) | low
            else:
                # odd
                fat_entry = (high << 4) | (low >> 4)

            self.fat[curr] = fat_entry
            curr += 1

        self.initialized = True

    def new(self):
        if self.initialized:
            raise Exception("This object is already initialized")

        total_entries = 512 * 9 / 1.5 # Total bytes in FAT (512*9) / bytes per entry (1.5)

        self.fat = [0x0]*int(total_entries)
        self.fat[0] = 0xf0
        self.fat[1] = 0xff

        self.initialized = True

    def get_cluster_list(self, first_logical_cluster):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        physical_clusters = []
        curr = first_logical_cluster
        while True:
            physical_clusters.append(33 + curr - 2)
            if self.fat[curr] in [0xff8, 0xff9, 0xffa, 0xffb, 0xffc, 0xffd, 0xffe, 0xfff]:
                # This is the end!
                break

            curr = self.fat[curr]

        return physical_clusters

    def add_file(self, length):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        # Update the FAT to hold the data for the file
        num_clusters = ceiling_div(length, 512)
        first_cluster = None

        last = None
        curr = 2
        while curr < len(self.fat) and num_clusters > 0:
            if self.fat[curr] == 0x0:
                if first_cluster is None:
                    first_cluster = curr

                if last is not None:
                    self.fat[last] = curr

                last = curr

                num_clusters -= 1

            curr += 1

        if first_cluster is None or num_clusters != 0:
            raise Exception("No space left on device")

        # Set the last cluster
        self.fat[last] = 0xfff

        return first_cluster

    def add_dir(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        first_cluster = None

        curr = 2
        while curr < len(self.fat) and first_cluster is None:
            if self.fat[curr] == 0x0:
                first_cluster = curr
                self.fat[curr] = 0xfff

            curr += 1

        if first_cluster is None:
            raise Exception("No space left on device")

        return first_cluster

    def record(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        ret = '\xf0\xff'

        for byte in range(3, 512*9, 3):
            curr = byte * 2/3
            ret += struct.pack("=B", self.fat[curr] & 0xff)
            ret += struct.pack("=B", ((self.fat[curr] >> 8) | (self.fat[curr + 1] << 4)) & 0xff)
            ret += struct.pack("=B", self.fat[curr + 1] & 0xff)

        return ret

class PyFat(object):
    FAT12 = 0
    FAT16 = 1
    FAT32 = 2

    # This boot code was taken from dosfstools
    BOOT_CODE = "\x0e\x1f\xbe\x5b\x7c\xac\x22\xc0\x74\x0b\x56\xb4\x0e\xbb\x07\x00\xcd\x10\x5e\xeb\xf0\x32\xe4\xcd\x16\xcd\x19\xeb\xfeThis is not a bootable disk.  Please insert a bootable floppy and\r\npress any key to try again ... \r\n"

    def __init__(self):
        self.root_dir_entries = []
        self.initialized = False

    def open(self, infp, size_in_kb):
        if self.initialized:
            raise Exception("This object is already initialized")

        if size_in_kb != 1440:
            raise Exception("Only 1.44MB floppy disks supported")

        self.infp = infp

        infp.seek(0)

        boot_sector = infp.read(512)

        (self.jmp_boot, self.oem_name, self.bytes_per_sector,
         self.sectors_per_cluster, self.reserved_sectors, self.num_fats,
         self.max_root_dir_entries, self.sector_count, self.media,
         self.sectors_per_fat, self.sectors_per_track, self.num_heads,
         self.hidden_sectors, self.total_sector_count_32, self.drive_num,
         unused1, self.boot_sig, self.volume_id, self.volume_label,
         self.fs_type, self.boot_code, sig) = struct.unpack("=3s8sHBHBHHBHHHLLBBBL11s8s448sH", boot_sector)

        self.jmp_boot2 = struct.unpack(">L", self.jmp_boot + '\x00')

        # FIXME: check that jmp_boot is 0xeb, 0x??, 0x90

        if self.bytes_per_sector != 512:
            raise Exception("Expected 512 bytes per sector")

        if self.sectors_per_cluster != 1:
            raise Exception("Expected 1 sector per cluster")

        if self.media not in [0xf0, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff]:
            raise Exception("Invalid media type")

        if self.num_fats != 2:
            raise Exception("Expected 2 FATs")

        if self.max_root_dir_entries != 224:
            raise Exception("Expected 224 root directory entries")

        if self.drive_num not in [0x00, 0x80]:
            raise Exception("Invalid drive number")

        if self.sectors_per_fat != 9:
            raise Exception("Expected sectors per FAT to be 9")

        if self.total_sector_count_32 != 0:
            raise Exception("Expected the total sector count 32 to be 0")

        if self.fs_type != "FAT12   ":
            raise Exception("Invalid filesystem type")

        if sig != 0xaa55:
            raise Exception("Invalid signature")

        self.size_in_kb = size_in_kb

        # The following determines whether this is FAT12, FAT16, or FAT32
        root_dir_sectors = ((self.max_root_dir_entries * 32) + (self.bytes_per_sector - 1)) / self.bytes_per_sector
        if self.sectors_per_fat != 0:
            fat_size = self.sectors_per_fat
        else:
            raise PyIsoException("Only support FAT12 right now!")

        if self.sector_count != 0:
            total_sectors = self.sector_count
        else:
            total_sectors = self.total_sector_count_32

        data_sec = total_sectors - (self.reserved_sectors + (self.num_fats * fat_size) + root_dir_sectors)
        count_of_clusters = data_sec / self.sectors_per_cluster

        if count_of_clusters < 4085:
            self.fat_type = self.FAT12
        elif count_of_clusters < 65525:
            self.fat_type = self.FAT16
        else:
            self.fat_type = self.FAT32

        # Read the first FAT
        first_fat = infp.read(512 * 9)

        # Read the second FAT
        second_fat = infp.read(512 * 9)

        if first_fat != second_fat:
            raise Exception("The first FAT and second FAT do not agree; corrupt FAT filesystem")

        self.fat = FAT12()
        self.fat.parse(first_fat)

        # Now walk the root directory entry
        self.root = FATDirectoryEntry()
        self.root.parse('           \x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', None, infp)
        root_cluster_list = []
        for i in range(19, 19+14):
            root_cluster_list.append(i)

        dirs = collections.deque([(self.root, root_cluster_list)])
        while dirs:
            currdir,cluster_list = dirs.popleft()

            # Read all of the data for this directory
            data = ''
            for cluster in cluster_list:
                infp.seek(cluster * 512)
                data += infp.read(512)

            read = 0
            while read < len(data):
                dir_entry = data[read:read+32]
                read += 32

                if dir_entry[0] == '\x00':
                    # Empty dir entry, done reading
                    break
                elif dir_entry[0] == '\xe5':
                    # Empty dir entry, skip to next one
                    continue

                ent = FATDirectoryEntry()
                ent.parse(dir_entry, currdir, infp)
                currdir.add_child(ent)
                if ent.is_dir():
                    dirs.append((ent, self.fat.get_cluster_list(ent.first_logical_cluster)))

        self.initialized = True

    def _find_record(self, path):
        if path[0] != '/':
            raise Exception("Must be a path starting with /")

        if path == '/':
            raise Exception("Cannot write data from the root")

       # Split the path along the slashes
        splitpath = path.split('/')
        # Skip past the first one, since it is always empty.
        splitindex = 1

        currpath = splitpath[splitindex]
        splitindex += 1
        children = self.root.children
        index = 0
        while index < len(children):
            child = children[index]
            index += 1

            if child.filename.rstrip() != currpath:
                continue

            if splitindex == len(splitpath):
                # We have to remove one from the index since we incremented it
                # above.
                return child,index-1
            else:
                if child.is_dir():
                    children = child.children
                    index = 0
                    currpath = splitpath[splitindex]
                    splitindex += 1

        raise Exception("Could not find path %s" % (path))

    def get_and_write_file(self, path, outfp):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        child,index = self._find_record(path)

        data_fp = child.get_data_fp()

        for cluster in self.fat.get_cluster_list(child.first_logical_cluster):
            data_fp.seek(cluster * 512)
            outfp.write(data_fp.read(512))

    def new(self, size_in_kb=1440):
        if self.initialized:
            raise Exception("This object is already initialized")

        if size_in_kb != 1440:
            raise Exception("Only size 1440 disks supported")

        self.jmp_boot = '\x00\xeb\x3c\x90'
        self.oem_name = 'pyfat   '
        self.bytes_per_sector = 512
        self.sectors_per_cluster = 1
        self.reserved_sectors = 1
        self.num_fats = 2
        self.max_root_dir_entries = 224
        self.sector_count = 2880
        self.media = 0xf0
        self.sectors_per_fat = 9
        self.sectors_per_track = 18
        self.num_heads = 2
        self.hidden_sectors = 0
        self.total_sector_count_32 = 0
        self.drive_num = 0
        self.boot_sig = 41
        self.volume_id = 4248983325
        self.volume_label = "NO NAME    "
        self.fs_type = "FAT12   "
        self.boot_code = self.BOOT_CODE

        self.root = FATDirectoryEntry()
        self.root.new_root()

        self.fat = FAT12()
        self.fat.new()

        self.size_in_kb = size_in_kb

        self.initialized = True

    def _name_and_parent_from_path(self, path):
        if path[0] != '/':
            raise Exception("Must be a path starting with /")

        # First we need to find the parent of this directory, and add this
        # one as a child.
        splitpath = path.split('/')
        # Pop off the front, as it is always blank.
        splitpath.pop(0)
        # Now take the name off.
        name = splitpath.pop()
        if len(splitpath) == 0:
            # This is a new directory under the root, add it there
            parent = self.root
        else:
            parent,index = self._find_record('/' + '/'.join(splitpath))

        return (name, parent)

    def add_fp(self, path, infp, length):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        filename,parent = self._name_and_parent_from_path(path)

        name,ext = os.path.splitext(filename)
        if ext[0] == '.':
            ext = ext[1:]

        first_cluster = self.fat.add_file(length)

        child = FATDirectoryEntry()
        child.new_file(infp, length, parent, name, ext, first_cluster)

        parent.add_child(child)

        # FIXME: when adding a new file, we may have to expand the parent size and the size in the FAT

    def add_dir(self, path):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        filename,parent = self._name_and_parent_from_path(path)

        name,ext = os.path.splitext(filename)

        first_cluster = self.fat.add_dir()

        child = FATDirectoryEntry()
        child.new_dir(parent, name, ext, first_cluster)

        parent.add_child(child)

        dot = FATDirectoryEntry()
        dot.new_dot(parent, first_cluster)
        child.add_child(dot)

        dotdot = FATDirectoryEntry()
        dotdot.new_dotdot(parent)
        child.add_child(dotdot)

    # FIXME: implement the ability to manipulate attributes

    # FIXME: add the ability to remove directories

    def rm_file(self, path):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        filename,parent = self._name_and_parent_from_path(path)

        name,ext = os.path.splitext(filename)

        parent.remove_child(name, ext)

        # FIXME: we need to remove this entries FAT entry
        # FIXME: when removing a child, we may have to shrink the parent size in the FAT

    def write(self, outfp):
        if not self.initialized:
            raise Exception("This object is not yet initialized")

        # First write out the boot entry
        outfp.seek(0 * 512)
        outfp.write(struct.pack("=3s8sHBHBHHBHHHLLBBBL11s8s448sH", self.jmp_boot,
                                self.oem_name, self.bytes_per_sector,
                                self.sectors_per_cluster, self.reserved_sectors,
                                self.num_fats, self.max_root_dir_entries,
                                self.sector_count, self.media,
                                self.sectors_per_fat,
                                self.sectors_per_track, self.num_heads,
                                self.hidden_sectors,
                                self.total_sector_count_32, self.drive_num,
                                0, self.boot_sig, self.volume_id,
                                self.volume_label, self.fs_type, self.boot_code, 0xaa55))

        # Now write out the first FAT
        outfp.seek(1 * 512)
        outfp.write(self.fat.record())

        # Now write out the second FAT
        outfp.seek(10 * 512)
        outfp.write(self.fat.record())

        # Now write out the directory entries
        root_cluster_list = []
        for i in range(19, 19+14):
            root_cluster_list.append(i)

        dirs = collections.deque([(self.root, root_cluster_list)])
        while dirs:
            currdir,physical_clusters = dirs.popleft()

            cluster_iter = iter(physical_clusters)
            outfp.seek(cluster_iter.next() * 512)
            cluster_offset = 0
            for child in currdir.children:
                if cluster_offset + 32 > 512:
                    cluster_offset = 0
                    outfp.seek(cluster_iter.next() * 512)

                outfp.write(child.directory_record())
                cluster_offset += 32

                if child.is_dir() and not (child.is_dot() or child.is_dotdot()):
                    dirs.append((child, self.fat.get_cluster_list(child.first_logical_cluster)))

        # Now write out the files
        dirs = collections.deque([self.root])
        while dirs:
            currdir = dirs.popleft()

            for child in currdir.children:
                if child.is_dir():
                    dirs.append(child)
                else:
                    data_fp = child.get_data_fp()
                    data_cluster = 0

                    # An actual file we have to write out
                    for cluster in self.fat.get_cluster_list(child.first_logical_cluster):
                        data_fp.seek(data_cluster * 512)
                        outfp.seek(cluster * 512)
                        outfp.write(data_fp.read(512))
                        data_cluster += 1

        # Finally, truncate the file out to its final size
        outfp.write('\x00'*(self.size_in_kb * 1024 - outfp.tell()))

    def close(self):
        if not self.initialized:
            raise Exception("Can only call close on an already open object")

        self.initialized = False
