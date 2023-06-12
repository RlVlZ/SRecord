import os
import re
os.system('color')
from functools import partial

class SRecordError(Exception):
    pass

class CorruptedSRecError(SRecordError):
    pass

class UpdateSRecError(SRecordError):
    pass

class AccessSRecError(SRecordError):
    pass

INT = partial(int, base = 16)

NOT_HEX_CHAR = re.compile(r'[^0-9A-Fa-f]')

class SRecord:
    """Class containing s-record"""
    ADDR_LEN = {
            'S0':2,     #header s-record
            'S1':2,     #data   s-record
            'S2':3,     #data   s-record
            'S3':4,     #data   s-record
            'S5':2,     #count  s-record
            'S7':4,     #footer s-record
            'S8':3,     #footer s-record
            'S9':2      #footer s-record
            }

    def __init__(self, srec):
        '''Takes a string and extract srecord infos'''
        srec = srec.strip()
        if len(srec)%2 != 0:
            raise CorruptedSRecError("Odd number of char : not an SRecord")
        if srec[:2] not in SRecord.ADDR_LEN:
            raise CorruptedSRecError("Unknown type of SRecord")
        else:
            self.s_type = srec[:2]
            self.count_h = srec[2:4]
            self.count_u = INT(self.count_h)
            self.address_h = srec[4: 4 + self.addr_len('char')]
            self.address_u = INT(self.address_h)
            data = srec[4 + self.addr_len('char'): -2]
            self.data_h = [data[i:i+2] for i in range(0, len(data), 2)]
            self.data_u = [INT(byte) for byte in self.data_h]
            self.checksum = srec[-2:]
        if not self.check_data_len():
            raise CorruptedSRecError("Count field value is incorrect")
        if data and NOT_HEX_CHAR.findall(data):
            raise CorruptedSRecError("The data field contains non-hexadecimal character")

    def addr_len(self, byte_or_char = 'byte'):
        '''
        return the size of address field in characters
        if byte_or_char is set to char, returns the number of char
        else, number of bytes is returned
        '''
        if byte_or_char == 'char':
            return SRecord.ADDR_LEN[self.s_type]*2
        elif byte_or_char == 'byte':
            return SRecord.ADDR_LEN[self.s_type]
        else :
            raise AccessSRecError("Invalid 'byte_or_char' arg in function 'addr_len'")

    def check_data_len(self):
        return (len(self.data_h) + len(self.address_h + self.checksum)/2) == self.count_u

    def __repr__(self):
        return f"SRec of type {self.s_type}, address {self.address_h}"

    def __str__(self):
        '''return a nicely formated string for display purpose'''
        s_type = "\033[0;96m {}\033[00m".format(self.s_type)
        count = "\033[0;95m {}\033[00m".format(self.count_h)
        address = "\033[0;92m {}\033[00m".format(self.address_h)
        data = "\033[0;93m {}\033[00m".format(''.join(self.data_h))
        checksum = "\033[0;31m {}\033[00m".format(self.checksum)
        return s_type + count + address + data + checksum


    def __iter__(self):
        return (elem for elem in (self.s_type, self.count_h, self.address_h, self.data_h, self.checksum))

    def __getitem__(self, position, hex_or_int = 'hex'):
        '''return the byte at position (0 start indexation)'''
        if hex_or_int == 'int':
            return(self.data_u[position])
        else:
            return(self.data_h[position])

    def __setitem__(self, position, value):
        '''set the byte at position with value (0 start indexation)'''
        if type(value) is not str:
            raise UpdateSRecError("SRecord class: __setitem__: 'value' argument must be a string")
        if NOT_HEX_CHAR.findall(value):
            raise UpdateSRecError("SRecord class: __setitem__: 'value' argumen must be an hex string")
        if len(value) > 2:
            raise UpdateSRecError("SRecord class: __setitem__: 'value' argument can't be longer than a byte")
        value = value.upper().zfill(2)
        self.data_h[position] = value
        self.data_u[position] = INT(value)
        self.update_checksum()

    def __lt__(self, other):
        return self.address_u < other.address_u

    def __le__(self, other):
        return self.address_u <= other.address_u

    def __gt__(self, other):
        return(self.address_u > other.address_u)

    def __ge__(self, other):
        return(self.address_u >= other.address_u)

    def compute_checksum(self):
        sum_address = sum([INT(self.address_h[i : i+2]) for i in range(0, self.addr_len('char'), 2)])
        if not self.data_h:
            sum_data = 0
        else:
            sum_data = sum(self.data_u)
        s_sum = self.count_u + sum_address + sum_data
        sum_lsb = s_sum & 0xFF
        return "{0:0>2X}".format(sum_lsb ^ 0xFF)

    def update_checksum(self):
        self.checksum = self.compute_checksum()
    
    def end_address(self):
        '''
        return address of the last byte of the SRecord
        '''
        return self.address_u + len(self.data_u) - 1

    def to_string(self, end = ''):
        '''
        return the SRec as a simple string
        '''
        return self.s_type + self.count_h + self.address_h + ''.join(self.data_h) + self.checksum + end