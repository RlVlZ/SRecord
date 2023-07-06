import argparse
import shlex
import SRecord as sr
import SRecordFile as srf
import os

from collections import namedtuple
from shutil import copyfile
from filecmp import cmp
from copy import deepcopy



#===========================================================================
# NamedTuple FuncDef : contains a function, its shortcuts and its arg parser
#===========================================================================

FuncDef = namedtuple('FuncPrs', ['fnc', 'sct', 'prs'])

#=====================================================================
# Class SubFuncSet to deal with functions names, shortcuts and parsers
#=====================================================================

class SubFuncSet():

    def __init__(self):
        self.parser_dict = {}
        self.shortCut_dict = {}
        self.func2shortCut_dict = {}
    
    def __getitem__(self, position):
        if position in self.shortCut_dict:
            return self.parser_dict[self.shortCut_dict[position]]
        elif position in self.parser_dict :
            return self.parser_dict[position]
        else:
            return None
    
    def __contains__(self, item):
        if self[item] == None:
            return False
        else:
            return True

    def addSubFunc(self, func_def):
        '''
        func_def is a named tuple : 
            func_def.fnc : a function
            func_def.sct : a string to be made as a short cut for func
            func_def.prs : a parser for the arguments needed for func
        '''
        self.parser_dict[func_def.fnc.__name__] = func_def.prs
        self.shortCut_dict[func_def.sct] = func_def.fnc.__name__
        self.func2shortCut_dict[func_def.fnc.__name__] = func_def.sct
        globals()[func_def.sct] = func_def.fnc

    def displayHelp(self):
        print("You may chose between the following actions :")
        for subF in self.parser_dict:
            print(f"\t* {subF} | {self.func2shortCut_dict[subF]}")
        print()
        print("For more information about an action : ACTION -h")
        print()

#==============================================
# Defining functions and their argument parsers
#==============================================

show_line_prs = argparse.ArgumentParser(prog="show_line", description="display the SRecord where is the given adress")
show_line_prs.add_argument('-a', '--address', help = 'address where the tagged memory area starts', nargs='+')
show_line_prs.add_argument('-nl', '--nb_lines', help='Number of line to display after the first one', nargs='?', default = 1, type=int)
def show_line(file, address, nb_lines):
    '''
    Display the line containing the address given
        Input   * file : SRecordFile object
                * address : string of hexadecimal address
    '''
    addr_u = file.convert_address(address)
    try :
        line_addr = file.get_data_coord(addr_u).line
    except srf.SRecordFileError as e:
        print("Given adress not found in current file")
        print(e)
    else :
        for i in range(nb_lines):
            try :
                print(file.data[line_addr])
                line_addr += len(file.data[line_addr].data_h)
            except KeyError:
                print("/!\ - Reaching end of sector.")

bin_disp_pars = argparse.ArgumentParser(prog="bin_disp", description="binary display of datas")
bin_disp_pars.add_argument('-a', '--address', help = 'address where the tagged memory area starts', nargs='+')
bin_disp_pars.add_argument('-nw', '--nb_words', help="number of words to display per line", nargs='?', default = 4, type=int)
bin_disp_pars.add_argument('-nl', '--nb_lines', help="number of lines to display", nargs='?', default=1, type=int)
bin_disp_pars.add_argument('-e', '--endianess', help="Endianess of words display", nargs='?', default='big', type=str)
def bin_disp(file, address, nb_words, nb_lines, endianess):
    '''
    Display a binary view of the data at address given, nb_words words for nb_lines lines
        Input   * file : SRecordFile object
                * address : address, not matter the format
                * nb_words : number of words to display per line
                * nb lines : number of lines to display
    '''
    addr_u = file.convert_address(address)
    print(file.binary_display_header(nb_words, endianess))
    for i in range(nb_lines):
        try:
            print(file.binary_display(addr_u + i*nb_words*4, nb_words, endianess))
        except srf.AccessSrecFileError as e:
            print(e)
            break

display_sectors_info_prs = argparse.ArgumentParser(prog='display_sectors_info', description='display information about sectors')
def display_sectors_info(file):
    print(file.get_sectors_infos())

patch_prs = argparse.ArgumentParser(prog="patch", description="change the data at a given adress with the value given")
patch_prs.add_argument('-a', '--address', help = 'address where the tagged memory area starts', nargs='+')
patch_prs.add_argument('-v', '--value', help='Hex value you want to write', required=True)
def patch(file, address, value):
    '''
    Patching the ADDRESS given with VALUE
        Input   * file : SRecordFile object
                * address : string of hexadecimal address
                * value : string of hexadecimal value to patch
    '''
    addr_u = file.convert_address(address)
    try:
        file.patch_SRecord_File(addr_u, value)
    except srf.SRecordFileError as e:
        print(e)


fix_cks_prs = argparse.ArgumentParser(prog='fix_cks', description="parse the current file and update the checksums")
def fix_cks(file):
    '''
    Compute and patch the checksum of a given SRec file
        Input   * file : SRecordFile object
    '''
    for srec in file:
        srec.update_checksum()
    print("Checksums fixed.\n")


