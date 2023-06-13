# SRecord
Python scripts to deal with Motorola SRecords

---

### /!\ Disclaimer
This is a quick and ugly implementation made by someone who is new to python. It is a project to try things such as OOP, the argparse module etc. If you are looking for something made in python and cleaner, I think the bincopy project might be the way to go.
This being said, if you have any piece of advice, idea of better implementation or new functionnalities that could be implemented, feel free to contact me and contribute :)

---

![Imgur](https://imgur.com/VnhPnq9.gif)

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
