#!/usr/bin/env python3
"""
Utility to remove the "QNX IS COOL" demo from the QNX demodisk XIP file.

This pattern can be modified to remove other entries from the XIP file. The
offsets are as follows:

Pg.vga4flat:
XIP_VGA4FLAT_ENTRY_OFFSET = 0x40
XIP_VGA4FLAT_DATA_OFFSET = 0x1000
XIP_VGA4FLAT_DATA_SIZE = 0x22000

cool:
XIP_COOL_ENTRY_OFFSET = 0x80
XIP_COOL_DATA_OFFSET = 0x23000
XIP_COOL_DATA_SIZE = 0x5000

destaller:
XIP_DESTALLER_ENTRY_OFFSET = 0xc0
XIP_DESTALLER_DATA_OFFSET = 0x28000
XIP_DESTALLER_DATA_SIZE = 0x5000

dhcpc:
XIP_DHCPC_ENTRY_OFFSET = 0x100
XIP_DHCPC_DATA_OFFSET = 0x2d000
XIP_DHCPC_DATA_SIZE = 0x5000

fbrowse:
XIP_FBROWSE_ENTRY_OFFSET = 0x140
XIP_FBROWSE_DATA_OFFSET = 0x32000
XIP_FBROWSE_DATA_SIZE = 0x5000

installer:
XIP_INSTALLER_ENTRY_OFFSET = 0x180
XIP_INSTALLER_DATA_OFFSET = 0x37000
XIP_INSTALLER_DATA_SIZE = 0x9000

netcfg:
XIP_NETCFG_ENTRY_OFFSET = 0x1c0
XIP_NETCFG_DATA_OFFSET = 0x40000
XIP_NETCFG_DATA_SIZE = 0xc000

note:
XIP_NOTE_ENTRY_OFFSET = 0x200
XIP_NOTE_DATA_OFFSET = 0x4c000
XIP_NOTE_DATA_SIZE = 0xe000

phfontphf:
XIP_PHFONTPHF_ENTRY_OFFSET = 0x240
XIP_PHFONTPHF_DATA_OFFSET = 0x5a000
XIP_PHFONTPHF_DATA_SIZE = 0xa000

phgrafx:
XIP_PHGRAFX_ENTRY_OFFSET = 0x280
XIP_PHGRAFX_DATA_OFFSET = 0x64000
XIP_PHGRAFX_DATA_SIZE = 0x8000

pwm:
XIP_PWM_ENTRY_OFFSET = 0x2c0
XIP_PWM_DATA_OFFSET = 0x6c000
XIP_PWM_DATA_SIZE = 0x16000

voyager:
XIP_VOYAGER_ENTRY_OFFSET = 0x300
XIP_VOYAGER_DATA_OFFSET = 0x82000
XIP_VOYAGER_DATA_SIZE = 0x17000

voyager.server:
XIP_VOYAGERSERVER_ENTRY_OFFSET = 0x340
XIP_VOYAGERSERVER_DATA_OFFSET = 0x99000
XIP_VOYAGERSERVER_DATA_SIZE = 0xb2000

-i input_file is expected to point to xip.z
"""


__author__ = "Philip Barton"
__version__ = "1.1.0"
__license__ = "MIT"


import argparse
import textwrap
import qnxdd


XIP_ENTRY_SIZE = 0x40
XIP_COOL_ENTRY_OFFSET = 0x80
XIP_COOL_DATA_OFFSET = 0x23000
XIP_COOL_DATA_SIZE = 0x5000


def zeroes(in_size):
    return [0] * in_size


def main(args):
    """ Main entry point of the app """
    try:
        with open(args.input_file[0], "rb") as in_f:
            xip_file = in_f.read()
    except Exception as e:
        quit(f"Couldn't read xip.z. Error: {e}.")

    xip_file = bytearray(qnxdd.qunzip(xip_file))

    xip_file[XIP_COOL_ENTRY_OFFSET:XIP_COOL_ENTRY_OFFSET + XIP_ENTRY_SIZE] = zeroes(XIP_ENTRY_SIZE)

    xip_file[XIP_COOL_DATA_OFFSET:XIP_COOL_DATA_OFFSET + XIP_COOL_DATA_SIZE] = zeroes(XIP_COOL_DATA_SIZE)

    xip_file = qnxdd.qzip(xip_file)

    try:
        with open(args.input_file[0], "wb") as out_f:
            out_f.write(xip_file)
    except Exception as e:
        quit(f"Couldn't write xip.z. Error: {e}.")


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                description=textwrap.dedent('''\
        XIP Cleaner
        -------------------
        Use to remove the 'cool' demo from the QNX demodisk.'''))
    parser.add_argument('-i', '--input', dest='input_file', metavar='input_file',
                        nargs=1, type=str, help='QNX XIP image filename.', required=True)
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    main(parser.parse_args())