apply_prs = argparse.ArgumentParser(prog='apply', description="write the modification done to the file w/o closing it")
def apply(file):
    '''
    write the changes made to the file
        Input   * file : SRecordFile object
    '''
    file.export(file.path)


patch_by_file_prs = argparse.ArgumentParser(prog="patch_by_file", description="patch the current file using data from another file")
patch_by_file_prs.add_argument('-a', '--address', help = 'address where the tagged memory area starts', nargs='+')
patch_by_file_prs.add_argument('-pf', '--patching_file', help='SRecord file containing data for patching', required=True)
def patch_by_file(file, address, patching_file):
    '''
    Patching the ADDRESS given in dest_f with values from data_f
        Input   * file : SRecordFile object
                * address : string of hexadecimal address
                * patching_file : (string) path to a SRecord file containing data to patch
    '''
    #Creating data string to patch destination file
    addr_u = file.convert_address(address)
    data = ''
    srec_data = srf.SRecordFile()
    srec_data.read_file(patching_file)
    for line in srec_data:
        data += ''.join(line.data_h)
    file.patch_SRecord_File(addr_u, data)


change_working_file_prs = argparse.ArgumentParser(prog="change_working_file", description="save the current file and open a new one")
change_working_file_prs.add_argument('-f', '--file', help = 'new file to load and work on', required=True)
def change_working_file(old_file: srf.SRecordFile, old_file_backup: srf.SRecordFile, file: str) -> srf.SRecordFile:
    '''
    Change the working file, after saving and closing the current one.
        Input   * old_file : SRecordFile object to save and close
                * file : (string) path to a SRecord file to work on
    /!\ old_file is a SRecordFile object while file is a path string
    '''
    old_file.export(old_file.path)
    if old_file != old_file_backup:
        old_file_backup.export(old_file_backup + 'bak')
    _new_file = srf.SRecordFile()
    print("Importing binary file")
    _new_file.read_file(file)
    print(f"{_new_file.name} successfully imported.")
    print(_new_file.get_file_infos())
    return _new_file

strings_prs = argparse.ArgumentParser(prog="strings", description="print strings found in the SRecordFile")
strings_prs.add_argument('-m', '--min_len', help = 'minimal lengh requiered to print a string', nargs='?', default = 3)
def strings(file, min_len):
    '''
    Display all the ascii strings longer than 2 chars found in the file
        Insput  * file : SRecordFile object in which the search is performed
    '''
    # low acceptance for ASCII. Will only consider numbers and letters.
    # i.e : 0x30 - 0x39 for numbers
    #       0x41 - 0x5A for upper case
    #       0x61 - 0x7A for lower case

    min_len = int(min_len)

    detected_string = ''
    all_data = []
    for addr in file.data:
        all_data += file.data[addr].data_u
    

    for byte in all_data:
        if byte in srf.ASCII:
            detected_string += chr(byte)
        else :
            if len(detected_string) >= min_len:
                print(detected_string)
                detected_string = ""
            else:
                detected_string = ""

add_tag_prs = argparse.ArgumentParser(prog="add_tag", description="add a tag to a memory field")
add_tag_prs.add_argument('-n', '--name', help = 'tag name', required=True)
add_tag_prs.add_argument('-a', '--address', help = 'address where the tagged memory area starts', nargs='+')
def add_tag(file, name, address):
    addr_u = file.convert_address(address)
    file.add_tag(name, addr_u)


print_tag_prs = argparse.ArgumentParser(prog='print_tag', description='print the datas designed by a tag')
print_tag_prs.add_argument('-n', '--name', help = 'tag name', required=True)
def print_tag(file, name):
    if name in file.tags:
        for i in range(file.tags[name].length):
            print(file.bytes[file.tags[name].start + i], end='')
        print()

print_tag_list_prs = argparse.ArgumentParser(prog="print_tag_list", description="Print the list of tags currently defined in the file")
def print_tag_list(file):
    if len(file.tags) == 0:
        print("No tag present in the file")
    else:
        [print(' - ' + tag_name) for tag_name in file.tags.keys()]

add_scope_prs = argparse.ArgumentParser(prog='add_scope', description='add a scope to monitor memory area')
add_scope_prs.add_argument('-n', '--name', help = 'tag name', required=True)
add_scope_prs.add_argument('-a', '--address', help = 'address where the tagged memory area starts', nargs='+')
add_scope_prs.add_argument('-nw', '--nb_words', help="number of words to display per line", nargs='?', default = 4, type=int)
add_scope_prs.add_argument('-nl', '--nb_lines', help="number of lines to display", nargs='?', default=1, type=int)
add_scope_prs.add_argument('-e', '--endianess', help="Endianess of words display", nargs='?', default='big', type=str)
def add_scope(file, name, address, nb_words, nb_lines, endianess):
    try:
        addr_u = file.convert_address(address)
        file.add_scope(name, addr_u, nb_words, nb_lines, endianess)
    except srf.AccessSrecFileError as e:
        print(e)

