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

'''
Main PyFat class and support classes and utilities.
'''

import struct
import collections
import os
import time

# FIXME: add support for FAT16
# FIXME: add support for FAT32
# FIXME: add support for editing a filesystem in-place

class PyFatException(Exception):
    '''
    The custom Exception class for PyFat.
    '''
    def __init__(self, msg):
        Exception.__init__(self, msg)

def hexdump(instring):
    '''
    A utility function to print a string in hex.

    Parameters:
     st - The string to print.
    Returns:
     A string containing the hexadecimal representation of the input string.
    '''
    return ':'.join(x.encode('hex') for x in instring)

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
    '''
    The class that represents a single FAT Directory Entry.
    '''
    DATA_ON_ORIGINAL_FAT = 1
    DATA_IN_EXTERNAL_FP = 2

    def __init__(self):
        self.initialized = False

    def parse(self, instr, parent, data_fp):
        '''
        Method to parse a directory entry out of a string.  The string must be
        exactly 32 bytes long for this to succeed.

        Parameters:
         instr - The string to parse.
         parent - The parent of this directory entry.
         data_fp - The file pointer for the backing file that contains this
                   directory entry.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This directory entry is already initialized")

        if len(instr) != 32:
            raise PyFatException("Expected 32 bytes for the directory entry")

        (self.filename, self.extension, self.attributes, unused1,
         self.creation_time, self.creation_date, self.last_access_date, unused2,
         self.last_write_time, self.last_write_date, self.first_logical_cluster,
         self.file_size) = struct.unpack("=8s3sBHHHHHHHHL", instr)

        self.parent = parent
        self.children = []

        if not self.attributes & 0x10:
            # Save the data pointer and original data location only for files
            self.data_fp = data_fp
            self.original_data_location = self.DATA_ON_ORIGINAL_FAT

        self.initialized = True

    def _new(self, filename, extension, is_dir, first_logical_cluster, file_size, parent):
        '''
        Internal method to create a new directory entry.

        Parameters:
         filename - The filename to give to this directory entry; it must be 8 characters or less.
         extension - The extension to give to this directory entry; it must be 3 characters or less.
         is_dir - Whether this new entry is a directory.
         first_logical_cluster - The first logical cluster in the FAT for this directory entry.
         file_size - The file size of this directory entry.
         parent - The parent of this directory entry.
        Returns:
         Nothing.
        '''
        if len(filename) > 8:
            raise PyFatException("Filename is too long (must be 8 or shorter)")

        if len(extension) > 3:
            raise PyFatException("Extension is too long (must be 3 or shorter)")

        time_since_epoch = time.time()
        local = time.localtime(time_since_epoch)
        year = local.tm_year - 1980
        month = local.tm_mon
        day = local.tm_mday

        date = (year << 9) | (month << 5) | (day & 0x1f)

        self.filename = "{:<8}".format(filename)
        self.extension = "{:<3}".format(extension)
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
        '''
        A method to create a new root.  Note that every FAT filesystem must have
        one and only one root.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This directory entry is already initialized")

        self._new('        ', '   ', True, 0, 0, None)

    def new_file(self, data_fp, length, parent, filename, extension, first_logical_cluster):
        '''
        A method to create a new file.

        Parameters:
         data_fp - The file-like object that contains the data for this file.
         length - The length of this directory entry.
         parent - The parent of this directory entry.
         filename - The filename to give to this directory entry; it must be 8 characters or less.
         extension - The extension to give to this directory entry; it must be 3 characters or less.
         first_logical_cluster - The first logical cluster in the FAT for this directory entry.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This directory entry is already initialized")

        self.data_fp = data_fp
        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self._new(filename, extension, False, first_logical_cluster, length, parent)


    def new_dir(self, parent, filename, extension, first_logical_cluster):
        '''
        A method to create a new directory.

        Parameters:
         parent - The parent of the new directory.
         filename - The filename for the new directory.
         extension - The extension for the new directory.
         first_logical_cluster - The first logical cluster for the new directory.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This directory entry is already initialized")

        self._new(filename, extension, True, first_logical_cluster, 0, parent)

    def new_dot(self, parent, first_logical_cluster):
        '''
        A method to create a new '.' directory.  Every directory must start
        with a '.' and '..' entry.

        Parameters:
         parent - The parent for the new '.' directory.
         first_logical_cluster - The first logical cluster for the new '.' directory.  Note that this will be the same as the first logical cluster for the parent.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This directory entry is already initialized")

        self._new('.', '', True, first_logical_cluster, 0, parent)

    def new_dotdot(self, parent):
        '''
        A method to create a new '..' directory.  Every directory must start
        with a '.' and '..' entry.

        Parameters:
         parent - The parent for the new '..' directory.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This directory entry is already initialized")

        self._new('..', '', True, 0, 0, parent)

    def is_dir(self):
        '''
        A method to determine whether this entry is a directory.

        Parameters:
         None.
        Returns:
         True if this entry is a directory, False otherwise.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        return self.attributes & 0x10

    def is_dot(self):
        '''
        A method to determine whether this entry is a '.' entry.

        Parameters:
         None.
        Returns:
         True if this entry is a '.' entry, False otherwise.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        return self.filename == '.       '

    def is_dotdot(self):
        '''
        A method to determine whether this entry is a '..' entry.

        Parameters:
         None.
        Returns:
         True if this entry is a '..' entry, False otherwise.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        return self.filename == '..      '

    def add_child(self, child):
        '''
        A method to add a new child to this entry.  This is only valid if this
        entry is a directory, and is not '.' or '..'.

        Parameters:
         child - Directory entry object to as child of this entry.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        if not self.is_dir():
            raise PyFatException("Can only add children to directories")

        if self.is_dot() or self.is_dotdot():
            raise PyFatException("Cannot add children to dot or dotdot")

        if self.parent is None and len(self.children) == 224:
            # The root entry has a fixed limit of 224 entries.
            raise PyFatException("Too many files in the root entry (max is 224)")

        self.children.append(child)

    def remove_child(self, index):
        '''
        A method to remove a child from this entry.  This is only valid if
        this entry is a directory, and is not '.' or '..'.

        Parameters:
         index - The index of the child in this directory entry's array.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        if not self.is_dir():
            raise PyFatException("Can only remove children from directories")

        if self.is_dot() or self.is_dotdot():
            raise PyFatException("Cannot remove children from dot or dotdot")

        del self.children[index]

    def record(self):
        '''
        A method to generate a string representing this directory entry.

        Parameters:
         None.
        Returns:
         A string representing this directory entry.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        return struct.pack("=8s3sBHHHHHHHHL", "{:<8}".format(self.filename),
                           "{:<3}".format(self.extension),
                           self.attributes, 0, self.creation_time,
                           self.creation_date, self.last_access_date, 0,
                           self.last_write_time, self.last_write_date,
                           self.first_logical_cluster, self.file_size)

    def set_hidden(self):
        '''
        A method to set the hidden attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes |= 0x02

    def set_archive(self):
        '''
        A method to set the archive attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes |= 0x20

    def set_system(self):
        '''
        A method to set the system attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes |= 0x04

    def set_read_only(self):
        '''
        A method to set the read only attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes |= 0x01

    def clear_hidden(self):
        '''
        A method to clear the hidden attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes &= ~0x02

    def clear_system(self):
        '''
        A method to clear the system attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes &= ~0x04

    def clear_archive(self):
        '''
        A method to clear the archive attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes &= ~0x20

    def clear_read_only(self):
        '''
        A method to clear the read only attribute on this directory entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This directory entry is not yet initialized")

        self.attributes &= ~0x01

