# qnxdemotools
Tools to manipulate the 90s QNX Demodisk.

## What?
Admittedly, the target audience is extremely limited and possibly non-existent.

This set of tools allows a user to modify the ramdisk images contained within the QNX v4.05 Demodisk published in the late 90s, enabling additions/removals of binaries and data. It was a fascinating challenge:

1. Reverse the bootloader
2. Sort out the XOR cipher obfuscating both the demodisk and the QNXDE files used to extend it
3. Re-implement an unknown decompression algorithm (from i386 assembly to Python!)
4. Sort out the ramdisk format and write a utility to enable RW access
5. Dig into the XIP ramdisk format to remove unwanted data
6. Sort out what makes a QNXDE file special to the demodisk

If you'd like to know more about the QNX Demodisk, [OpenQNX](https://openqnx.com) has a [decent write-up](https://openqnx.com/node/259), and the image files are archived [at WinWorld.com](https://winworldpc.com/product/qnx/144mb-demo).

The best way to run the demo today is via QEMU, which implements one of the three supported network adapters (DEC's "tulip" chipset). VMWare does not implement any of the three supported network adapters (tulip, 3c509, or ne2k). Here is a one-liner for Linux users to use for QEMU:

```
qemu-system-i386 -device tulip -drive format=raw,if=floppy,file=qnxdemo.dat
```

## Okay... What??
I'm glad you asked! Here are the important things to know:

### dexordd.py
This program is used to de-XOR the demodisk. De-XOR the DD, get it? It is invoked like this:

```
./dexordd.py -i qnxdemo.dat -w working_dir -m unpack
```

Running dexordd.py like this will split qnxdemo.dat into its constituent parts, decipher and/or decompress them as needed, and write them to the working directory "working_dir".

But let's say you've already done this and would like to repack your edited files... Well, invoke dexordd.py like this:

```
./dexordd.py -i destination_file.dat -w working_dir -m pack
```
This will use the files in working_dir to make a new image having the name destination_file.dat.

### qzip.py
This program is used to compress/decompress QNX's ".z", ramdisk, and QNXDE files. It is invoked like this:

```
./qzip.py -i filename.ext
```

It will do the right thing based on the filename extension. If the extension is ".z", it will decompress. If it's ".qnxde", it will de-XOR and decompress. If it's a ramdisk, it will compress. If it's a ramdisk and you use the super-special --extension flag, it will compress and re-apply the XOR cipher. The output file will always have the correct extension, and your input file will be preserved.

### decool.py
This program is used to remove the "QNX IS COOL" demo from the xip.z file on the demodisk. Included in the comments within the file are offsets and other important information for removing other executables contained within the XIP. It is invoked like this:

```
./decool.py -i filename.ext
```

It really only makes sense for the input file to be 'xip.z'. Be aware that, just like your favorite naughty puppy, this utility will gladly mangle any file handed to it.

### qnxddcli.py
This program is an interactive shell for working with a QNX Demodisk ramdisk. It is invoked like this:

```
./qnxddcli.py -i image.ramdisk [-s script_file] 
```

Once running, commands can be issued to directly manipulate the contents of the ramdisk. Those commands are accessible through the command "help" in the CLI.

The optional script file can be used to automatically process through a series of commands. Example scripts are contained within demo_mod_files.zip.

### qnxdd.py
This module is the bulk of the code. It contains the Ramdisk and Entry class definitions, as well as the implementation for the XOR cipher and the mysterious decompression algorithm from the second stage bootloader.

## Ahh... What???
If, like me, you're using Linux, you can simply clone this repository and run ./make_mod.sh. I encourage you to read the (brief) shell file, but here's a summary of what it does:

1. Unzip demo_mod_files.zip to ./
2. Unpack qnxdemo.dat to ./working/
3. Dump the compressed images from the boot ramdisk to ./
4. Decompress the compressed images to ./
5. Remove extraneous network drivers from image1.ramdisk
6. Remove "QNX IS COOL" demo from xip.z
7. Remove extraneous serial driver and HTML files from image2.ramdisk, inject files necessary for running KSH, and inject a new pwm.menu
8. Compress the ramdisk files in ./
9. Inject the edited files back into the boot ramdisk in ./working/
10. Repack the demodisk as "qnxdemo_repack.dat"
11. Tidy up all the files we'd strewn all about

It's just that simple!

## Alright, I understand all of that, but... What????
Amazing, right? It's been a load of fun, and I've learned a lot. I'm not done, either! There's still much I don't understand about the demodisk, and much I'd still like to try out. If you feel compelled to contact me, [audiophyl@gmail.com](mailto:audiophyl@gmail.com) is best.
