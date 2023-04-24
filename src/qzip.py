#!/usr/bin/env python3
"""
QZip Compression/Decompression Utility

Use to compress/decompress files from the QNX demodisk from the 90s.

QZip files are BZip2 compressed files with a slightly modified header.

QNXDE file are XOR ciphered QZip files.

Command line flags:
-i input_file is expected to point to a QZip compressed file.
-w working_dir is the working folder to use for file processing and output.
"""


__author__ = "Philip Barton"
__version__ = "1.1.0"
__license__ = "MIT"


import argparse
import textwrap
import qnxdd


def main(args):
    input_file = args.input_file[0].split(".")

    try:
        with open(args.input_file[0], "rb") as in_f:
            input_data = in_f.read()
    except Exception as e:
        quit(f"Could not read input file. Error: {e}")

    match input_file[1]:
        case "z":
            output_file = input_file[0] + ".ramdisk"
            output_data = qnxdd.qunzip(input_data)
        case "qnxde":
            output_file = input_file[0] + ".ramdisk"
            output_data = qnxdd.xor_cipher(input_data)
        case "ramdisk":
            if args.is_extension:
                output_file = input_file[0] + ".qnxde"
                output_data = qnxdd.xor_cipher(qnxdd.qzip(input_data))
            else:
                output_file = input_file[0] + ".z"
                output_data = qnxdd.qzip(input_data)
        case _:
            quit(f"Not a valid QZip file.")

    if not output_data:
        quit("Invalid input file.")

    try:
        with open(output_file, "wb") as out_f:
            out_f.write(output_data)
    except Exception as e:
        quit(f"Could not write output file. Error: {e}")


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                description=textwrap.dedent('''\
        QNX QZip Utility
        -------------------
        Use to compress/decompress QNX demodisk ramdisks or QNXDE files.'''))
    parser.add_argument('-i', '--input', dest='input_file', metavar='input_file',
                        nargs=1, type=str, help='QZip compressed file.', required=True)
    parser.add_argument('-e', '--extension', dest='is_extension', action='store_true',
                        help='Compress as QNXDE file.', required=False)
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    main(parser.parse_args())