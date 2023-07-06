import SRecord as sr
import collections
import os

from copy import deepcopy
from bisect import bisect_right

ASCII = list(range(0x30, 0x39)) + list(range(0x41, 0x5a)) + list(range(0x61, 0x7a))

Coord = collections.namedtuple('Coord', ['line', 'idx'])

Sector = collections.namedtuple('Sector', ['start', 'end'])

Tag = collections.namedtuple('Tag', ['start', 'length'])

Scope = collections.namedtuple('Scope', ['start', 'nb_words', 'nb_line', 'endianess'])

class SRecordFileError(Exception):
    pass

class AccessSrecFileError(SRecordFileError):
    pass

class SRecordFile:

    def __init__(self):
        '''
        This function takes a motorola SRecord file and outputs a SRecordFile instance as follow :
            a list of header SRecord
            a list of footer SRecord
            a dictionnary of data SRecord, each SRecord having its own address for key
        '''
        self.tags = {}
        self.scopes = {}
        self.sectors = []
        self.path = None
        self.name = None
        self.header  = collections.OrderedDict()
        self.footer  = collections.OrderedDict()
        self.data    = {}
        self.bytes = {}
        self.max_addr_len = 0
        self.max_data_len = 0
        self.addr_list = []
        self.lower_addr = 0
        self.higher_addr = 0
        self.addrFormat = None

    def read_file(self, file_name):
        _start = ''
        _previous_Srec = sr.SRecord('S104000000FF')
        self.path = file_name
        self.name = os.path.basename(file_name)
        with open(file_name, 'r') as srec_f:
            srec_lines = srec_f.read().splitlines()
        for line in srec_lines:
            crt_srec = sr.SRecord(line)
            for i, byte in enumerate(crt_srec.data_h):
                self.bytes[crt_srec.address_u + i] = byte
            if crt_srec.s_type == 'S0':
                self.header[crt_srec.address_u] = crt_srec
            elif crt_srec.s_type in ('S7', 'S8', 'S9'):
                self.footer[crt_srec.address_u] = crt_srec
            else:
                self.data[crt_srec.address_u] = crt_srec
                if _start == '':
                    _start = crt_srec.address_u
                elif crt_srec.address_u != _previous_Srec.end_address() + 1 :
                    self.sectors.append(Sector(start=_start, end= _previous_Srec.end_address()))
                    _start = crt_srec.address_u
                _previous_Srec = crt_srec
        self.sectors.append(Sector(start=_start, end=_previous_Srec.end_address()))

        self.data = collections.OrderedDict(sorted(self.data.items()))
        self.max_addr_len = max(SRec.addr_len('char') for SRec in self.data.values())
        self.max_data_len = max([len(SRec.data_h) for SRec in self.data.values()])
        self.addr_list = list(self.data.keys())
        self.lower_addr = self.addr_list[0]
        self.higher_addr = self.data[self.addr_list[-1]].end_address()
        #update tags with sections first words
        for i, sector in enumerate(self.sectors):
            self.tags["sec" + str(i)] = sector.start
        #format string usable to display addresses at the same lenght
        self.addrFormat = f"{{0:0>{self.max_addr_len}X}}"

    
    def __deepcopy__(self, memo):
        id_self = id(self)
        _copy = memo.get(id_self)
        if _copy is None:
            _copy = SRecordFile()
            _copy.tags = deepcopy(self.tags)
            _copy.scopes = deepcopy(self.scopes)
            _copy.sectors = deepcopy(self.sectors)
            _copy.path = deepcopy(self.path)
            _copy.name = deepcopy(self.name)
            _copy.header  = deepcopy(self.header)
            _copy.footer  = deepcopy(self.footer)
            _copy.data    = deepcopy(self.data)
            _copy.bytes = deepcopy(self.bytes)
            _copy.max_addr_len = deepcopy(self.max_addr_len)
            _copy.max_data_len = deepcopy(self.max_data_len)
            _copy.addr_list = deepcopy(self.addr_list)
            _copy.lower_addr = deepcopy(self.lower_addr)
            _copy.higher_addr = deepcopy(self.higher_addr)
            _copy.addrFormat = deepcopy(self.addrFormat)
            memo[id_self] = _copy
        return _copy
    
    def __eq__(self, obj):
        if isinstance(obj, type(self)):
            if obj.bytes == self.bytes :
                return True
            else:
                return False
        else:
            raise SRecordFile("Compared object must be SRecordFile")
    
    def contains_address(self, address):
        return address in self.bytes
    
    def convert_address(self, address):
        '''
        This function provides a mean to make sure an address can be used as an input
        Address here can be a list, due to the way we parse user input
        '''
        if type(address) == list:
            # A list means user input, so either a math expression or an hex value
            # If one element in the list we expect it to be aither an hex value or a tag name
            if len(address) == 1:
                address = address[0]
                if address in self.tags:
                    return self.tags[address]
                elif address.lower().startswith('0x'):
                    address = address[2:]
                try:
                    return sr.INT(address)
                except ValueError:
                    raise AccessSrecFileError("Address given cannot be resolved to an integer")
            # If three elements in the list we should have tag + offset
            elif len(address) == 3:
                tag, operand, offset = address
                if operand in ['+', '-']:
                    try:
                        return eval(f"{self.tags[tag]} {operand} {sr.INT(offset)}")
                    except:
                        raise AccessSrecFileError("Address given cannot be resolved to an integer")
        elif type(address) == int:
            return address
        else:
            raise AccessSrecFileError("Address given cannot be resolved to an integer")

    def get_file_infos(self):
        file_infos = 20*'-' + '\n'
        file_infos += f"File contains {len(self.header)+len(self.footer)+len(self.data)} SRecords,\n"
        file_infos += f"including {len(self.data)} data SRecords.\n"
        file_infos += 20*'-' + '\n'
        file_infos += f"   Lower address   :\t0x{self.addrFormat.format(self.lower_addr)}\n"
        file_infos += f"   Higher address :\t0x{self.addrFormat.format(self.higher_addr)}\n"
        file_infos += 20*'-' + '\n'
        file_infos += self.get_sectors_infos()
        return file_infos
    
    def get_sectors_infos(self):
        sectors_infos = 20*'-' + '\n'
        for i, sector in enumerate(self.sectors):
            sectors_infos += f"Sector {i} starts at address 0x{self.addrFormat.format(sector.start)}, ends at address 0x"
            sectors_infos += f"{self.addrFormat.format(sector.end)}\n"
        sectors_infos += 20*'-' + '\n'
        return sectors_infos

    def __iter__(self):
        headers = list(self.header.values())
        datas = list(self.data.values())
        footers = list(self.footer.values())
        return (item for item in (headers + datas + footers))

    def __getitem__(self, position):
        '''
        This function returns the SRec at posision if it exists
        Position is the address, integer format
        '''
        try:
            return self.data[position]
        except KeyError:
            raise AccessSrecFileError("Not an SRecordFile address")

    def __setitem__(self, position, value):
        '''
        This function set the byte at address "position" to "value"
        '''
        data_coord = self.get_data_coord(position)
        self[data_coord.line][data_coord.idx] = value

    def get_data_coord(self, position):
        '''
        Input : position is an address inside the file, integer format
        Output : a Coord named tuple, with line and idx
        '''
        if self.contains_address(position):
            addr_line = self.addr_list[bisect_right(self.addr_list, position) - 1]
            addr_byte = position - addr_line
            return Coord(line=addr_line, idx=addr_byte)
        else:
            raise AccessSrecFileError("get_data_coord is being given an address in-between two sectors")

    def patch_SRecord_File(self, position, value):
        '''
        Input : position is an address inside the file, integer format
                value : the new value of the data, hexadecimal format
        Output : None, self will be updated
        '''
        if len(value)%2 != 0:
            raise SRecordFileError("Patching requieres full byte data, i.e. an even number of char")
        data_coord = self.get_data_coord(position)
        patching_bytes = [value[i-2:i].upper() for i in range(len(value), 0, -2)]
        while patching_bytes:
            self.bytes[position] = patching_bytes[-1]
            self[data_coord.line][data_coord.idx] = patching_bytes.pop()
            position +=1
            data_coord = self.get_data_coord(position)
    
    #========================#
    # BINARY DISPLAY SECTION #
    #========================#
    
    def get_word(self, pos, endianess='big'):
        '''
        Given a integer address, this function returns the word stored at this address (4 bytes) as a byte list
        '''
        if self.contains_address(pos) and self.contains_address(pos + 4):
            if endianess == 'big':
                return [self.bytes[pos + x] for x in range(4)]
            elif endianess == 'little' :
                return [self.bytes[pos + x] for x in range(3, -1, -1)]
            else :
                raise AccessSrecFileError("Unknown endianess option")
        else:
            raise AccessSrecFileError("Given address not present in the file")

    def binary_display_header(self, nr_words, endianess = 'big'):
        header = (self.max_addr_len + 3) * ' '
        header += (nr_words*4*3 + (nr_words - 1) * 2 - 1)*"-"
        header += '\n'
        header += (self.max_addr_len + 3) * ' '
        for i in range(nr_words):
            if endianess == 'big':
                for j in range(4):
                    header += "{0:0>2X} ".format(4*i + j)
            elif endianess == 'little':
                for j in range(3, -1, -1):
                    header += "{0:0>2X} ".format(4*i + j)
            else:
                raise AccessSrecFileError("Unknown endianess option")
            header += "  "
        header += '\n'
        header += (self.max_addr_len + 3) * ' '
        header += (nr_words*4*3 + (nr_words - 1) * 2 - 1)*"-"
        return header

    def binary_display(self, pos, nr_words = 4, endianess = 'big'):
        '''
        Given an integer address, this function will return a line of words, binary view
        '''
        first_addr = self.addrFormat.format(pos)
        words = [self.get_word(pos + 4*x, endianess) for x in range(nr_words)]
        displ_char = ''
        ascii_char = ''
        for word in words:
            for byte in word:
                if sr.INT(byte) in ASCII:
                    ascii_char += chr(sr.INT(byte))
                else:
                    ascii_char += '.'
                displ_char += f" {byte}"
            displ_char += "  "
        return first_addr + ": " + displ_char + "   " + ascii_char
    
    #=====================#
    # Dealing with scopes #
    #=====================#
    
    def add_scope(self, name, address, nb_words = 4, nb_line = 1, endianess = 'big'):
        if self.contains_address(address) and self.contains_address(address + 4*nb_words*nb_line):
            self.tags[name] = address
            self.scopes[name] = Scope(start=address, nb_words=nb_words, nb_line=nb_line, endianess=endianess)
        else:
            raise AccessSrecFileError("Given address field not present in the file")
    
    def get_scope(self, name):
        if name in self.scopes :
            return self.scopes[name]
        else:
            raise AccessSrecFileError("Given name is not in scope list")

    #===================#
    # Dealing with tags #
    #===================#

    def add_tag(self, name, address):
        if self.contains_address(address):
            self.tags[name] = address
        else:
            raise AccessSrecFileError("Given address field not present in the file")
    

    def export(self, name):
        '''
        This function write the SRecFile Object into a .s19 file
        '''
        with open(name, 'w+') as SRec_f:
            for addr in self.header:
                SRec_f.write(self.header[addr].to_string(end='\n'))
            for addr in self.data:
                SRec_f.write(self.data[addr].to_string(end='\n'))
            for addr in self.footer:
                SRec_f.write(self.footer[addr].to_string(end='\n'))
