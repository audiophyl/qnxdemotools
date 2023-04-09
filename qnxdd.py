"""
QNXDD is a collection of functions and classes relevant to the manipulation
of the QNX Demodisk released in the 90s and its associated extensions.
"""

__author__ = "Philip Barton"
__version__ = "1.7.3"
__license__ = "MIT"


import bz2
import math


# XOR_KEY is the ASCII values of " Dan Hildebrand creator of demodisk " with
# each character shifted -1. If you can read machine code, everything is open
# source! ;)
XOR_KEY = [31, 67, 96, 109, 31, 71, 104, 107, 99, 100, 97, 113, 96, 109, 99,
           31, 98, 113, 100, 96, 115, 110, 113, 31, 110, 101, 31, 99, 100, 108,
           110, 99, 104, 114, 106, 31]
SEGMENT_SIZE = 512
QZ_MAGIC_1 = b'\x51\x5a\x68'
QZ_MAGIC_2 = b'\x31\x41\x59\x26\x53\x59'
BZ2_MAGIC_1 = b'\x42\x5a'


def xor_cipher(in_data):
    """ Apply Dan Hildebran's XOR cipher to the given input.
    
        Args:
            in_data: The data to cipher/decipher.

        Returns: The ciphered/deciphered data.
    """

    in_data_len = len(in_data)
    out_data = bytearray(in_data_len)
    xor_key_len = len(XOR_KEY)
    offset = 0

    while offset < in_data_len:
        segment_len = SEGMENT_SIZE if offset + SEGMENT_SIZE < in_data_len else in_data_len - offset

        for i in range(segment_len):
            out_data[offset + i] = in_data[offset + i] ^ XOR_KEY[i % xor_key_len]

        offset += segment_len

    return out_data


def decomp_enigma(in_data):
    """ Decompression for the third stage bootloader. 
    
        We don't presently do anything with the decompressed data, so this
        function exists purely to satisfy curiosity. Writing a suitable
        compression algorithm should be straightforward, and I will get around
        to this.

        I'm not well-versed on compression schemes, but to my untrained eye
        this looks like some kind of RLE.

        No comments are provided as an exercise to the reader.

        Args:
            in_data: Input data as bytearray.

        Returns: Decompressed data.
    """

    seg_size = -1
    return_bytes = bytearray()
    current_byte = 0

    while seg_size:
        table1 = bytearray(256)
        for byte in range(256):
            table1[byte] = byte
        table2 = bytearray(256)
        table_index = 0

        seg_size = int.from_bytes(in_data[current_byte:current_byte + 2], "big")
        current_byte += 2
        if seg_size == 0:
            continue

        while table_index < 256:
            token = in_data[current_byte]
            current_byte += 1

            if token > 127:
                token -= 127
                table_index += token
                if table_index >= 256:
                    continue
                test_byte = in_data[current_byte]
                current_byte += 1
                if test_byte == table_index:
                    table_index += 1
                    continue
                else:
                    table1[table_index] = test_byte
                    table2[table_index] = in_data[current_byte]
                    current_byte += 1
            else:
                table1[table_index] = in_data[current_byte]
                current_byte += 1
                table2[table_index] = in_data[current_byte]
                current_byte += 1
                while token > 0:
                    table_index += 1
                    token -= 1
                    test_byte = in_data[current_byte]
                    current_byte += 1
                    if test_byte == table_index:
                        table_index += 1
                        token -= 1
                        test_byte = in_data[current_byte]
                        current_byte += 1
                    table1[table_index] = test_byte
                    table2[table_index] = in_data[current_byte]
                    current_byte += 1
            table_index += 1

        if table_index == 256:
            out_bin = bytearray()
            comp_bin = in_data[current_byte:current_byte + seg_size]
            current_byte += seg_size
            token_stack = []
            for token in comp_bin:
                token_stack.append(token)
                while token_stack:
                    temp_token = token_stack.pop(-1)
                    if temp_token == table1[temp_token]:
                        out_bin.extend([temp_token])
                    else:
                        token_stack.append(table2[temp_token])
                        token_stack.append(table1[temp_token])
            return_bytes.extend(out_bin)
        else:
            print(f"Invalid file.")
            return None

    return return_bytes


def qunzip(in_data):
    """ Decompress the provided data.
    
        'QZip' files are slightly modified BZ2 files, so we slightly modify
        them back to being BZ2 files and feed them to bz2.decompress().

        Args:
            in_data: Byte array to be decompressed.

        Returns: Byte array of decompressed data.
    """

    magic_1 = in_data[0:4]
    magic_2 = in_data[8:14]
    if magic_1[0:3] == QZ_MAGIC_1 and magic_2 == QZ_MAGIC_2:
        bz2data = BZ2_MAGIC_1 + magic_1[2:] + QZ_MAGIC_2 + in_data[14:]
        return bz2.decompress(bz2data)
    else:
        print(f"This doesn't appear to be a QZip file.")


