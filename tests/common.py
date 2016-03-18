import StringIO

def internal_check_boot_sector(fat):
    assert(fat.bytes_per_sector == 512)
    assert(fat.sectors_per_cluster == 1)
    assert(fat.reserved_sectors == 1)
    assert(fat.num_fats == 2)
    assert(fat.max_root_dir_entries == 224)
    assert(fat.sector_count == 2880)
    assert(fat.media == 0xf0)
    assert(fat.sectors_per_fat == 9)
    assert(fat.sectors_per_track == 18)
    assert(fat.num_heads == 2)
    assert(fat.hidden_sectors == 0)
    assert(fat.total_sector_count_32 == 0)
    assert(fat.drive_num == 0)
    assert(fat.boot_sig == 41)
    assert(fat.size_in_kb == 1440)

def internal_check_directory_entry(entry, filename, extension, first_logical_cluster, file_size, attributes):
    assert(entry.filename == filename)
    assert(entry.extension == extension)
    assert(entry.first_logical_cluster == first_logical_cluster)
    assert(entry.file_size == file_size)
    assert(entry.attributes == attributes)

def internal_check_root(root):
    internal_check_directory_entry(root, '        ', '   ', 0, 0, 0x10)

def check_nofiles(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 0)
    assert(fat.root.children == [])

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    for i in range(2, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

def check_onefile(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x20)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")

def check_onedir(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "DIR1    ", "   ", 2, 0, 0x10)
    assert(len(fat.root.children[0].children) == 2)

    dir1 = fat.root.children[0]
    assert(len(dir1.children) == 2)
    internal_check_directory_entry(dir1.children[0], ".       ", "   ", 2, 0, 0x10)
    internal_check_directory_entry(dir1.children[1], "..      ", "   ", 0, 0, 0x10)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

def check_onefile_system(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x24)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")

def check_onefile_archive(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x20)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")

def check_onefile_hidden(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x22)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")

def check_onefile_read_only(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x21)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")

def check_onefile_all_attr(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x27)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")

def check_onefile_no_attr(fat, filesize):
    assert(filesize == 1474560)

    internal_check_boot_sector(fat)

    internal_check_root(fat.root)
    assert(fat.root.parent is None)
    assert(len(fat.root.children) == 1)
    internal_check_directory_entry(fat.root.children[0], "FOO     ", "   ", 2, 4, 0x0)
    assert(len(fat.root.children[0].children) == 0)

    assert(len(fat.fat.fat) == 512 * 9 / 1.5)
    assert(fat.fat.fat[0] == 0xf0)
    assert(fat.fat.fat[1] == 0xff)
    assert(fat.fat.fat[2] == 0xfff)
    for i in range(3, int(512*9 / 1.5)):
        assert(fat.fat.fat[i] == 0x00)

    fout = StringIO.StringIO()
    fat.get_and_write_file("/FOO", fout)
    assert(fout.getvalue() == "foo\n")
