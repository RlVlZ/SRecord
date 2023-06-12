import SRecord as sr
import collections
import os

from bisect import bisect_right

Coord = collections.namedtuple('Coord', ['line', 'idx'])

Sector = collections.namedtuple('Sector', ['start', 'end'])

class SRecordFileError(Exception):
    pass

class AccessSrecFileError(SRecordFileError):
    pass

class SRecordFile:

    def __init__(self, file_name):
        '''
        This function takes a motorola SRecord file and outputs a SRecordFile instance as follow :
            a list of header SRecord
            a list of footer SRecord
            a dictionnary of data SRecord, each SRecord having its own adress for key
        '''
        self.sectors = []
        self.start = ''
        self.path = file_name
        self.name = os.path.basename(file_name)
        print("Importing file ", self.name)
        self.header  = collections.OrderedDict()
        self.footer  = collections.OrderedDict()
        self.data    = {}
        previous_Srec = sr.SRecord('S104000000FF')
        with open(file_name, 'r') as srec_f:
            srec_lines = srec_f.read().splitlines()
        for line in srec_lines:
            crt_srec = sr.SRecord(line)
            if crt_srec.s_type == 'S0':
                self.header[crt_srec.address_u] = crt_srec
            elif crt_srec.s_type in ('S7', 'S8', 'S9'):
                self.footer[crt_srec.address_u] = crt_srec
            else:
                self.data[crt_srec.address_u] = crt_srec
                if self.start == '':
                    self.start = crt_srec.address_h
                elif crt_srec.address_u != previous_Srec.end_address() + 1 :
                    self.sectors.append(Sector(start=self.start, end= previous_Srec.end_address()))
                    self.start = crt_srec.address_h
                previous_Srec = crt_srec
        self.sectors.append(Sector(start=self.start, end=previous_Srec.end_address()))

        self.data = collections.OrderedDict(sorted(self.data.items()))
        self.max_addr_len = max(SRec.addr_len() for SRec in self.data.values())
        self.max_data_len = max([len(SRec.data_h) for SRec in self.data.values()])
        self.addr_list = list(self.data.keys())
        self.lower_addr = self.addr_list[0]
        self.higher_addr = self.data[self.addr_list[-1]].end_address()
        #format string usable to display addresses at the same lenght
        self.addrFormat = f"{{0:0>{self.max_addr_len}X}}"
        print(f"{self.name} successfully imported.")
        print(self.get_file_infos())


    def get_file_infos(self):
        file_infos = 20*'-' + '\n'
        file_infos += f"File contains {len(self.header)+len(self.footer)+len(self.data)} SRecords,\n"
        file_infos += f"including {len(self.data)} data SRecords.\n"
        file_infos += 20*'-' + '\n'
        file_infos += f"   Lower adress   :\t0x" + self.addrFormat.format(self.lower_addr) + '\n'
        file_infos += f"   Higher address :\t0x" + self.addrFormat.format(self.higher_addr) + '\n'
        file_infos += 20*'-' + '\n'
        for i, sector in enumerate(self.sectors):
            file_infos += f"Sector {i} starts at adress 0x{sector.start}, ends at adress 0x"
            file_infos += self.addrFormat.format(sector.end) + '\n'
        file_infos += 20*'-' + '\n'
        return file_infos

    def __iter__(self):
        headers = list(self.header.values())
        datas = list(self.data.values())
        footers = list(self.footer.values())
        return (item for item in (headers + datas + footers))

    def __getitem__(self, position):
        '''
        This function returns the SRec at posision if it exists
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
        Input : position is an adress inside the file, integer format
        Output : a Coord named tuple, with line and idx
        '''
        if position < self.lower_addr:
            raise AccessSrecFileError("get_data_coord is being given an address too low")
        elif position > self.higher_addr:
            raise AccessSrecFileError("get_data_coord is being given an address too high")
        else:
            addr_line = self.addr_list[bisect_right(self.addr_list, position) - 1]
            if position <= self.data[addr_line].end_address():
                addr_byte = position - addr_line
                return Coord(line=addr_line, idx=addr_byte)
            else:
                raise AccessSrecFileError("get_data_coord is being fiven an address in-between two sectors")

    def patch_SRecord_File(self, position, value):
        '''
        Input : position is an address inside the file, hexadecimal format
                value : the new value of the data, hexadecimal format
        Output : None, self will be updated
        '''
        pos = sr.INT(position)
        if len(value)%2 != 0:
            raise SRecordFileError("Patching requieres full byte data, i.e. an even number of char")
        data_coord = self.get_data_coord(pos)
        patching_bytes = [value[i-2:i] for i in range(len(value), 0, -2)]
        while patching_bytes:
            self[data_coord.line][data_coord.idx] = patching_bytes.pop()
            pos +=1
            data_coord = self.get_data_coord(pos)

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

