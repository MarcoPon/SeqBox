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

PROGRAM_VER = "0.5a"

def banner():
    """Display the usual presentation, version, (C) notices, etc."""
    print("\nSeqBox - Sequenced Box container - Encoder v%s" % (PROGRAM_VER),
          " - (C) 2017 by M.Pontello\n")


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="create a SeqBox container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-/+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SBxEncoder v%s' % PROGRAM_VER)
    parser.add_argument("filename", action="store", 
                        help="filename to encode")
    parser.add_argument("sbxfilename", action="store", nargs='?',
                        help="sbx container filename")
    parser.add_argument("-nm","--nometa", action="store_true", default=False,
                        help="exclude matadata block")
    parser.add_argument("-uid", action="store", default="r", type=str,
                        help="use random or custom UID (up to 12 hexdigits)")
    res = parser.parse_args()
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)
      

def getsha256(filename):
    """SHA256 used to verify the integrity of the encoded file"""
    with open(filename, mode='rb') as f:
        d = hashlib.sha256()
        for buf in iter(partial(f.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()


def main():

    banner()
    cmdline = get_cmdline()

    filename = cmdline.filename
    sbxfilename = cmdline.sbxfilename
    if not sbxfilename:
        sbxfilename = filename + ".sbx"

    #parse eventual custom uid
    uid = cmdline.uid
    if uid !="r":
        uid = uid[-12:]
        try:
            uid = int(uid, 16).to_bytes(6, byteorder='big')
        except:
            errexit(1, "invalid UID")

    if not os.path.exists(filename):
        errexit(1, "file '%s' not found" % (filename))
    filesize = os.path.getsize(filename)

    fout = open(sbxfilename, "wb")

    print("hashing file '%s'..." % (filename))
    sha256 = getsha256(filename)

    fin = open(filename, "rb")
    print("encoding file '%s'..." % filename)

    sbx = seqbox.sbxBlock(uid=uid)
    
    #write metadata block 0
    if not cmdline.nometa:
        sbx.metadata = {"filesize":filesize,
                        "filename":os.path.split(filename)[1],
                        "sbxname":os.path.split(sbxfilename)[1],
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
        
    fin.close()
    fout.close()

    totblocks = sbx.blocknum if cmdline.nometa else sbx.blocknum + 1
    sbxfilesize = totblocks * sbx.blocksize
    overhead = 100.0 * sbxfilesize / filesize - 100 if filesize > 0 else 0
    print("\nsbx file size: %i - blocks: %i - overhead: %.1f%%" %
          (sbxfilesize, totblocks, overhead))


if __name__ == '__main__':
    main()
