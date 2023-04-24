#!/usr/bin/env bash

set -o errexit
trap cleanup EXIT

PROJECT_ROOT="$(dirname -- "$(readlink -f "${BASH_SOURCE[0]}")")"
SRC_DIR="${PROJECT_ROOT}/src"
BUILD_DIR="${PROJECT_ROOT}/build"
TMP_DIR=$(mktemp -d)

cleanup() {
    last_command=$BASH_COMMAND
    exit_code=$?
    if [ $exit_code -gt 0 ]
    then
        echo "\"${last_command}\" exited with code $exit_code."
    fi
    cd "${PROJECT_ROOT}"
    echo "Tidying up..."
    rm -rf "${TMP_DIR}"
}

echo "Unzipping demo_mod_files.zip..."
unzip "${SRC_DIR}/demo_mod_files.zip" -d "${TMP_DIR}"

echo "Changing to ${TMP_DIR} to operate..."
cd "${TMP_DIR}"

echo "Unpacking QNX Demodisk v4.05 parts..."
"${SRC_DIR}/dexordd.py" -i qnxdemo.dat -w "${TMP_DIR}" -m unpack

echo "Dumping qzip files from BASE ramdisk..."
"${SRC_DIR}/qnxddcli.py" -i "${TMP_DIR}/boot_fs.ramdisk" -s s_00

echo "Decompressing ramdisks..."
"${SRC_DIR}/qzip.py" -i image1.z
rm image1.z
"${SRC_DIR}/qzip.py" -i image2.z
rm image2.z

echo "Removing pesky bits from image1.ramdisk..."
"${SRC_DIR}/qnxddcli.py" -i image1.ramdisk -s s_01

echo "Removing pesky bits from xip.ramdisk..."
"${SRC_DIR}/decool.py" -i xip.z

echo "Performing magic edit on image2.ramdisk..."
"${SRC_DIR}/qnxddcli.py" -i image2.ramdisk -s s_02

echo "Compressing ramdisks..."
"${SRC_DIR}/qzip.py" -i image1.ramdisk
"${SRC_DIR}/qzip.py" -i image2.ramdisk

echo "Preparing boot_fs.ramdisk..."
"${SRC_DIR}/qnxddcli.py" -i "${TMP_DIR}/boot_fs.ramdisk" -s s_03

echo "Repacking QNX Demodisk v4.05 parts..."
"${SRC_DIR}/dexordd.py" -i qnxdemo.dat -w "${TMP_DIR}" -m pack

mkdir -p "${BUILD_DIR}"
mv "${TMP_DIR}/qnxdemo_repack.dat" "${BUILD_DIR}"
