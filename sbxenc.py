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

def getsha256(filename):
    with open(filename, mode='rb') as f:
        d = hashlib.sha256()
        for buf in iter(partial(f.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()

def banner():
    print("\nSeqBox - Sequenced Box Container v%s - (C) 2017 Marco Pontello\n"
           % (PROGRAM_VER))

def usage():
    print("""usage:

seqbox <file> [file.sbx] encode file in file.sbx
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
        res["file"] = sys.argv[1]
        res["sbxfile"] = res["file"] + ".sbx"
    if len(sys.argv) > 2:
        res["sbxfile"] = sys.argv[2]
    if len(sys.argv) > 3:
        usage()
        errexit(1)

    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)
      

def main():

    banner()

    cmdline = getcmdargs()

    filename = cmdline["file"]
    sbxfilename = cmdline["sbxfile"]

    print("reading %s..." % filename)
    filesize = os.path.getsize(filename)
    sha256 = getsha256(filename)
    fin = open(filename, "rb")
    fout = open(sbxfilename, "wb")

    sbx = seqbox.sbxBlock(uid=b'uiduid')
    
    #write block 0
    sbx.metadata = {"filesize":filesize,
                    "filename":filename,
                    "sbxname":sbxfilename,
                    "hash":sha256}
    fout.write(sbx.encode())
    
    #write all other blocks
    while True:
        buffer = fin.read(sbx.datasize)
        if len(buffer) < sbx.datasize:
            if len(buffer) == 0:
                break
        sbx.blocknum += 1
        sbx.data = buffer
        #print(fin.tell(), sbx.blocknum, " ",end = "\r")
        fout.write(sbx.encode())
                
        
    fout.close()
    fin.close()

    print("\nok!")


if __name__ == '__main__':
    main()
