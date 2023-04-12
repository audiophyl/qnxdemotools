#!/usr/bin/env bash

set -o errexit
trap cleanup EXIT

WORKING_DIR=$(mktemp -d)

cleanup() {
    last_command=$BASH_COMMAND
    exit_code=$?
    if [ $exit_code -gt 0 ]
    then
        echo "\"${last_command}\" exited with code $exit_code."
    fi
    echo "Tidying up..."
    rm Dev
    rm Dev.pty
    rm pterm
    rm ksh
    rm index.html
    rm pwm.menu
    rm s_00
    rm s_01
    rm s_02
    rm s_03
    rm qnxdemo.dat
    rm image1.z
    rm xip.z
    rm image2.z
    rm -rf "${WORKING_DIR}"
}

echo "Unzipping demo_mod_files.zip..."
unzip demo_mod_files.zip

echo "Unpacking QNX Demodisk v4.05 parts..."
./dexordd.py -i qnxdemo.dat -w "${WORKING_DIR}" -m unpack

echo "Dumping qzip files from BASE ramdisk..."
./qnxddcli.py -i "${WORKING_DIR}/boot_fs.ramdisk" -s s_00

echo "Decompressing ramdisks..."
./qzip.py -i image1.z
rm image1.z
./qzip.py -i image2.z
rm image2.z

echo "Removing pesky bits from image1.ramdisk..."
./qnxddcli.py -i image1.ramdisk -s s_01

echo "Removing pesky bits from xip.ramdisk..."
./decool.py -i xip.z

echo "Performing magic edit on image2.ramdisk..."
./qnxddcli.py -i image2.ramdisk -s s_02

echo "Compressing ramdisks..."
./qzip.py -i image1.ramdisk
rm image1.ramdisk
./qzip.py -i image2.ramdisk
rm image2.ramdisk

echo "Preparing boot_fs.ramdisk..."
./qnxddcli.py -i "${WORKING_DIR}/boot_fs.ramdisk" -s s_03

echo "Repacking QNX Demodisk v4.05 parts..."
./dexordd.py -i qnxdemo.dat -w "${WORKING_DIR}" -m pack

mv "${WORKING_DIR}/qnxdemo_repack.dat" ./