def qzip(in_data):
    """ Compress the provided data.
    
        'QZip' files are slightly modified BZ2 files, so we slightly modify
        the output from bz2.compress().

        Args:
            in_data: Byte array to be compressed.

        Returns: Byte array of compressed data.
    """

    return_bytes = QZ_MAGIC_1
    bz2data = bz2.compress(in_data)
    return_bytes += bz2data[3:4]    
    ramdisk_size = int.to_bytes(len(in_data), 4, "big")
    return_bytes += ramdisk_size
    return_bytes += bz2data[4:]
    return return_bytes


class Ramdisk:
    """ Validates and provides functionality for an 'RD_v1.2' ramdisk.

        Used to hold a QNX ramdisk as a bytearray for manipulation. Supports
        the handful of commands available for use in qnxddcli.
    """

    # Offsets and magic numbers for ramdisks.
    MAGIC_START = 0
    MAGIC_END = 8
    MAGIC = b'RD_v1.2\x00'
    SIZE_START = 8
    SIZE_END = 12
    SECTOR_SIZE_START = 12
    SECTOR_SIZE_END = 14
    BASE_OFFSET = 14
    CHECKVAL_START = 22
    CHECKVAL_END = 24
    CHECKVAL = 0x16
    SECTOR_MAP_START = 133
    
    # For some reason, 105 is used in the disk utilization calculation instead
    # of 0x77 == 119 bytes. Perhaps an error in the original design?
    ENTRY_SIZE_MAGIC = 105

    # This is a list of known flags observed in a stock ramdisk.
    KNOWN_FLAGS = [0x81fd, 0x81a4, 0x81b4, 0x41fd]


    def __init__(self, in_file):
        """ Inits Ramdisk with self._raw = in_file """

        try:
            with open(in_file, "rb") as in_f:
                self._raw = bytearray(in_f.read())
        except Exception as e:
            print(f"Unable to read ramdisk file. Error: {e}.")
            return None

        if self._raw[self.MAGIC_START:self.MAGIC_END] != self.MAGIC:
            raise Exception("Unsupported format.")
        if int.from_bytes(self._raw[self.CHECKVAL_START:self.CHECKVAL_END], "little") != self.CHECKVAL:
            raise Exception("Checkval on *base* is incorrect.")
        
        self._filename = in_file
        self._size = int.from_bytes(self._raw[self.SIZE_START:self.SIZE_END], "little")
        self._sector_size = int.from_bytes(self._raw[self.SECTOR_SIZE_START:self.SECTOR_SIZE_END], "little")
        self._base = Entry(self._raw[self.BASE_OFFSET:self.BASE_OFFSET + Entry.ENTRY_SIZE])
        self._path = [self._base]


    def info(self):
        """ Output details about the ramdisk.

        Args: None.

        Returns: None.
        """

        print(f"{'Filename:' : <10}{self._filename}")
        print(f"{'Size:' : <10}{self._size : >8} bytes")
        print(f"{'Sector: ' : <10}{self._sector_size : >8} bytes")
        print(f"{'Free: ' : <10}{self._get_free() : >8} bytes")
        sector_map = self._raw[self.SECTOR_MAP_START:self.SECTOR_MAP_START + (self._size // (self._sector_size * 8))]
        print(f"{'Map: ' : <10}{bytes(sector_map).hex()}")


    def _alloc(self, in_request):
        """ Locate the specified number of free sectors.

        Locate the specified number of free sectors and return their offsets
        as a list. If not enough sectors are free, return an empty list.

        Args:
            in_request (int): An int for the number of sectors requested.

        Returns ([int]): A list of length in_request containing the offsets of
            free sectors, OR an empty list if there are not enough free sectors
            to satisfy the original request.
        """

        free_sectors = self._list_free()
        alloc_sectors = []
        while True in free_sectors:
            tmp_sector = free_sectors.index(True)
            free_sectors[tmp_sector] = False
            alloc_sectors.append(tmp_sector * self._sector_size)
            if len(alloc_sectors) == in_request:
                return alloc_sectors
        return []


    def _get_free(self):
        """ Compute free space on ramdisk.
        
            Args: None.

            Returns (int): Free space as bytes.
        """

        free_sectors = self._list_free().count(True)
        return free_sectors * self._sector_size


    def _list_free(self):
        """ Generate a True/False list for occupancy of each sectors.

        This function is tricky and possibly not correct, but I'm having
        a difficult time dreaming up edge cases. Basically, maintain two
        lists: one containing every sector header, the other containing
        True/False values indicating whether or not the sector is free.

        We assume all sectors are free, then establish which are occupied.
        A value of True indicates a sector is free, a value of False
        indicates it is occupied.

        Args: None

        Returns ([bool]): A list containing True or False values dependent upon
            sector occupation.
        """

        # examine the first four bytes ('next' pointer) of every sector.
        sector_headers = []
        test_sector = 0
        while test_sector * self._sector_size < len(self._raw):
            tmp_offset = test_sector * self._sector_size
            sector_headers.append(int.from_bytes(self._raw[tmp_offset:tmp_offset + 4], "little") // self._sector_size)
            test_sector += 1

        sector_free = [True] * len(sector_headers)

        for i, val in enumerate(sector_headers):
            # if the pointer bytes are non-zero or the sector is
            # pointed at elsewhere, the sector is 'occupied'
            if val != 0 or i in sector_headers:
                sector_free[i] = False
            # elif the sector is a file/dir occupying one single sector,
            # at least one byte will be non-zero. if our set contains more
            # than one element, mark the sector as occupied.
            elif val == 0:
                tmp_offset = i * self._sector_size
                sector_bytes = set(self._raw[tmp_offset:tmp_offset + self._sector_size])
                if len(sector_bytes) > 1:
                    sector_free[i] = False

        return sector_free


    def _get_dir_contents(self, in_dir):
        """ Generate a list of Entry objects for each entry in the directory.
        
            Iterate across all sectors containing directory data and
            convert each Entry-sized chunk into an Entry.

            Args:
                in_dir (Entry): An Entry representing the directory to be
                    listed.

            Yields ([Entry]): A generator for Entry objects.
        """


        sectors = self._get_sector_list(in_dir)
        for sector in sectors:
            raw_directory = self._raw[sector + 4:sector + self._sector_size - 4]
            num_entries = len(raw_directory) // Entry.ENTRY_SIZE
            for entry in range(0, num_entries):
                tmp_entry = Entry(raw_directory[(Entry.ENTRY_SIZE * entry):(Entry.ENTRY_SIZE * entry) + Entry.ENTRY_SIZE])
                yield tmp_entry
    

    def _entry_exists(self, in_name):
        """ Determine whether or not a given entry name is in use.
        
        Args:
            in_name (str): Entry name as a string.
            
        Returns (bool): Exists/doesn't exist.
        """

        etypes = ["links", "dir", "file"]
        for etype in etypes:
            if self._get_entry(in_name, etype):
                return True
        return False


    def _get_entry(self, in_name, in_type):
        """ Attempt to locate an Entry by name & type.
        
            Given a name and type of entry (link, dir, file), attempt
            to locate this Entry within the current directory.

            Args:
                in_name (str): The name of the Entry to attempt to locate.
                in_type (str): The type of Entry (link, dir, file) to attempt
                    to locate.

            Returns (Entry): A single Entry if located, else None.
        """

        for entry in self._get_dir_contents(self._path[-1]):
            if entry.etype == in_type:
                if entry.etype == "empty":
                    return entry
                if entry.name == in_name:
                    return entry
        return None

    
    def _get_sector_list(self, in_entry):
        """ Get the list of sectors occupied by the given Entry.
        
            Follows the dest_offset of the given Entry and compiles a list
            of all linked sectors. When an offset of 0 has been added
            to the list, we have moved one sector beyond the end of
            useful data, so pop the last value and return what remains.

            Args:
                in_entry (Entry): The Entry for which sectors will be located.

            Returns ([int]): A list of sector offsets.
        """

        sectors = [in_entry.dest_offset]
        while sectors[-1] != 0:
            sectors.append(int.from_bytes(self._raw[sectors[-1]:sectors[-1] + 4], "little"))
        sectors.pop(-1)
        return sectors
    

    def _write_entry(self, in_entry, in_offset):
        """ Write an Entry to the specified offset.

            Writes Entry.ENTRY_SIZE bytes from in_entry to Ramdisk starting
            at in_offset.
            
            Args:
                in_entry (Entry): The Entry to be written.
                in_offset (int): The offset at which to begin writing.

            Returns: None.
        """

        if in_entry.etype != "empty":
            in_entry.fat_offset = in_offset
        self._raw[in_offset:in_offset + Entry.ENTRY_SIZE] = in_entry.raw


    def _zero_sector(self, in_sector):
        """ Zero out the specified sector.
        
            Write zeroes to the full sector specified by in_sector. It is
            important to note that in_sector is merely an OFFSET, it is not
            an ordinal position.

            Args:
                in_sector (int): Offset of sector to zero.

            Returns: None.
        """

        self._raw[in_sector:in_sector + self._sector_size] = [0] * self._sector_size


    def _optimize(self):
        """ Fix the file allocation table and parent directory on edit.
        
            When an Entry has been removed or added, make the necessary
            adjustments to the parent directory's Entry and also rewrite the
            file allocation table for the entire parent directory. Account
            for the possibility that the directory's contents may grow/shrink
            through a sector boundary.

            This function is a beast, and I wish I had better ideas.

            Args: None.

            Returns: None.
        """

        # List all sectors occupied by directory info.
        sectors = self._get_sector_list(self._path[-1])
        # Generator containing every Entry in this directory.
        entries = self._get_dir_contents(self._path[-1])
        # The first two Entry objects are links.
        links = [next(entries), next(entries)]
        # Empty lists for dir and file Entry types.
        dirs = []
        files = []

        # Iterate over entries in the directory, creating Entry objects and
        # separating them out to either the 'dirs' or 'files' lists.
        #for entry in entries[2:]:
        for entry in entries:
            if entry.etype == "file":
                files.append(entry)
            elif entry.etype == "dir":
                dirs.append(entry)

        total_count = len(links) + len(dirs) + len(files)

        # Sort dirs and files by alpha.
        dirs = sorted(dirs, key=lambda dir: dir.name)
        files = sorted(files, key=lambda file: file.name)

        # Update the parent directory's content count.
        self._path[-1].contains = len(links) + len(dirs)
        # Update the parent directory's 'space on disk'.
        self._path[-1].size = total_count * self.ENTRY_SIZE_MAGIC
        # Update the parent directory's max_size.
        self._path[-1].max_size = len(sectors) * ((self._sector_size - 4) // Entry.ENTRY_SIZE)

        # Commit above parent directory Entry changes.
        self._write_entry(self._path[-1], self._path[-1].fat_offset)

        # Re-write directory contents then zero remaining space.
        # Start in the first sector, and write one Entry at a time -- first all
        # links, second all dirs, third all files -- advancing sectors as needed.
        for sector in sectors:
            tmp_offset = 4

            while tmp_offset + Entry.ENTRY_SIZE < self._sector_size:
                if links:
                    self._write_entry(links.pop(0), sector + tmp_offset)
                elif dirs:
                    self._write_entry(dirs.pop(0), sector + tmp_offset)
                elif files:
                    self._write_entry(files.pop(0), sector + tmp_offset)
                else:
                    break
                tmp_offset += Entry.ENTRY_SIZE

            self._raw[sector + tmp_offset:sector + self._sector_size] = [0] * (self._sector_size - tmp_offset)

        # Drop a sector from the directory table if needed and zero it out.
        if ((self._sector_size - 4) // Entry.ENTRY_SIZE) * (len(sectors) - 1) >= total_count:
            self._zero_sector(sectors[-1])
            # Zero the pointer to the sector which was just zeroed.
            self._raw[sectors[-2]:sectors[-2] + 4] = [0, 0, 0, 0]
            self._path[-1].max_size -= (self._sector_size - 4) // Entry.ENTRY_SIZE
            self._write_entry(self._path[-1], self._path[-1].fat_offset)

        # Update free space map at head of ramdisk.
        sector_map = list(map(lambda x: "0" if x else "1", self._list_free()))
        if len(sector_map) % 8 != 0:
            extension = ["0"] * (8 - (len(sector_map) % 8))
            sector_map.extend(extension)
        updated_map = []
        sector_map_offset = 0
        while sector_map_offset < len(sector_map):
            tmp_bits = int(''.join(reversed(sector_map[sector_map_offset:sector_map_offset + 8])), 2)
            updated_map.append(tmp_bits)
            sector_map_offset += 8
        self._raw[self.SECTOR_MAP_START:self.SECTOR_MAP_START + len(updated_map)] = updated_map


    def _rm_entry(self, in_entry):
        sectors = self._get_sector_list(in_entry)
        for sector in sectors:
            self._zero_sector(sector)
        self._write_entry(Entry(), in_entry.fat_offset)
        self._optimize()


    def ls(self):
        """ Pretty print a directory listing.
        
            Args: None.

            Returns: None.
        """

        print(f"{'TYPE' : <8}{'NAME' : <20}{'SIZE' : >8}{'OFFSET' : >10}")
        print(f"{'-' * 46}")
        for entry in self._get_dir_contents(self._path[-1]):
            match entry.etype:
                case "empty":
                    continue
                case "link":
                    extra = f""
                case "dir":
                    extra = f" CONTAINS: {hex(entry.contains)} FLAGS: {hex(entry.flags)}"
                case "file":
                    extra = f" FLAGS: {hex(entry.flags)}"
                case _:
                    print(f"{entry.raw}")
                    quit("Something went wrong.")
            print(f"{entry.etype : <8}{entry.name : <20}{entry.size : >8}{hex(entry.fat_offset) : >10}" + extra)


    def cd(self, in_dir):
        """ Change directory.
        
            Checks to ensure in_dir exists, and if so traverses into the Entry.

            Args:
                in_dir (str): Name of directory Entry to traverse.

            Returns (bool): Succeed/fail.
        """

        match in_dir:
            case "/":
                self._path = [self._base]
                return True
            case ".":
                return True
            case "..":
                if len(self._path) > 1:
                    self._path.pop(-1)
                return True
            case _:
                if entry := self._get_entry(in_dir, "dir"):
                    self._path.append(Entry(self._raw[entry.fat_offset:entry.fat_offset + Entry.ENTRY_SIZE]))
                    return True
        return False


    def dump(self, in_name):
        """ Output data from the specified file to the local drive.
        
            Attempt to locate in_name in the current directory. If located,
            dump the Entry's data from the Ramdisk to a local file having the
            same name.

            Args:
                in_name (str): Name of the Entry to dump.

            Returns (bool): Succeed/fail.
        """

        if entry := self._get_entry(in_name, "file"):
            out_bytes = b''
            remaining_bytes = entry.size
            sectors = self._get_sector_list(entry)
            while sectors:
                current_sector = sectors.pop(0)
                if remaining_bytes < self._sector_size - 4:
                    tmp_bytes = self._raw[current_sector + 4:current_sector + remaining_bytes + 4]
                else:
                    tmp_bytes = self._raw[current_sector + 4:current_sector + self._sector_size]
                remaining_bytes -= len(tmp_bytes)
                out_bytes += tmp_bytes
            try:
                with open(in_name, "wb") as out_f:
                    out_f.write(out_bytes)
            except Exception as e:
                print(f"{e}")
                return False
            return True
        return False


    def inject(self, in_name):
        """ Inject data from a local file into the ramdisk.
        
            Attempt to inject local file in_name into the current directory
            of the Ramdisk. Check to see if an Entry by that name already
            exists, and whether there's enough free space.

            Args:
                in_name (str): Name of local file to inject.

            Returns (bool): Succeed/fail.
        """

        if self._entry_exists(in_name):
            print(f"'{in_name}' already exists.")
            return False

        try:
            with open(in_name, "rb") as in_f:
                inject_bin = bytearray(in_f.read())
        except Exception as x:
            print(f"{x}")
            return False
        
        # Use (self._sector_size - 4) since the first four bytes of each
        # sector are reserved as a pointer for the next sector.
        sectors_needed = math.ceil(len(inject_bin) / (self._sector_size - 4))
        grow_dir = False

        # If the directory is 'full', we will also need to find an additional
        # sector to accomodate the growth of the directory table.
        if (self._path[-1].size // self.ENTRY_SIZE_MAGIC) == self._path[-1].max_size:
            grow_dir = True
            sectors_needed += 1

        if sectors := self._alloc(sectors_needed):
            # Get our directory sectors.
            dir_sectors = self._get_sector_list(self._path[-1])
            # If needed, grow the directory by one sector.
            if grow_dir:
                if new_sector := sectors.pop(0):
                    self._raw[dir_sectors[-1]:dir_sectors[-1] + 4] = int.to_bytes(new_sector, 4, "little")
                    entry_offset = new_sector + 4
                else:
                    return False
            else:
                # First, calculate how many entries will fit in the directory.
                entry_offset = self._path[-1].size // self.ENTRY_SIZE_MAGIC
                # Second, modulo this value by the number of entries per
                # sector.
                entry_offset %= (self._sector_size - 4) // Entry.ENTRY_SIZE
                # Third, multiply this smaller value by the actual Entry size.
                entry_offset *= Entry.ENTRY_SIZE
                # Fourth, add our value to the sector offset, plus 4 to account
                # for the initial four bytes in the sector which serve as a
                # pointer.
                entry_offset += dir_sectors[-1] + 4

            # Configure a new Entry object for the injection.
            entry = Entry()
            entry.etype = "file"
            entry.contains = 1
            entry.name = in_name
            entry.size = len(inject_bin)
            entry.max_size = sectors_needed * (self._sector_size - 4)
            entry.dest_offset = sectors[0]
            entry.flags = Entry.VALID_FLAGS['DEFAULT_FILE']

            # Write the Entry to the file table
            self._write_entry(entry, entry_offset)

            # Write the file to the ramdisk.
            read_offset = 0
            for i, sector in enumerate(sectors):
                if i < len(sectors) - 1:
                    self._raw[sector:sector + 4] = int.to_bytes(sectors[i + 1], 4, "little")
                    self._raw[sector + 4:sector + self._sector_size] = inject_bin[read_offset:read_offset + self._sector_size - 4]
                    read_offset += self._sector_size - 4
                else:
                    remaining_bin = inject_bin[read_offset:]
                    self._raw[sector + 4:sector + len(remaining_bin) + 4] = remaining_bin

            # Call _optimize to adjust the parent directory, free space map, etc.
            self._optimize()
            return True
        else:
            return False


    def flags(self, in_name, in_flags):
        """ Set flags for supplied Entry.

            I haven't yet been able to figure out which flags mean what. Check
            that the provided flags have been used elsewhere, which is good
            enough for a first release.
        
            Args:
                in_name (str): Name of file Entry to update.
                in_flags (str): Flags string.

            Returns (bool): Succeed/fail.
        """

        tmp_flags = int(in_flags, 16)
        if tmp_flags not in Entry.VALID_FLAGS.values():
            return False
        if entry := self._get_entry(in_name, "file"):
            entry.flags = int(in_flags, 16)
            self._write_entry(entry, entry.fat_offset)
            return True
        return False
    

    def rm(self, in_name):
        """ Remove the specified file Entry.
        
            Args:
                in_name (str): Name of the Entry to remove.

            Returns (bool): Succeed/fail.
        """

        if entry := self._get_entry(in_name, "file"):
            self._rm_entry(entry)
            return True
        return False
    

    def rmdir(self, in_name):
        """ Remove the specified directory Entry.
        
            Checks whether or not the specified directory exists and is empty,
            then deletes it if conditions are met.

            Args:
                in_name (str): Name of the Entry to remove.

            Returns (bool): Succeed/fail.
        """

        if entry := self._get_entry(in_name, "dir"):
            contents = list(filter(
                lambda x:
                    True if x.etype == "file" or x.etype == "dir" else False,
                self._get_dir_contents(entry)
            ))
            if contents:
                return False
            self._rm_entry(entry)
            return True
        return False


    def commit(self, in_file):
        """ Commit active Ramdisk to disk as in_file.
        
            Args:
                in_file (str): Local file name to which Ramdisk will be
                written.

            Returns (bool): Succeed/fail.
        """

        try:
            with open(in_file, "wb") as out_f:
                out_f.write(self._raw)
        except Exception as e:
            print(f"Unable to write file: {e}.")
            return False
        return True


    def pwd(self):
        """ Print working directory.
        
            Args: None.
            
            Returns (str): Full path to Ramdisk's current directory.
        """

        dir_names = [entry.name for entry in self._path[1:]]
        pwd_str = "/" + "/".join(dir_names)
        return pwd_str


    def showfat(self, in_entry):
        """ Show Entry for the specified link/file/dir.
        
            Args:
                in_entry (str): Name of Entry to retrieve.

            Returns (str): Hex string of raw Entry data.
        """

        etypes = ["link", "dir", "file"]
        for etype in etypes:
            entry = self._get_entry(in_entry, etype)
            if entry != None:
                return bytes(entry.raw).hex()
        return None
    

    def listfree(self):
        """ List offsets for all free sectors.
        
            Args: None.

            Returns ([int]): List of offsets for all free sectors.
        """

        free_sectors = self._list_free()
        sectors = []
        while True in free_sectors:
            sectors.append(free_sectors.index(True))
            free_sectors[sectors[-1]] = False
        return sectors


class Entry:
    ENTRY_SIZE = 119
    TYPE_OFFSET = 0
    TYPE_EMPTY = 0x00000000
    TYPE_LINK = 0x81000000
    TYPE_FILEDIR = 0x80000000
    MAX_SIZE_OFFSET = 4
    FAT_OFFSET = 8
    LINK_NAME_OFFSET = 12   # 'link' name offset
    SIZE_OFFSET = 16
    FLAGS_OFFSET = 50
    VALID_FLAGS = {
        'DEFAULT_FILE': 0x81fd, # renamable executables
        'ALT_FILE_1': 0x81a4,   # RW text files (ex. HTML files)
        'ALT_FILE_2': 0x81b4,   # RW text files (ex. configs), non-renamable executables
        'DEFAULT_DIR': 0x41fd   # all directories
    }
    CONTAINS_OFFSET = 56
    NAME_OFFSET = 64        # 'dir' and 'file' name offsets
    NAME_LENGTH = 48        # The filesystem begins to choke beyond this limit
    DEST_OFFSET = 115


    def __init__(self, in_entry=None):
        if in_entry and len(in_entry) == self.ENTRY_SIZE:
            self._raw = in_entry
            if self.etype == "bad":
                return None
        elif not in_entry:
            self._raw = bytearray([0] * self.ENTRY_SIZE)
        return
    

    def _is_invalid_char(self, in_char):
        """ Check ascii encoded character for validity.
        
            Used to filter filenames passed to self.name setter. QNX disallows
            control characters (0x01-0x1f), "/" (0x2f), DEL (0x7f), and 0xff
            within names of files and directories. There does not appear to be
            a limitation on what a name may begin with, either.

            Args:
                in_char (str): The ascii encoded character to test.
            
            Returns (bool): True/False to be used by filter().
        """

        if in_char <= 0x1f:
            return True
        
        match in_char:
            case 0x2f | 0x7f | 0xff:
                return True
            case _:
                return False


    @property
    def etype(self):
        """ Get etype.

            Args: None.
            Returns:
                'empty': The provided data slot is free for use.
                'link': The provided data represents '.' or '..'
                'file': The provided data are a file descriptor.
                'dir': The provided data are a directory descriptor.
                'bad': The provided data aren't an entry.
        """

        header = int.from_bytes(self._raw[self.TYPE_OFFSET:self.TYPE_OFFSET + 4], "little")
        match header:
            case self.TYPE_EMPTY:
                return "empty"
            case self.TYPE_LINK:
                return "link"
            case self.TYPE_FILEDIR:
                return "file" if self.contains == 1 else "dir"
            case _:
                return "bad"


    @etype.setter
    def etype(self, in_type):
        """ Set etype.

            Allows changing the etype from "empty" to "link", "file", or "dir".
            Will not allow changes for any other starting etype.

            Args:
                in_type (str): The type to which etype will be set.

            Returns (bool): Succeed/fail.
        """

        if self.etype != "empty":
            return False

        match in_type:
            case "empty":
                val = self.TYPE_EMPTY
            case "link":
                val = self.TYPE_LINK
            case "file":
                val = self.TYPE_FILEDIR
            case "dir":
                val = self.TYPE_FILEDIR

        tmp_bytes = int.to_bytes(val, 4, "little")
        self._raw[self.TYPE_OFFSET:self.TYPE_OFFSET + 4] = tmp_bytes
        return True


    @property
    def name(self):
        """ Get name.

            Args: None.

            Returns (str):
                '' for empty slots.
                '.' or '..' for links.
                The full name string for files and directories.
        """

        if self.etype == "empty":
            return ""
        name_start = self.LINK_NAME_OFFSET if self.etype == "link" else self.NAME_OFFSET
        name_end = name_start + 1
        while self._raw[name_end] != 0:
            name_end += 1
        return self._raw[name_start:name_end].decode("ascii")


    @name.setter
    def name(self, in_name):
        """ Set name.

            Sets provided value for Entry of type "dir" or "file". Limits in_name
            to 48 characters. Checks for disallowed characters. Given the current
            architecture, there is no way to know whether the name being set is
            already in use elsewhere.

            Args:
                in_name (str): Name for Entry.

            Returns: None.
        """

        if len(in_name) >= self.NAME_LENGTH:
            in_name = in_name[0:self.NAME_LENGTH]

        if len(list(filter(self._is_invalid_char, in_name.encode('ascii')))):
            return

        if self.etype == "dir" or self.etype == "file":
            name_bytes = bytearray(in_name.encode())
            for _ in range(self.NAME_LENGTH - len(name_bytes)):
                name_bytes.append(0)
            self._raw[self.NAME_OFFSET:self.NAME_OFFSET + self.NAME_LENGTH] = name_bytes


    @property
    def max_size(self):
        """ Get maximum size.

            Maximum size is different for "file" and "dir". For "file",
            max_size is the maximum potential data which can be fit into
            the sectors allocated to the file Entry. For "dir", max_size
            if the maximum potential number of Entry objects which can be
            fit into the sectors allocated to the directory Entry.

            Args: None.

            Returns (int):
                self.etype == "file": Size of file on disk/maximum potential file size
                self.etype == "dir": Maximum potential directory entries
        """

        if self.etype == "dir" or self.etype == "file":
            return int.from_bytes(self._raw[self.MAX_SIZE_OFFSET:self.MAX_SIZE_OFFSET + 4], "little")
        else:
            return 0


    @max_size.setter
    def max_size(self, in_value):
        """ Set maximum size.

            Sets provided value so long as Entry is "dir" or "file". Does not
            check sanity of in_value.

            Args:
                in_value (int): Value to set.

            Returns: None.
        """

        if self.etype == "dir" or self.etype == "file":
            tmp_bytes = int.to_bytes(in_value, 4, "little")
            self._raw[self.MAX_SIZE_OFFSET:self.MAX_SIZE_OFFSET + 4] = tmp_bytes


    @property
    def fat_offset(self):
        """ Get file table offset checkval.

            This appears to be used like a checkval. Slightly difference for
            links compares to files and dirs.

            Args: None.

            Returns:
                File table offset for the given entry.
        """

        fat_offset = int.from_bytes(self._raw[self.FAT_OFFSET:self.FAT_OFFSET + 4], "little")
        return fat_offset if self.etype == "link" else fat_offset - 8


    @fat_offset.setter
    def fat_offset(self, in_value):
        """ Set file table offset checkval.

            Sets provided value so long as self.etype is "dir" or "file".
            Does not check sanity of in_value.

            Args:
                in_value (int): New file table offset checkval.

            Returns: None.
        """

        if self.etype == "dir" or self.etype == "file":
            tmp_bytes = int.to_bytes(in_value + 8, 4, "little")
            self._raw[self.FAT_OFFSET:self.FAT_OFFSET + 4] = tmp_bytes


    @property
    def size(self):
        """ Get size.

            Args: None.

            Returns:
                'file': Actual file size.
                'dir': Number of occupied directory entries times 105. Still
                    making sense of this, as each entry occupies 119 bytes.
                'empty': 0
                # TODO 'link': UNKNOWN
        """

        return int.from_bytes(self._raw[self.SIZE_OFFSET:self.SIZE_OFFSET + 4], "little")


    @size.setter
    def size(self, in_value):
        """ Set size.

            Sets provided value so long as Entry is "dir" or "file". When
            setting "dir" size, keep in mind the 105/119 discrepancy.

            Args:
                in_value (int): Size in bytes.

            Returns: None.
        """

        if self.etype == "dir" or self.etype == "file":
            tmp_bytes = int.to_bytes(in_value, 4, "little")
            self._raw[self.SIZE_OFFSET:self.SIZE_OFFSET + 4] = tmp_bytes


    @property
    def flags(self):
        """ Get flags.
        
            Args: None.

            Returns (int): Flags.
        """
        return int.from_bytes(self._raw[self.FLAGS_OFFSET:self.FLAGS_OFFSET + 2], "little")


    @flags.setter
    def flags(self, in_value):
        """ Set flags.

            Sets provided value so long as Entry is "dir" or "file".

            Args:
                in_value (int): Flags.

            Returns: None.
        """

        if self.etype == "dir" or self.etype == "file":
            tmp_bytes = int.to_bytes(in_value, 2, "little")
            self._raw[self.FLAGS_OFFSET:self.FLAGS_OFFSET + 2] = tmp_bytes


    @property
    def contains(self):
        """ Get number of contents.

            The number of contents is straightforward: 1 if the Entry is a
            file, and 2+ if the Entry is a dir. For a dir, the value is based
            upon how many immediate subdirs are contained within. Since every
            dir contains at minimum "." and "..", this value will always be 2+.

            Args: None.

            Returns (int): Number of contents as described above.
        """

        return int.from_bytes(self._raw[self.CONTAINS_OFFSET:self.CONTAINS_OFFSET + 4], "little")


    @contains.setter
    def contains(self, in_value):
        """ Set number of contents.

            Sets provided value so long as Entry is "dir" or "file". Does not
            check for sanity.

            Args:
                in_value (int): Number of contents.
            
            Returns: None.
        """

        if self.etype == "dir" or  self.etype == "file" and in_value >= 1:
            tmp_bytes = int.to_bytes(in_value, 4, "little")
            self._raw[self.CONTAINS_OFFSET:self.CONTAINS_OFFSET + 4] = tmp_bytes
            self._raw[63] = 1   # The most magic of numbers, I do not know why this is needed.


    @property
    def dest_offset(self):
        """ Get destination offset.

            Get the offset to which this Entry points.

            Args: None.

            Returns (int): Destination offset in Ramdisk.
        """

        return int.from_bytes(self._raw[self.DEST_OFFSET:], "little")


    @dest_offset.setter
    def dest_offset(self, in_value):
        """ Set destination offset.

            Sets provided value so long as Entry is "dir" or "file".

            Args:
                in_value (int): Destination offset in Ramdisk.

            Returns: None.
        """

        if self.etype == "dir" or self.etype == "file":
            tmp_bytes = int.to_bytes(in_value, 4, "little")
            self._raw[self.DEST_OFFSET:self.DEST_OFFSET + 4] = tmp_bytes


    @property
    def raw(self):
        """ Get raw bytearray.

        Args: None.

        Returns (bytearray): Entire Entry.
        """

        return self._raw
