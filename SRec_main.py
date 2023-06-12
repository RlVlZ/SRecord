import argparse
import shlex
import SRecord as sr
import SRecordFile as srf
import os

from collections import namedtuple
from shutil import copyfile
from filecmp import cmp

ASCII = list(range(0x30, 0x39)) + list(range(0x41, 0x5a)) + list(range(0x61, 0x7a))

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

#==============================================
# Defining functions and their argument parsers
#==============================================

show_line_prs = argparse.ArgumentParser(prog="show_line", description="display the SRecord where is the given adress")
show_line_prs.add_argument('-a', '--address', help='Hex adress of the data you want to display.No 0x needed')
show_line_prs.add_argument('-nl', '--nb_lines', help='Number of line to display after the first one', nargs='?', default = 1, type=int)
def show_line(file, address, nb_lines):
    '''
    Display the line containing the address given
        Input   * file : SRecordFile object
                * address : string of hexadecimal address
    '''
    addr_u = sr.INT(address)
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


patch_prs = argparse.ArgumentParser(prog="patch", description="change the data at a given adress with the value given")
patch_prs.add_argument('-a', '--address', help='Hex adress of the data you want to patch. No 0x needed')
patch_prs.add_argument('-v', '--value', help='Hex value you want to write')
def patch(file, address, value):
    '''
    Patching the ADDRESS given with VALUE
        Input   * file : SRecordFile object
                * address : string of hexadecimal address
                * value : string of hexadecimal value to patch
    '''
    file.patch_SRecord_File(address, value)


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
patch_by_file_prs.add_argument('-a', '--address', help='adress of the data you want to patch')
patch_by_file_prs.add_argument('-pf', '--patching_file', help='SRecord file containing data for patching')
def patch_by_file(file, address, patching_file):
    '''
    Patching the ADDRESS given in dest_f with values from data_f
        Input   * file : SRecordFile object
                * address : string of hexadecimal address
                * patching_file : (string) path to a SRecord file containing data to patch
    '''
    #Creating data string to patch destination file
    data = ''
    srec_data = srf.SRecordFile(patching_file)
    for line in srec_data:
        data += ''.join(line.data_h)
    file.patch_SRecord_File(address, data)


change_working_file_prs = argparse.ArgumentParser(prog="change_working_file", description="save the current file and open a new one")
change_working_file_prs.add_argument('-f', '--file', help = 'new file to load and work on')
def change_working_file(old_file, file):
    '''
    Change the working file, after saving and closing the current one.
        Input   * old_file : SRecordFile object to save and close
                * file : (string) path to a SRecord file to work on
    /!\ old_file is a SRecordFile object while file is a path string
    '''
    old_file.export(old_file.path)
    if cmp(old_file.path, old_file.path + '_bak'):
        os.remove(old_file.path + '_bak')  
    copyfile(file, file + '_bak')
    return srf.SRecordFile(file)

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
        if byte in ASCII:
            detected_string += chr(byte)
        else :
            if len(detected_string) >= min_len:
                print(detected_string)
                detected_string = ""
            else:
                detected_string = ""


#Initializing our sub_func_set that will contains links between functions, their shortcuts and their parsers
sub_func_set = SubFuncSet()

#Populating our SubFuncSet
sub_func_set.addSubFunc(FuncDef(fnc=show_line, sct='sl', prs=show_line_prs))
sub_func_set.addSubFunc(FuncDef(fnc=patch, sct='p', prs=patch_prs))
sub_func_set.addSubFunc(FuncDef(fnc=fix_cks, sct='fc', prs=fix_cks_prs))
sub_func_set.addSubFunc(FuncDef(fnc=apply, sct='a', prs=apply_prs))
sub_func_set.addSubFunc(FuncDef(fnc=patch_by_file, sct='pbf', prs=patch_by_file_prs))
sub_func_set.addSubFunc(FuncDef(fnc=change_working_file, sct='cwf', prs=change_working_file_prs))
sub_func_set.addSubFunc(FuncDef(fnc=strings, sct='s', prs=strings_prs ))

#######################################
# Main function : entry point for SRec 
#######################################

def main():
    #Init_pars get the argv array from the command line.
    #It expects a file given as argument
    init_pars = argparse.ArgumentParser(description="Load a SRecord file to work with")
    init_pars.add_argument('-f', '--file', help='File Name')

    #We use the object ini_pars to parse the command line arguments
    args = init_pars.parse_args()

    #from it we get the "file" argument and use it to open the file
    copyfile(args.file, args.file + '_bak')
    SRec_f = srf.SRecordFile(args.file)

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
            SRec_f.export(SRec_f.path)
            if cmp(SRec_f.path, SRec_f.path + '_bak'):
                os.remove(SRec_f.path + '_bak')

        else:
            print(f"{command} : unknown command.")
            print("Please choose between the following actions :")
            for subF in sub_func_set.parser_dict:
                print(f"\t* {subF} | {sub_func_set.func2shortCut_dict[subF]}")
            print()
            print("For more information about an action : ACTION -h")
            print()
    
if __name__ == '__main__':
    main()
