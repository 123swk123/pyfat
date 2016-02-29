import struct

class PyFat(object):
    FAT12 = 0
    FAT16 = 1
    FAT32 = 2

    def __init__(self):
        self.initialized = False

    def open(self, infp):
        if self.initialized:
            raise Exception("This object is already initialized")

        infp.seek(0)

        boot_sector = infp.read(512)

        (self.jmp_boot, self.oem_name, self.bytes_per_sector, self.sectors_per_cluster,
         self.reserved_sectors, self.num_fats, self.max_root_dir_entries,
         self.sector_count, self.media, self.sectors_per_fat,
         self.sectors_per_track, self.num_heads, self.hidden_sectors,
         self.total_sector_count_32, self.drive_num, unused1, self.boot_sig, self.volume_id,
         self.volume_label, self.fs_type, unused2, sig) = struct.unpack("=3s8sHBHBHHBHHHLLBBBL11s8s448sH", boot_sector)

        self.jmp_boot2 = struct.unpack(">L", self.jmp_boot + '\x00')

        print "Jmp Boot: 0x%x" % (self.jmp_boot2)
        print "OEM Name: %s" % (self.oem_name)
        print "Bytes per sector: %d" % (self.bytes_per_sector)
        print "Sectors per cluster: %d" % (self.sectors_per_cluster)
        print "Reserved sectors: %d" % (self.reserved_sectors)
        print "Number of FATs: %d" % (self.num_fats)
        print "Maximum Root Directory Entries: %d" % (self.max_root_dir_entries)
        print "Sector Count: %d" % (self.sector_count)
        print "Media: 0x%x" % (self.media)
        print "Sectors Per FAT: %d" % (self.sectors_per_fat)
        print "Sectors Per Track: %d" % (self.sectors_per_track)
        print "Number of Heads: %d" % (self.num_heads)
        print "Hidden Sectors: %d" % (self.hidden_sectors)
        print "Total Sector Count FAT32: %d" % (self.total_sector_count_32)
        print "Drive number: %d" % (self.drive_num)
        print "Boot Signature: %d" % (self.boot_sig)
        print "Volume ID: %d" % (self.volume_id)
        print "Volume Label: %s" % (self.volume_label)
        print "FS Type: '%s'" % (self.fs_type)

        # FIXME: check that jmp_boot is 0xeb, 0x??, 0x90

        if self.bytes_per_sector != 512:
            raise Exception("Expected 512 bytes per sector")

        if self.sectors_per_cluster != 1:
            raise Exception("Expected 1 sector per cluster")

        if self.media not in [0xf0, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff]:
            raise Exception("Invalid media type")

        if self.num_fats != 2:
            raise Exception("Expected 2 FATs")

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

        self.initialized = True

    def new(self):
        if self.initialized:
            raise Exception("This object is already initialized")

    def close(self):
        if not self.initialized:
            raise Exception("Can only call close on an already open object")

        self.initialized = False