print_scope_prs = argparse.ArgumentParser(prog='print_scope', description='binary display of the given scope')
print_scope_prs.add_argument('-n', '--name', help = 'tag name', required=True)
def print_scope(file, name):
    try:
        scope = file.get_scope(name)
    except srf.AccessSrecFileError as e:
        print(e)
    else:
        bin_disp(file, scope.start, scope.nb_words, scope.nb_line, scope.endianess)


#Initializing our sub_func_set that will contains links between functions, their shortcuts and their parsers
sub_func_set = SubFuncSet()

#Populating our SubFuncSet
sub_func_set.addSubFunc(FuncDef(fnc=show_line, sct='sl', prs=show_line_prs))
sub_func_set.addSubFunc(FuncDef(fnc=bin_disp, sct='bd', prs=bin_disp_pars))
sub_func_set.addSubFunc(FuncDef(fnc=display_sectors_info, sct='dsi', prs=display_sectors_info_prs))
sub_func_set.addSubFunc(FuncDef(fnc=patch, sct='p', prs=patch_prs))
sub_func_set.addSubFunc(FuncDef(fnc=fix_cks, sct='fc', prs=fix_cks_prs))
sub_func_set.addSubFunc(FuncDef(fnc=apply, sct='a', prs=apply_prs))
sub_func_set.addSubFunc(FuncDef(fnc=patch_by_file, sct='pbf', prs=patch_by_file_prs))
sub_func_set.addSubFunc(FuncDef(fnc=change_working_file, sct='cwf', prs=change_working_file_prs))
sub_func_set.addSubFunc(FuncDef(fnc=strings, sct='s', prs=strings_prs ))
sub_func_set.addSubFunc(FuncDef(fnc=add_tag, sct = 'adt', prs=add_tag_prs))
sub_func_set.addSubFunc(FuncDef(fnc=print_tag, sct='pt', prs=print_tag_prs))
sub_func_set.addSubFunc(FuncDef(fnc=print_tag_list, sct='ptl', prs=print_tag_list_prs))
sub_func_set.addSubFunc(FuncDef(fnc=add_scope, sct='ads', prs=add_scope_prs))
sub_func_set.addSubFunc(FuncDef(fnc=print_scope, sct='ps', prs=print_scope_prs))

#######################################
# Main function : entry point for SRec 
#######################################

def main():
    #Init_pars get the argv array from the command line.
    #It expects a file path given as argument
    init_pars = argparse.ArgumentParser(description="Load a SRecord file to work with")
    init_pars.add_argument('-f', '--file', help='File Name')

    #We use the object ini_pars to parse the command line arguments
    args = init_pars.parse_args()

    #from it we get the "file" argument and use it to open the file
    print("Importing binary file")
    SRec_f = srf.SRecordFile()
    SRec_f.read_file(args.file)
    SRec_f_backup = deepcopy(SRec_f)
    print(f"{SRec_f.name} successfully imported.")
    print(SRec_f.get_file_infos())

    command = ''

    while command not in ["quit", "q", "exit", "ciao"]:
        #We use input to get a string from the user, that will be formated as a call to a script
        command = input("\033[0;91m {}\033[00m".format(SRec_f.name + ">"))

        #We cut this string into arguments using spaces
        options = shlex.split(command, posix=0) #posix=0 retains backslashes in Windows paths

        #We store the first element (the name of the subfunction) into command
        #In case nothing was entered before hiting enter, loop
        try:
            command = options.pop(0).lower()
        except IndexError:
            continue

        #If the command given is in the parsers dictionnary, we apply its parser to the options
        #Then we gives the result to the correct function (the command string is evaluated which trigger the function itself)
        if command in sub_func_set:
            try:
                arguments = sub_func_set[command].parse_args(options)
                ret = eval(command)(SRec_f, **vars(arguments))
                #The only function to return anything is the change_working_file() one, meaning we want to update SRec_f
                if type(ret) == srf.SRecordFile:
                    SRec_f = ret
            except SystemExit:
                #In case we get a SystemExit, it's raised by the function parser.
                #We then show the function parser help message and keep running
                #This is to avoid the exit usually called when asking for -h
                pass

        #Various ways to exit, if the file has not changed, we suppress its backup
        elif command in ["quit", "q", "exit", "ciao"]:
            print("\n ############")
            print(" Ciao bella !")
            print(" ############")
            if SRec_f == SRec_f_backup:
                SRec_f.export(SRec_f.path)
            else:
                SRec_f.export(SRec_f.path)
                SRec_f_backup.export(SRec_f_backup.path + "_bak")
        #Here we deal with the help commands
        elif command in ["-h", "--help", "help", "h"]:
            sub_func_set.displayHelp()
        #Finally if the command entered is not a sub_function, nore a quit or a help :
        else:
            print(f"{command} : unknown command.")
            sub_func_set.displayHelp()
    
if __name__ == '__main__':
    main()
