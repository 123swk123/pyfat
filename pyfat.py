import struct
import collections
import os

def hexdump(st):
    '''
    A utility function to print a string in hex.

    Parameters:
     st - The string to print.
    Returns:
     A string containing the hexadecimal representation of the input string.
    '''
    return ':'.join(x.encode('hex') for x in st)

class FATDirectoryEntry(object):
    def __init__(self):
        self.initialized = False
        self.physical_clusters = []

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

    def new_root(self):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        self.filename = '        '
        self.extension = '   '
        self.attributes = 0
        self.creation_time = 0
        self.creation_date = 0
        self.last_access_date = 0
        self.last_write_time = 0
        self.last_write_date = 0
        self.first_logical_cluster = 0
        self.file_size = 0

        self.parent = None
        self.children = []

        self.initialized = True

    def new_file(self, infp, parent, filename, extension):
        if self.initialized:
            raise Exception("This directory entry is already initialized")

        if len(filename) > 8:
            raise Exception("Filename is too long (must be 8 or shorter)")

        if len(extension) > 3:
            raise Exception("Extension is too long (must be 3 or shorter)")

        self.filename = filename
        self.extension = extension
        self.attributes = 0
        self.creation_time = 0
        self.creation_date = 0
        self.last_access_date = 0
        self.last_write_time = 0
        self.last_write_date = 0
        self.first_logical_cluster = 0
        self.file_size = 0

        self.data_fp = data_fp

    def is_dir(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return self.attributes & 0x10

    def add_child(self, child):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        self.children.append(child)

    def directory_record(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return struct.pack("=8s3sBHHHHHHHHL", self.filename, self.extension,
                           self.attributes, 0, self.creation_time,
                           self.creation_date, self.last_access_date, 0,
                           self.last_write_time, self.last_write_date,
                           self.first_logical_cluster, self.file_size)

    def get_data_fp(self):
        if not self.initialized:
            raise Exception("This directory entry is not yet initialized")

        return self.data_fp

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

        self.fat = first_fat

        # Now walk the root directory entry
        self.root = FATDirectoryEntry()
        self.root.parse('           \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', None, infp)
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
                    dirs.append((ent, _get_cluster_list_from_fat(ent.first_logical_cluster)))

        self.initialized = True

    def _get_cluster_list_from_fat(self, first_logical_cluster):
        curr = first_logical_cluster
        physical_clusters = []
        physical_clusters.append(33 + curr - 2)
        while True:
            offset = (3*curr)/2
            if curr % 2 == 0:
                # even
                low,high = struct.unpack("=BB", self.fat[offset:offset+2])
                fat_entry = ((high & 0x0f) << 8) | (low)
            else:
                # odd
                low,high = struct.unpack("=BB", self.fat[offset:offset+2])
                fat_entry = (high << 4) | (low >> 4)

            if fat_entry in [0xff8, 0xff9, 0xffa, 0xffb, 0xffc, 0xffd, 0xffe, 0xfff]:
                # This is the end!
                break
            else:
                physical_clusters.append(33 + fat_entry - 2)
                curr = fat_entry

        return physical_clusters

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

        for cluster in self._get_cluster_list_from_fat(child.first_logical_cluster):
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

        self.fat = '\xf0\xff\xff'

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

        filename,parent = self._name_and_parent_from_index(path)

        name,ext = os.path.splitext(filename)

        child = FATDirectoryEntry()
        child.new_file(infp, parent, name, ext)

        parent.add_child(child)

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
        outfp.write(self.fat)

        # Now write out the second FAT
        outfp.seek(10 * 512)
        outfp.write(self.fat)

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

                if child.is_dir():
                    dirs.append(child)

        # Now write out the files
        dirs = collections.deque([self.root])
        while dirs:
            currdir = dirs.popleft()

            for child in currdir.children:
                if child.is_dir():
                    dirs.append(child)
                else:
                    data_fp = child.get_data_fp()

                    # An actual file we have to write out
                    for cluster in self._get_cluster_list_from_fat(child.first_logical_cluster):
                        data_fp.seek(cluster * 512)
                        outfp.seek(cluster * 512)
                        outfp.write(data_fp.read(512))

        # Finally, truncate the file out to its final size
        outfp.truncate(self.size_in_kb * 1024)

    def close(self):
        if not self.initialized:
            raise Exception("Can only call close on an already open object")

        self.initialized = False