class FAT12(object):
    '''
    The class that represents the FAT (File Allocation Table) for this
    filesystem.  This class represents the 12-bit FAT.
    '''
    def __init__(self):
        self.initialized = False

    def parse(self, fatstring):
        '''
        Method to parse a FAT out of a string.  The string must be
        exactly 32 bytes long for this to succeed.

        Parameters:
         fatstr - The string to parse.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This object is already initialized")

        if len(fatstring) != 512 * 9:
            raise PyFatException("Invalid length on FAT12 string")

        total_entries = 512 * 9 / 1.5 # Total bytes in FAT (512*9) / bytes per entry (1.5)

        self.fat = [0x0]*int(total_entries)
        self.fat[0] = 0xff0
        self.fat[1] = 0xfff

        curr = 2
        while curr < total_entries:
            offset = (3*curr)/2
            low, high = struct.unpack("=BB", fatstring[offset:offset+2])
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
        '''
        A method to create a new FAT12.  All entries are initially set to 0
        (unallocated), except for the first two.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This object is already initialized")

        total_entries = 512 * 9 / 1.5 # Total bytes in FAT (512*9) / bytes per entry (1.5)

        self.fat = [0x0]*int(total_entries)
        self.fat[0] = 0xff0
        self.fat[1] = 0xfff

        self.initialized = True

    def get_cluster_list(self, first_logical_cluster):
        '''
        A method to get the physical cluster list, given the first logical
        cluster in a chain.

        Parameters:
         first_logical_cluster - The logical cluster to start with.
        Returns:
         A list containing all of the physical cluster locations for this chain.
        '''
        # FIXME: we should make this a generator

        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        physical_clusters = []
        curr = first_logical_cluster
        while True:
            physical_clusters.append(33 + curr - 2)
            if self.fat[curr] in [0xff8, 0xff9, 0xffa, 0xffb, 0xffc, 0xffd, 0xffe, 0xfff]:
                # This is the end!
                break

            curr = self.fat[curr]

        return physical_clusters

    def add_entry(self, length):
        '''
        A method to add a new entry to the FAT.  As many entries as necessary
        to cover the length will be allocated and linked together.

        Parameters:
         length - The length of the entry to be allocated.
        Returns:
         The first logical cluster.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

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
            raise PyFatException("No space left on device")

        # Set the last cluster
        self.fat[last] = 0xfff

        return first_cluster

    def expand_entry(self, first_logical_cluster):
        '''
        A method to expand the number of clusters assigned to the entry starting
        at the given logical cluster.

        Parameters:
         first_logical_cluster - The first logical cluster of the entry to expand.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        old_last_entry = None
        curr = first_logical_cluster
        while True:
            if self.fat[curr] in [0xff8, 0xff9, 0xffa, 0xffb, 0xffc, 0xffd, 0xffe, 0xfff]:
                # OK, we've found the last entry for this entry.  Let's save
                # the offset so we can come back and update it once we've found
                # the new cluster.
                old_last_entry = curr
                break

            curr = self.fat[curr]

        if old_last_entry is None:
            raise PyFatException("Old last entry not found!")

        # Now that we have the old last entry, let's scan the entire FAT for
        # a free cluster.
        curr = 2
        while curr < len(self.fat):
            if self.fat[curr] == 0x0:
                # OK we've found a free entry; update it to be the end, update
                # the last entry to point to this, and get out of here.
                self.fat[old_last_entry] = curr
                self.fat[curr] = 0xfff
                return

            curr += 1

        raise PyFatException("No space left on device")

    def remove_entry(self, first_logical_cluster):
        '''
        A method to remove a chain of clusters from the FAT.

        Parameters:
         first_logical_cluster - The cluster to start from.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        curr = first_logical_cluster
        while True:
            if self.fat[curr] in [0xff8, 0xff9, 0xffa, 0xffb, 0xffc, 0xffd, 0xffe, 0xfff]:
                # This is the end!
                self.fat[curr] = 0
                break

            nextcluster = self.fat[curr]
            self.fat[curr] = 0
            curr = nextcluster

    def record(self):
        '''
        A method to generate a string representing this File Allocation Table.

        Parameters:
         None.
        Returns:
         A string representing this File Allocation Table.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        ret = '\xf0\xff\xff'

        for byte in range(3, 512*9, 3):
            curr = byte * 2/3
            ret += struct.pack("=B", self.fat[curr] & 0xff)
            ret += struct.pack("=B", ((self.fat[curr] >> 8) | (self.fat[curr + 1] << 4)) & 0xff)
            ret += struct.pack("=B", self.fat[curr + 1] & 0xff)

        return ret

