# -*- coding: utf-8 -*-
'''The Shared-Cache strings (dsc) file parser.'''

import os
import posixpath
import struct
from uuid import UUID
from bisect import bisect_right

from UnifiedLog import data_format
from UnifiedLog import logger


class Dsc(data_format.BinaryDataFormat):
    '''Shared-Cache strings (dsc) file parser.

    Attributes:
      uuid_entries (list[tuple[int, int, UUID, str, str]]): UUID entries.
    '''

    def __init__(self, v_file):
        '''Initializes a shared-Cache strings (dsc) file parser.

        Args:
          v_file (VirtualFile): a virtual file.
        '''
        super(Dsc, self).__init__()
        self._file = v_file
        self._format_version = None
        self.uuid_entries  = []  # [ [v_off,  size,  uuid,  lib_path, lib_name], [..], ..] # v_off is virt offset
        self.uuid_entry_dict = {}
        self.uuid_entry_offsets = []
        self.num_uuid_entries = 0
        self.range_entries = {}  # {v_off: [uuid_index, v_off, data_offset, data_len]} # data_offset is absolute in file
        self.range_entry_offsets = []
        self.num_range_entries = 0
        self.fmt_cache = {}


    def _ParseFileObject(self, file_object):
        '''Parses a dsc file-like object.

        Args:
          file_object (file): file-like object.

        Returns:
          bool: True if the dsc file-like object was successfully parsed,
              False otherwise.

        Raises:
          IOError: if the dsc file cannot be parsed.
          OSError: if the dsc file cannot be parsed.
          struct.error: if the dsc file cannot be parsed.
        '''
        file_header_data = file_object.read(16)
        if file_header_data[0:4] != b'hcsd':
            signature_base16 = binascii.hexlify(file_header_data[0:4])
            logger.info((
                'Wrong signature in DSC file, got 0x{} instead of 0x68637364 '
                '(hcsd)').format(signature_base16))
            return False

        major_version, minor_version, num_range_entries, num_uuid_entries = (
            struct.unpack("<HHII", file_header_data[4:16]))

        if major_version > 2:
            raise UserWarning("Unsupported DSC Format")

        self._format_version = '{0:d}.{1:d}'.format(major_version, minor_version)

        while len(self.range_entries) < num_range_entries:
            if major_version == 1:
                range_entry_data = file_object.read(16)

                uuid_index, v_off, data_offset, data_len = struct.unpack(
                    "<IIII", range_entry_data)
                range_entry = [uuid_index, v_off, data_offset, data_len]
                if v_off in self.range_entries:
                    raise ValueError("v_off not unique!")
                self.range_entries[v_off] = range_entry
            elif major_version == 2:
                range_entry_data = file_object.read(24)
                v_off, data_offset, data_len, uuid_index = struct.unpack(
                    "<QIIQ", range_entry_data)
                range_entry = [uuid_index, v_off, data_offset, data_len]
                if v_off in self.range_entries:
                    raise ValueError("v_off not unique!")
                self.range_entries[v_off] = range_entry
            else:
                raise UserWarning("Unsupported DSC Format")

        self.range_entry_offsets = sorted([k for k in self.range_entries.keys()])
        self.num_range_entries = len(self.range_entry_offsets)

        uuid_entry_offset = file_object.tell()
        while len(self.uuid_entries) < num_uuid_entries:
            if major_version == 1:
                file_object.seek(uuid_entry_offset, os.SEEK_SET)
                uuid_entry_data = file_object.read(28)
                uuid_entry_offset += 28

                v_off, size = struct.unpack("<II", uuid_entry_data[:8])
                uuid_object = UUID(bytes=uuid_entry_data[8:24])
                data_offset = struct.unpack("<I", uuid_entry_data[24:])[0]

                file_object.seek(data_offset, os.SEEK_SET)
                path_data = file_object.read(1024) # File path should not be >1024

                lib_path = self._ReadCString(path_data)
                lib_name = posixpath.basename(lib_path)
            elif major_version == 2:
                file_object.seek(uuid_entry_offset, os.SEEK_SET)
                uuid_entry_data = file_object.read(32)
                uuid_entry_offset += 32

                v_off, size = struct.unpack("<QI", uuid_entry_data[:12])
                uuid_object = UUID(bytes=uuid_entry_data[12:28])
                data_offset = struct.unpack("<I", uuid_entry_data[28:])[0]

                file_object.seek(data_offset, os.SEEK_SET)
                path_data = file_object.read(1024)  # File path should not be >1024

                lib_path = self._ReadCString(path_data)
                lib_name = posixpath.basename(lib_path)
            else:
                raise UserWarning("Unsupported DSC Format")

            self.uuid_entries.append([v_off, size, uuid_object, lib_path, lib_name])
            if v_off in self.uuid_entry_dict:
                raise ValueError("expected v_off to be unique in uuid_entries")
            self.uuid_entry_dict[v_off] = [v_off, size, uuid_object, lib_path, lib_name]

        self.uuid_entry_offsets = sorted([k for k in self.uuid_entry_dict.keys()])
        self.num_uuid_entries = len(self.uuid_entry_offsets)

        uuid_entry_offset2 = file_object.tell()

        return True

    def FindVirtualOffsetEntries(self, v_offset):
        '''Return tuple (range_entry, uuid_entry) where range_entry[xx].size <= v_offset'''

        # find the the range_entry by searching for idx where we can insert
        # v_offset without breaking sort. bisect_right makes sure that our
        # index is one higher than the index of the range we want to check
        pos=bisect_right(self.range_entry_offsets, v_offset, 0, self.num_range_entries)
        # now, the v_offset is somewhere *after* the previous range, so we need
        # to check if the v_offsets falls within the *previous* range
        if pos > 0:
            range_offset = self.range_entry_offsets[pos-1]
            # get the range
            a = self.range_entries[range_offset]

            # now check if the v_offset is within the range
            if (a[1] + a[3]) > v_offset:
                ret_range_entry = a
                ret_uuid_entry = self.uuid_entries[a[0]]
                return (ret_range_entry, ret_uuid_entry)

        #Not found
        logger.error('Failed to find v_offset in Dsc!')
        return (None, None)


    def ReadFmtStringAndEntriesFromVirtualOffset(self, v_offset):
        '''Reads the format string, range and UUID entry for a specific offset.

        Args:
          v_offset (int): virtual (or dsc range) offset.

        Returns:
          tuple: that contains:
            str: format string.
            tuple[int, int, int, int]: range entry.
            tuple[int, int, UUID, str, str]: UUID entry.

        Raises:
          KeyError: if no range entry could be found corresponding the offset.
          IOError: if the format string cannot be read.
        '''

        if v_offset in self.fmt_cache:
            return self.fmt_cache[v_offset]

        range_entry, uuid_entry = self.FindVirtualOffsetEntries(v_offset)
        if not range_entry:
            raise KeyError('Missing range entry for offset: 0x{0:08x}'.format(
                v_offset))

        rel_offset = v_offset - range_entry[1]
        file_object = self._file.file_pointer
        file_object.seek(range_entry[2] + rel_offset)
        cstring_data = file_object.read(range_entry[3] - rel_offset)
        cstring = self._ReadCString(cstring_data, range_entry[3] - rel_offset)
        self.fmt_cache[v_offset] = (cstring, range_entry, uuid_entry)
        return cstring, range_entry, uuid_entry


    def GetUuidEntryFromVirtualOffset(self, v_offset):
        '''Returns uuid_entry where uuid_entry[xx].v_off <= v_offset and falls within allowed size'''

        # find the the range_entry by searching for idx where we can insert
        # v_offset without breaking sort. bisect_right makes sure that our
        # index is one higher than the index of the range we want to check
        pos=bisect_right(self.uuid_entry_offsets, v_offset, 0, self.num_uuid_entries)
        # now, the v_offset is somewhere *after* the previous range, so we need
        # to check if the v_offsets falls within the *previous* range
        if pos > 0:
            uuid_offset = self.uuid_entry_offsets[pos-1]
            # get the range
            b = self.uuid_entry_dict[uuid_offset]

            # now check if the v_offset is within the uuid range
            if (b[0] + b[1]) > v_offset:
                return b

        logger.error('Failed to find uuid_entry for v_offset 0x{:X} in Dsc!'.format(v_offset))
        return None

    def DebugPrintDsc(self):
        logger.debug("DSC version={0:s} file={1:s}".format(
            self._format_version or "Unknown version", self._file.filename))

        logger.debug("Range entry values")
        for range_entry in self.range_entries:
            logger.debug("{0:d} {1:d} {2:d} {3:d}".format(
                range_entry[0], range_entry[1], range_entry[2], range_entry[3]))

        logger.debug("Uuid entry values")
        for uuid_entry in self.uuid_entries:
            logger.debug("{0:d} {1:d} {2!s} {3:s} {3:s}".format(
                uuid_entry[0], uuid_entry[1], uuid_entry[2], uuid_entry[3],
                uuid_entry[4]))

    def Parse(self):
        '''Parses a dsc file.

        self._file.is_valid is set to False if this method encounters issues
        parsing the file.

        Returns:
          bool: True if the dsc file-like object was successfully parsed,
              False otherwise.
        '''
        file_object = self._file.open()
        if not file_object:
          return False

        try:
            result = self._ParseFileObject(file_object)
        except (IOError, OSError, struct.error):
            logger.exception('DSC Parser error')
            result = False

        if not result:
            self._file.is_valid = False

        return result
