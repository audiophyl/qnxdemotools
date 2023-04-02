#!/usr/bin/env python3
"""
QNX Demodisk Utility

Use to unpack/pack files from/into the QNX demodisk from the 90s.
-i input_file is expected to point to a file either containing the cipher or to be ciphered.
-w working_dir is the working folder to use for file processing and output.
-m [pack|unpack] is the mode of operation.
"""


__author__ = "Philip Barton"
__version__ = "1.2.0"
__license__ = "MIT"


import os
import argparse
import textwrap
import qnxdd


QNX_DEMODISK_DATA_OFFSET = 0xc00
QNX_DATA_BOOTLOADER_OFFSET = 0x80
QNX_DATA_RAMDISK_OFFSET = 0x2e000
QNX_PACK_FILENAME = "/qnxdemo_repack.dat"


def main(args):
    """ Main entry point of the app """
    if args.mode[0] == "unpack":
        try:
            os.mkdir(args.working_dir[0], 0o755)
        except OSError as e:
            print(f"Error creating directory '{args.working_dir[0]}':")
            print(f"{e}")
        
        if os.path.isdir(args.working_dir[0]):
            input_file = bytearray()

            try:
                with open(args.input_file[0], "rb") as in_f:
                    with open(args.working_dir[0] + "/boot_stage_1_and_2.bin", "wb") as out_f:
                        out_f.write(in_f.read(QNX_DEMODISK_DATA_OFFSET))
                    in_f.seek(QNX_DEMODISK_DATA_OFFSET)
                    input_file.extend(bytearray(in_f.read()))
            except Exception as e:
                quit(f"Couldn't output boot_stage_1_and_2.bin. Error: {e}.")

            # Decipher the disks contents and place them in a new file.
            deciphered = qnxdd.xor_cipher(input_file)
            try:
                with open(args.working_dir[0] + "/deciphered.bin", "wb") as out_f:
                    out_f.write(deciphered)
            except Exception as e:
                quit(f"Couldn't output deciphered.bin. Error: {e}.")

            # Decompress the third stage bootloader.
            decompressed = qnxdd.decomp_enigma(args.working_dir[0] + "/deciphered.bin",
                                QNX_DATA_BOOTLOADER_OFFSET)
            try:
                with open(args.working_dir[0] + "/boot_stage_3.bin", "wb") as out_f:
                    out_f.write(decompressed)
            except Exception as e:
                quit(f"Couldn't output boot_stage_3.bin. Error: {e}.")

            # Dump the ramdisk to a separate file.
            try:
                with open(args.working_dir[0] + "/deciphered.bin", "rb") as in_f:
                    with open(args.working_dir[0] + "/boot_fs.ramdisk", "wb") as out_f:
                        in_f.seek(QNX_DATA_RAMDISK_OFFSET)
                        out_f.write(in_f.read())
            except Exception as e:
                quit(f"Couldn't output boot_fs.ramdisk. Error: {e}.")
        else:
            print(f"Working directory doesn't appear to be accessible.")
    elif args.mode[0] == "pack":
        output_file = bytearray()
        recipher = bytearray()
        
        try:
            with open(args.working_dir[0] + "/boot_stage_1_and_2.bin", "rb") as in_f:
                output_file.extend(bytearray(in_f.read()))
        except Exception as e:
            quit(f"Error adding boot_state_1_and_2.bin. Error: {e}.")
            
        try:
            with open(args.working_dir[0] + "/deciphered.bin", "rb") as in_f:
                recipher.extend(bytearray(in_f.read(QNX_DATA_RAMDISK_OFFSET)))
        except Exception as e:
            quit(f"Error adding deciphered.bin. Error: {e}.")

        try:
            with open(args.working_dir[0] + "/boot_fs.ramdisk", "rb") as in_f:
                recipher.extend(bytearray(in_f.read()))
        except Exception as e:
            quit(f"Error adding boot_fs.ramdisk. Error: {e}.")

        output_file.extend(qnxdd.xor_cipher(recipher))

        try:
            with open(args.working_dir[0] + QNX_PACK_FILENAME, "wb") as out_f:
                out_f.write(output_file)
        except Exception as e:
            quit(f"Error writing {QNX_PACK_FILENAME}. Error: {e}.")


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                description=textwrap.dedent('''\
        QNX Demodisk Utility
        -------------------
        Use to reverse the XOR cipher used on the QNX demodisk.'''))
    parser.add_argument('-i', '--input', dest='input_file', metavar='input_file',
                        nargs=1, type=str, help='QNX demodisk image filename.', required=True)
    parser.add_argument('-w', '--dir', dest='working_dir', metavar='working_dir',
                        nargs=1, type=str, help='Working directory.', required=True)
    parser.add_argument('-m', '--mode', dest='mode', metavar='[pack|unpack]', choices=['pack', 'unpack'],
                        nargs=1, type=str, help='Mode: [pack|unpack].', required=True)
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    main(parser.parse_args())
