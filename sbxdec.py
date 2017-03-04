#!/usr/bin/env python3

#--------------------------------------------------------------------------
# Name:        seqbox.py
# Purpose:     Sequenced Box container
#
# Author:      Marco Pontello
#
# Created:     10/02/2017
# Copyright:   (c) Mark 2017
# Licence:     GPL-something?
#--------------------------------------------------------------------------

import os
import sys
import hashlib
import argparse
import tempfile
import binascii
import random
from functools import partial

import seqbox

PROGRAM_VER = "0.04a"


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="Sequenced Box container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-/+')
    parser.add_argument('--version', action='version',
                        version='Sequenced Box container v%s' % PROGRAM_VER)
    parser.add_argument("filename", action="store", nargs='?',
                        help = "filename.", default="")
    res = parser.parse_args()
    return res

def banner():
    print("\nSBxDec - Sequenced Box Decoder v%s - (C) 2017 Marco Pontello\n"
           % (PROGRAM_VER))

def usage():
    print("""usage:

sbxdec <file.sbx> [file] decode file from file.sbx
sbxdec -i <file.sbx> show information on file.sbx
sbxdec -t <file.sbx> test file.sbx for integrity
    """)

def getcmdargs():
    res = {}
    if len(sys.argv) == 1:
        usage()
        errexit(1)
    elif sys.argv[1] in ["?", "-?", "-h", "--help"]:
        usage()
        errexit(0)

    if len(sys.argv) > 1:
        res["sbxfile"] = sys.argv[1]
        res["file"] = res["sbxfile"] + ".out"
    if len(sys.argv) > 2:
        print("OK")
        res["file"] = sys.argv[2]
    if len(sys.argv) > 3:
        usage()
        errexit(1)
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)

def getsha256(filename):
    with open(filename, mode='rb') as f:
        d = hashlib.sha256()
        for buf in iter(partial(f.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()


def main():

    banner()
    cmdline = getcmdargs()

    print("\nDecoding...")

    sbxfilename = cmdline["sbxfile"]
    filename = cmdline["file"]

    print(sbxfilename, "->", filename)

    fin = open(sbxfilename, "rb")
    fout= open(filename, "wb")

    sbx = seqbox.sbxBlock()
    lastblocknum = 0
    d = hashlib.sha256()
    trimfilesize = False
    filesize = 0
    while True:
        buffer = fin.read(sbx.blocksize)
        if len(buffer) < sbx.blocksize:
            break
        if not sbx.decode(buffer):
            errexit(errlev=1, mess="Invalid block.")
        else:
            print("Block #",sbx.blocknum)
            if sbx.blocknum == 0:
                #get metadata
                metadata = sbx.metadata
                if sbx.metadata["filesize"]:
                    trimfilesize = True
            else:
                #optimize size checking!
                if trimfilesize:
                    filesize += sbx.datasize
                    if filesize > sbx.metadata["filesize"]:
                        sbx.data = sbx.data[:-(filesize - sbx.metadata["filesize"])]
                fout.write(sbx.data)
                d.update(sbx.data)
    
    fout.close()
    fin.close()

    print("File decoded.")
    print(d.hexdigest())
    if d.digest() ==  metadata["hash"]:
        print("Hash match!")
    else:
        errexit(1, "Hash mismatch! Decoded file corrupted!")

if __name__ == '__main__':
    main()
