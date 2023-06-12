# SRecord
Python scripts to deal with Motorola SRecords

# Usage
```py SRec_main.py -f <srecord_file_name>```

Once the file is loaded, you have a prompt with a few options available to manipulate the SRecords of the file.

### show_line

Needs an adress (hex format) to display the SRecord that contains it.
Optional argument : nb_lines (-nl) - number of SRecord to print

### patch

Expect 2 arguments : address (hex format), and value (hex format)
The SRecord containing the address given will be updated (value and checksum)

### fix_cks

No arguments. Will fix the checksums of every SRecord

### apply

No arguments. Will write the modified file, making the changes done untill now "permanent"

### patch_by_file

Expects 2 arguments : address (hex format) and patching_file (SRecordFile).
Replace the SRecords from present file with those from the patching_file, starting at address

### change_working_file

Expects one argument : a file path
The current file is saved and the new one is loaded so you can work on it

### strings

One optional argument : min_len. Integer, lenght minimal to detect a string
This function will parse the SRecords looking for ASCII sequence. By default it looks for strings of 3 char minimum.