class PyFat(object):
    '''
    The main class to open or create FAT filesystems.
    '''
    FAT12 = 0
    FAT16 = 1
    FAT32 = 2

    # This boot code was taken from dosfstools
    BOOT_CODE = "\x0e\x1f\xbe\x5b\x7c\xac\x22\xc0\x74\x0b\x56\xb4\x0e\xbb\x07\x00\xcd\x10\x5e\xeb\xf0\x32\xe4\xcd\x16\xcd\x19\xeb\xfeThis is not a bootable disk.  Please insert a bootable floppy and\r\npress any key to try again ... \r\n"

    def __init__(self):
        self.orig_fp = None
        self.initialized = False

    def open(self, filename):
        '''
        A method to open up an existing FAT filesystem.

        Parameters:
         filename - The filename that contains the FAT filesystem to open.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This object is already initialized")

        self.orig_fp = open(filename, 'rb')

        self.orig_fp.seek(0, os.SEEK_END)
        size_in_kb = self.orig_fp.tell() / 1024

        if size_in_kb != 1440:
            raise PyFatException("Only 1.44MB filesystems are supported")

        self.orig_fp.seek(0)

        boot_sector = self.orig_fp.read(512)

        (self.jmp_boot, self.oem_name, self.bytes_per_sector,
         self.sectors_per_cluster, self.reserved_sectors, self.num_fats,
         self.max_root_dir_entries, self.sector_count, self.media,
         self.sectors_per_fat, self.sectors_per_track, self.num_heads,
         self.hidden_sectors, self.total_sector_count_32, self.drive_num,
         unused1, self.boot_sig, self.volume_id, self.volume_label,
         self.fs_type, self.boot_code, sig) = struct.unpack("=3s8sHBHBHHBHHHLLBBBL11s8s448sH", boot_sector)

        self.jmp_boot2 = struct.unpack(">L", self.jmp_boot + '\x00')

        # FIXME: check that jmp_boot is 0xeb, 0x??, 0x90

        if self.bytes_per_sector not in [512, 1024, 2048, 4096]:
            raise PyFatException("Expected 512, 1024, 2048, or 4096 bytes per sector")

        if self.sectors_per_cluster not in [1, 2, 4, 8, 16, 32, 64, 128]:
            raise PyFatException("Expected 1, 2, 4, 8, 16, 32, 64, or 128 sector per cluster")

        if self.reserved_sectors == 0:
            raise PyFatException("Number of reserved sectors must not be 0")

        if self.media not in [0xf0, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff]:
            raise PyFatException("Invalid media type")

        if self.num_fats not in [1, 2]:
            raise PyFatException("Expected 1 or 2 FATs")

        if self.drive_num not in [0x00, 0x80]:
            raise PyFatException("Invalid drive number")

        if self.sectors_per_fat != 9:
            raise PyFatException("Expected sectors per FAT to be 9")

        if self.total_sector_count_32 != 0:
            raise PyFatException("Expected the total sector count 32 to be 0")

        if self.fs_type != "FAT12   ":
            raise PyFatException("Invalid filesystem type")

        if sig != 0xaa55:
            raise PyFatException("Invalid signature")

        self.size_in_kb = size_in_kb

        # The following determines whether this is FAT12, FAT16, or FAT32
        self.root_dir_sectors = ((self.max_root_dir_entries * 32) + (self.bytes_per_sector - 1)) / self.bytes_per_sector
        if self.sectors_per_fat != 0:
            fat_size = self.sectors_per_fat
        else:
            raise PyFatException("Only support FAT12 right now!")

        if self.sector_count != 0:
            total_sectors = self.sector_count
        else:
            total_sectors = self.total_sector_count_32

        data_sec = total_sectors - (self.reserved_sectors + (self.num_fats * fat_size) + self.root_dir_sectors)
        count_of_clusters = data_sec / self.sectors_per_cluster

        if count_of_clusters < 4085:
            self.fat_type = self.FAT12
        elif count_of_clusters < 65525:
            self.fat_type = self.FAT16
        else:
            self.fat_type = self.FAT32

        # Read the first FAT
        first_fat = self.orig_fp.read(self.bytes_per_sector * self.sectors_per_fat)

        if self.num_fats == 2:
            # Read the second FAT if it exists
            second_fat = self.orig_fp.read(self.bytes_per_sector * self.sectors_per_fat)

            if first_fat != second_fat:
                raise PyFatException("The first FAT and second FAT do not agree; corrupt FAT filesystem")

        self.bytes_per_cluster = self.bytes_per_sector * self.sectors_per_cluster

        self.fat = FAT12()
        self.fat.parse(first_fat)

        # Now walk the root directory entry
        self.root = FATDirectoryEntry()
        self.root.parse('           \x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', None, self.orig_fp)
        root_cluster_list = []
        # The first root directory sector is preceded by:
        # BPB consisting of 1 sector
        # First FAT consisting of self.sectors_per_fat sectors
        # (Optional) Second FAT consisting of self.sectors_per_fat sectors
        first_root_dir_sector = 1 + (self.num_fats * self.sectors_per_fat)
        for i in range(first_root_dir_sector, first_root_dir_sector+self.root_dir_sectors):
            root_cluster_list.append(i)

        dirs = collections.deque([(self.root, root_cluster_list)])
        while dirs:
            currdir, cluster_list = dirs.popleft()

            # Read all of the data for this directory
            data = ''
            for cluster in cluster_list:
                self.orig_fp.seek(cluster * self.bytes_per_cluster)
                data += self.orig_fp.read(self.bytes_per_cluster)

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
                ent.parse(dir_entry, currdir, self.orig_fp)
                currdir.add_child(ent)
                if ent.is_dir() and not (ent.is_dot() or ent.is_dotdot()):
                    dirs.append((ent, self.fat.get_cluster_list(ent.first_logical_cluster)))

        self.initialized = True

    def _find_record(self, path):
        '''
        An internal method to find a FAT directory entry based on a given path.
        The path should be of the form '/dir1/file'.

        Parameters:
         path - The path to find in the filesystem.
        Returns:
         A tuple of the FAT directory entry object and index of the object into the parent's child list.
        '''
        if path[0] != '/':
            raise PyFatException("Must be a path starting with /")

        if path == '/':
            return self.root, None

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

            fullname = child.filename.rstrip()
            if len(child.extension.rstrip()) > 0:
                fullname += "." + child.extension.rstrip()
            if fullname != currpath:
                continue

            if splitindex == len(splitpath):
                # We have to remove one from the index since we incremented it
                # above.
                return child, index-1
            else:
                if child.is_dir():
                    children = child.children
                    index = 0
                    currpath = splitpath[splitindex]
                    splitindex += 1

        raise PyFatException("Could not find path %s" % (path))

    def get_and_write_file(self, fat_path, local_path):
        '''
        A method to get the data from a file on the FAT filesystem.
        The path should be of the form '/dir1/file'.

        Parameters:
         fat_path - The path on the FAT filesystem of the file data to get.
         local_path - The local_path in which to write the data.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(fat_path)

        if child.is_dir():
            raise PyFatException("Cannot get data from a directory")

        with open(local_path, 'wb') as outfp:
            new_cluster_list = self.fat.get_cluster_list(child.first_logical_cluster)
            if child.original_data_location == child.DATA_ON_ORIGINAL_FAT:
                # If this is a file that was on the original filesystem,
                # then we haven't modified the cluster list and the
                # original is the same as the new.
                orig_cluster_list = new_cluster_list
            elif child.original_data_location == child.DATA_IN_EXTERNAL_FP:
                orig_cluster_list = range(0, ceiling_div(child.file_size, self.bytes_per_cluster))

            left = child.file_size
            index = 0
            while index < len(orig_cluster_list) and left > 0:
                thisread = self.bytes_per_cluster
                if left < thisread:
                    thisread = left

                child.data_fp.seek(orig_cluster_list[index] * self.bytes_per_cluster)
                outfp.seek(index * self.bytes_per_cluster)
                outfp.write(child.data_fp.read(thisread))

                left -= thisread
                index += 1

    def new(self, size_in_kb=1440):
        '''
        A method to create a new FAT filesystem.

        Parameters:
         size_in_kb - The size of the filesystem in kilobytes.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyFatException("This object is already initialized")

        if size_in_kb != 1440:
            raise PyFatException("Only size 1440 disks supported")

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
        self.bytes_per_cluster = self.bytes_per_sector * self.sectors_per_cluster
        self.root_dir_sectors = ((self.max_root_dir_entries * 32) + (self.bytes_per_sector - 1)) / self.bytes_per_sector

        self.root = FATDirectoryEntry()
        self.root.new_root()

        self.fat = FAT12()
        self.fat.new()

        self.size_in_kb = size_in_kb

        self.initialized = True

    def _name_and_parent_from_path(self, path):
        '''
        An internal method to get the original name and parent given a pathname.

        Parameters:
         path - The path to find the parent and name for.
        Returns:
         A tuple of the name and the parent.
        '''
        if path[0] != '/':
            raise PyFatException("Must be a path starting with /")

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
            parent, index = self._find_record('/' + '/'.join(splitpath))

        return (name, parent)

    def add_file(self, fat_path, local_path):
        '''
        A method to add a new file to the filesystem.

        Parameters:
         fat_path - The path on the FAT filesystem to add the file.
         local_path - The local path that the file data should come from.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        infp = open(local_path, 'rb')
        length = os.fstat(infp.fileno()).st_size

        filename, parent = self._name_and_parent_from_path(fat_path)

        name, ext = os.path.splitext(filename)
        if len(ext) > 0 and ext[0] == '.':
            ext = ext[1:]

        first_cluster = self.fat.add_entry(length)

        child = FATDirectoryEntry()
        child.new_file(infp, length, parent, name, ext, first_cluster)

        parent.add_child(child)

        # We only try to expand directories that are not the root.
        if parent.parent is not None:
            if len(parent.children) > 1 and (len(parent.children) % (512/32)) == 1:
                # Here, we need to add another entry to the FAT filesystem.
                self.fat.expand_entry(parent.first_logical_cluster)

    def add_dir(self, path):
        '''
        A method to add a new directory to the FAT filesystem.

        Parameters:
         path - The path at which to create the new directory.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        filename, parent = self._name_and_parent_from_path(path)

        name, ext = os.path.splitext(filename)

        first_cluster = self.fat.add_entry(self.bytes_per_cluster)

        child = FATDirectoryEntry()
        child.new_dir(parent, name, ext, first_cluster)

        parent.add_child(child)

        dot = FATDirectoryEntry()
        dot.new_dot(parent, first_cluster)
        child.add_child(dot)

        dotdot = FATDirectoryEntry()
        dotdot.new_dotdot(parent)
        child.add_child(dotdot)

        # We only try to expand directories that are not the root.
        if parent.parent is not None:
            if len(parent.children) > 1 and (len(parent.children) % (512/32)) == 1:
                # Here, we need to add another entry to the FAT filesystem.
                self.fat.expand_entry(parent.first_logical_cluster)

    def rm_dir(self, path):
        '''
        A method to remove a directory from the FAT filesystem.

        Parameters:
         path - The path to the directory to be removed.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        if not child.is_dir():
            raise PyFatException("Cannot remove file; try rm_file instead")

        if len(child.children) != 2:
            # If there are more than 2 entries in the directory (. and ..),
            # then we can't remove
            raise PyFatException("Cannot remove non-empty directory")

        if child.parent is None:
            raise PyFatException("Cannot remove the root entry")

        self.fat.remove_entry(child.first_logical_cluster)

        child.parent.remove_child(index)

    def rm_file(self, path):
        '''
        A method to remove a file from the FAT filesystem.

        Parameters:
         path - The path to the file to be removed.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        if child.is_dir():
            raise PyFatException("Cannot remove directory; try rm_dir instead")

        self.fat.remove_entry(child.first_logical_cluster)

        child.parent.remove_child(index)

    def set_hidden(self, path):
        '''
        A method to set the hidden attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to set the hidden attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.set_hidden()

    def set_archive(self, path):
        '''
        A method to set the archive attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to set the archive attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.set_archive()

    def set_read_only(self, path):
        '''
        A method to set the read only attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to set the read only attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.set_read_only()

    def set_system(self, path):
        '''
        A method to set the system attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to set the system attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.set_system()

    def clear_hidden(self, path):
        '''
        A method to clear the hidden attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to clear the hidden attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.clear_hidden()

    def clear_archive(self, path):
        '''
        A method to clear the archive attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to clear the archive attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.clear_archive()

    def clear_read_only(self, path):
        '''
        A method to clear the read only attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to clear the read only attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.clear_read_only()

    def clear_system(self, path):
        '''
        A method to clear the system attribute on a FAT entry.

        Parameters:
         path - The path to the FAT entry to clear the system attribute for.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        child, index = self._find_record(path)

        child.clear_system()

    def write(self, local_path):
        '''
        A method to write this FAT filesystem out to a file.

        Parameters:
         local_path - The local file to write this FAT filesystem to.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("This object is not yet initialized")

        with open(local_path, 'wb') as outfp:
            # First write out the boot entry
            outfp.seek(0 * self.bytes_per_sector)
            outfp.write(struct.pack("=3s8sHBHBHHBHHHLLBBBL11s8s448sH",
                                    self.jmp_boot, self.oem_name,
                                    self.bytes_per_sector,
                                    self.sectors_per_cluster,
                                    self.reserved_sectors,
                                    self.num_fats, self.max_root_dir_entries,
                                    self.sector_count, self.media,
                                    self.sectors_per_fat,
                                    self.sectors_per_track, self.num_heads,
                                    self.hidden_sectors,
                                    self.total_sector_count_32, self.drive_num,
                                    0, self.boot_sig, self.volume_id,
                                    self.volume_label, self.fs_type,
                                    self.boot_code, 0xaa55))

            # Now write out the first FAT
            outfp.seek(1 * self.bytes_per_sector)
            outfp.write(self.fat.record())

            if self.num_fats == 2:
                # Now write out the second FAT
                outfp.seek((1+self.sectors_per_fat) * self.bytes_per_sector)
                outfp.write(self.fat.record())

            # Now write out the directory entries
            # The first root directory sector is preceded by:
            # BPB consisting of 1 sector
            # First FAT consisting of self.sectors_per_fat sectors
            # (Optional) Second FAT consisting of self.sectors_per_fat sectors
            first_root_dir_sector = 1 + (self.num_fats * self.sectors_per_fat)
            root_cluster_list = []
            for i in range(first_root_dir_sector, first_root_dir_sector+self.root_dir_sectors):
                root_cluster_list.append(i)

            dirs = collections.deque([(self.root, root_cluster_list)])
            while dirs:
                currdir, physical_clusters = dirs.popleft()

                cluster_iter = iter(physical_clusters)
                outfp.seek(cluster_iter.next() * self.bytes_per_cluster)
                cluster_offset = 0
                for child in currdir.children:
                    if cluster_offset + 32 > 512:
                        cluster_offset = 0
                        outfp.seek(cluster_iter.next() * self.bytes_per_cluster)

                    outfp.write(child.record())
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
                        new_cluster_list = self.fat.get_cluster_list(child.first_logical_cluster)
                        if child.original_data_location == child.DATA_ON_ORIGINAL_FAT:
                            # If this is a file that was on the original
                            # filesystem, then we haven't modified the cluster
                            # list and the original is the same as the new.
                            orig_cluster_list = new_cluster_list
                        elif child.original_data_location == child.DATA_IN_EXTERNAL_FP:
                            orig_cluster_list = range(0, ceiling_div(child.file_size, 512))

                        left = child.file_size
                        index = 0
                        while index < len(orig_cluster_list) and left > 0:
                            thisread = self.bytes_per_cluster
                            if left < thisread:
                                thisread = left

                            child.data_fp.seek(orig_cluster_list[index] * self.bytes_per_cluster)
                            outfp.seek(new_cluster_list[index] * self.bytes_per_cluster)
                            outfp.write(child.data_fp.read(thisread))

                            left -= thisread
                            index += 1

            # Finally, truncate the file out to its final size
            outfp.truncate(self.size_in_kb * 1024)
            outfp.seek(-1, os.SEEK_END)
            outfp.write("\x00")

    def list_dir(self, path):
        '''
        A method to list all of the children of this particular path.  Note that
        the specified path must be a directory.

        Parameters:
         path - The fully qualified path to the record, of the form "/FOO/BAR".
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("Can only call list_dir on an already open object")

        rec, index = self._find_record(path)

        if not rec.is_dir():
            raise PyIsoException("Record is not a directory!")

        for child in rec.children:
            yield child

    def close(self):
        '''
        A method to close out this object.  Once this is called, the object is
        no longer valid.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyFatException("Can only call close on an already open object")

        # Walk the entire directory tree, closing out file object as necessary.
        dirs = collections.deque([self.root])
        while dirs:
            currdir = dirs.popleft()

            for child in currdir.children:
                if child.is_dir():
                    dirs.append(child)
                else:
                    child.data_fp.close()

        if self.orig_fp is not None:
            self.orig_fp.close()
            self.orig_fp = None

        self.initialized = False
