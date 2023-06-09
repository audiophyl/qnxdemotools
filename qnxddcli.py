#!/usr/bin/env python3
""" Manipulate ramdisks of the format used by the QNX Demodisk.

    Provides a minimal command line interface with ability to run scripts in order
    to manipulate the ramdisk files present in the QNX Demodisk v4.05.

    Typical usage examples:

    qnxddcli.py -i working/base_fs.ramdisk -s script_file
"""

__author__ = "Philip Barton"
__version__ = "1.5.0"
__license__ = "MIT"

MIN_PYTHON = (3, 10)    # This code makes use of match/case, so Python 3.10+


import argparse
import textwrap
import sys
from qnxdd import Ramdisk


def script_buffer(in_file):
    try:
        with open(in_file, "r") as in_f:
            while True:
                line = in_f.readline()
                if len(line) == 0:
                    break
                else:
                    yield line.strip()
    except Exception as e:
        print(f"Error while reading script: {e}")
        quit(1)


def main(args):
    """ Prep for CLI loop """
    try:
        ramdisk = Ramdisk(args.input_file[0])
    except Exception as e:
        quit(f"Error: {e}.")

    script = None
    script_fault = False

    if args.script_file:
        script = script_buffer(args.script_file[0])
        command = next(script)
    else:
        command = "welcome"

    """ CLI loop """
    while command != "exit":
        command = command.split("#")[0]
        command = command.split(" ")

        match command[0]:
            case "ls":
                ramdisk.ls()

            case "dump":
                if len(command) == 1:
                    print(f"Usage:\n\t'dump <filename>'")
                else:
                    print(f"Attempting to dump '{command[1]}'...")
                    if not ramdisk.dump(command[1]):
                        print(f"Unable to dump {command[1]}.")
                        script_fault = True if script else False
            
            case "cd":
                if len(command) == 1:
                    print(f"Usage:\n\t'cd <directory>'\n\t'cd .'\n\t'cd ..'\n\t'cd /'")
                else:
                    if not ramdisk.cd(command[1]):
                        print(f"Invalid directory.")
                        script_fault = True if script else False

            case "info":
                ramdisk.info()
            
            case "rm":
                if len(command) == 1:
                    print(f"Usage:\n\t'rm <filename>'")
                else:
                    if not ramdisk.rm(command[1]):
                        print(f"Invalid file {command[1]}.")
                        script_fault = True if script else False
            
            case "rmdir":
                if len(command) == 1:
                    print(f"Usage:\n\t'rmdir <dirname>'")
                else:
                    if not ramdisk.rmdir(command[1]):
                        print(f"Couldn't delete directory {command[1]}.")
                        script_fault = True if script else False

            case "inject":
                if len(command) == 1:
                    print(f"Usage:\n\t'inject <filename>")
                else:
                    if not ramdisk.inject(command[1]):
                        print(f"Error injecting file {command[1]}.")
                        script_fault = True if script else False

            case "flags":
                if len(command) < 3:
                    print(f"Usage:\n\t'flags <filename> <flag_string>'")
                else:
                    if not ramdisk.flags(command[1], command[2]):
                        print(f"Error setting flags for {command[1]}.")
                        script_fault = True if script else False

            case "commit":
                ramdisk.commit(args.input_file[0])
            
            case "pwd":
                print(f"{ramdisk.pwd()}")

            case "showfat":
                if len(command) == 1:
                    print(f"Usage:\n\t'showfat <entry_name>'")
                else:
                    entry = ramdisk.showfat(command[1])
                    if entry:
                        print(f"'{command[1]}': {entry}")
                    else:
                        print(f"No entry '{command[1]}'.")
                        script_fault = True if script else False

            case "listfree":
                print(f"Free sectors: {ramdisk.listfree()}")

            case "welcome":
                print(f"QNX Ramdisk Terminal")
                print(f"Type 'help' for list of available commands.")

            case "help":
                print(f"{'ls:' : <9}List directory contents.")
                print(f"{'cd:' : <9}Change directory.")
                print(f"{'rm:' : <9}Remove a file.")
                print(f"{'rmdir:' : <9}Remove a directory.")
                print(f"{'dump:' : <9}Dump a single file's contents.")
                print(f"{'inject:' : <9}Inject a file into the ramdisk.")
                print(f"{'flags:' : <9}Set the flags on a file or dir.")
                print(f"{'commit:' : <9}Write ramdisk to output file.")
                print(f"{'info:' : <9}Print ramdisk information.")
                print(f"{'showfat:' : <9}Print the FAT entry for the specified file/dir/link.")
                print(f"{'help:' : <9}Display this information.")
                print(f"{'exit:' : <9}Exit the utility.")

            case _:
                if not (len(command) == 1 and command[0] == ""):
                    print(f"Invalid command.")
                    script_fault = True if script else False

        if script_fault:
            quit(f"Aborted: there was an error executing the provided script.")

        command = next(script) if script else input(f"ramdisk:{ramdisk.pwd()}$ ")

    print(f"Errors were avoided.")
    quit(0)


if __name__ == "__main__":
    """ This is executed when run from the command line """

    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                description=textwrap.dedent('''\
        QNX Ramdisk Utility
        -------------------
        Supports a limited number of commands.'''))
    parser.add_argument('-i', '--input', dest='input_file', metavar='input_file',
                        nargs=1, type=str, help='Input filename.', required=True)
    parser.add_argument('-s', '--script', dest='script_file', metavar='script_file',
                        nargs=1, type=str, help='Script filename (text).', required=False)
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    
    main(parser.parse_args())
