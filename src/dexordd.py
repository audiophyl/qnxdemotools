#!/usr/bin/env python3
"""
QNX Demodisk Utility

Use to unpack/pack files from/into the QNX demodisk from the 90s.
-i input_file is expected to point to a QNX demodisk image
-w working_dir is the working folder to use for file processing and output.
-m [pack|unpack] is the mode of operation.
"""


__author__ = "Philip Barton"
__version__ = "1.4.5"
__license__ = "MIT"


import pathlib
import argparse
import textwrap
import qnxdd


QNX_DEMODISK_DATA_OFFSET = 0xc00
QNX_DATA_BOOTLOADER_OFFSET = 0x80
QNX_DATA_RAMDISK_OFFSET = 0x2e000
QNX_STAGE_1_2_FILENAME = "boot_stage_1_and_2.bin"
QNX_DECIPHERED_DATA_FILENAME = "deciphered.bin"
QNX_STAGE_3_FILENAME = "boot_stage_3.bin"
QNX_BOOT_RAMDISK_FILENAME = "boot_fs.ramdisk"
QNX_PACK_FILENAME = "qnxdemo_repack.dat"


def pack(working_dir):
    if not working_dir.exists():
        print(f"Working directory doesn't appear to be accessible.")
        quit(1)

    output_file = bytearray()
    recipher = bytearray()
    
    # Begin by adding the 1st and 2nd stage bootloaders directly to the
    # output_file bytearray.
    try:
        with open(working_dir / QNX_STAGE_1_2_FILENAME, "rb") as in_f:
            output_file.extend(bytearray(in_f.read()))
    except Exception as e:
        quit(f"Error adding {QNX_STAGE_1_2_FILENAME}: {e}.")

    # Add the compressed 3rd stage bootloader to the recipher bytearray.
    # This is everything before QNX_DATA_RAMDISK_OFFSET.
    try:
        with open(working_dir / QNX_DECIPHERED_DATA_FILENAME, "rb") as in_f:
            recipher.extend(bytearray(in_f.read(QNX_DATA_RAMDISK_OFFSET)))
    except Exception as e:
        quit(f"Error adding {QNX_DECIPHERED_DATA_FILENAME}: {e}.")

    # Add the boot ramdisk to the recipher bytearray.
    try:
        with open(working_dir / QNX_BOOT_RAMDISK_FILENAME, "rb") as in_f:
            recipher.extend(bytearray(in_f.read()))
    except Exception as e:
        quit(f"Error adding {QNX_BOOT_RAMDISK_FILENAME}: {e}.")

    # Re-cipher the recipher bytearray and add the output to the
    # output_file bytearray.
    output_file.extend(qnxdd.xor_cipher(recipher))

    # Write out the result.
    try:
        with open(working_dir / QNX_PACK_FILENAME, "wb") as out_f:
            out_f.write(output_file)
    except Exception as e:
        quit(f"Error writing {QNX_PACK_FILENAME}: {e}.")


def unpack(demodisk_file, working_dir):
    if not working_dir.exists():
        try:
            working_dir.mkdir()
        except OSError as e:
            print(f"Error creating directory '{working_dir}': {e}")
            quit(1)
    
    if not working_dir.is_dir():
        print(f"Working directory doesn't appear to be accessible.")
        quit(1)
    else:
        input_file = bytearray()

        try:
            with open(demodisk_file, "rb") as in_f:
                with open(working_dir / QNX_STAGE_1_2_FILENAME, "wb") as out_f:
                    out_f.write(in_f.read(QNX_DEMODISK_DATA_OFFSET))
                in_f.seek(QNX_DEMODISK_DATA_OFFSET)
                input_file.extend(bytearray(in_f.read()))
        except Exception as e:
            quit(f"Error writing {QNX_STAGE_1_2_FILENAME}: {e}.")

        # Decipher the disks contents and place them in a new file.
        deciphered = qnxdd.xor_cipher(input_file)
        try:
            with open(working_dir / QNX_DECIPHERED_DATA_FILENAME, "wb") as out_f:
                out_f.write(deciphered)
        except Exception as e:
            quit(f"Error writing {QNX_DECIPHERED_DATA_FILENAME}: {e}.")

        # Decompress the third stage bootloader.
        decompressed = qnxdd.decomp_enigma(deciphered[QNX_DATA_BOOTLOADER_OFFSET:])

        # Dump the third stage bootloader to a separate file.
        try:
            with open(working_dir / QNX_STAGE_3_FILENAME, "wb") as out_f:
                out_f.write(decompressed)
        except Exception as e:
            quit(f"Error writing {QNX_STAGE_3_FILENAME}: {e}.")

        # Dump the ramdisk to a separate file.
        try:
            with open(working_dir / QNX_BOOT_RAMDISK_FILENAME, "wb") as out_f:
                out_f.write(deciphered[QNX_DATA_RAMDISK_OFFSET:])
        except Exception as e:
            quit(f"Error writing {QNX_BOOT_RAMDISK_FILENAME}: {e}.")


def main(args):
    """ Main entry point of the app """
    working_dir = pathlib.Path(args.working_dir[0])

    if args.mode[0] == "unpack":
        input_file = pathlib.Path(args.input_file[0])
        unpack(input_file, working_dir)
    elif args.mode[0] == "pack":
        pack(working_dir)


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
