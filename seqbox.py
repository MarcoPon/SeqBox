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

PROGRAM_VER = "0.01a"


def errexit(mess, errlev=1):
    """Display an error and exit."""
    print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)


def chunked(file, chunk_size):
    """Helper function to read files in chunks."""
    return iter(lambda: file.read(chunk_size), '')


def MD5digest(filename=None, data=None):
    """Return an MD5 digest for a file or a string."""
    h = hashlib.md5()
    if filename:
        f = open(filename, "rb")
        for data in chunked(f, 1024*1024):
            h.update(data)
        f.close()
    elif data:
        h.update(data)
    return h.hexdigest()


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


def main():
    sbxblocksize = 512
    sbxhdrsize = 16

    filename = "trid_linux_64.zip"
    sbxfilename = "test.sbx"
    
    sbxmagic = b'SBx'
    sbxver = b'\x00' # for prototyping
    sbxhdr = sbxmagic + sbxver

    random.seed()
    sbxuid = random.getrandbits(32).to_bytes(4, byteorder='little') # temporary
    sbxhdr += sbxuid
    sbxflags = b'\x00\x00'

    chunksize = sbxblocksize - sbxhdrsize

    print("reading %s..." % filename)
    filesize = os.path.getsize(filename)
    sha256 = getsha256(filename)
    fin = open(filename, "rb")
    fout = open(sbxfilename, "wb")

    blocks = 0
    #write block 0 / header

    parent_uid = 0
    buffer = parent_uid.to_bytes(4, byteorder='little')
    buffer += filesize.to_bytes(8, byteorder='little')
    buffer += (bytes(filename, "utf-8")+b"\x00"*255)[:255]
    buffer += sha256
    buffer += b'\x1A' * (chunksize - len(buffer)) # padding

    crc = binascii.crc_hqx(buffer,0)
    
    blockhdr = (sbxhdr + crc.to_bytes(2,byteorder='little') +
                blocks.to_bytes(4, byteorder='little') +
                sbxflags)
    fout.write(blockhdr+buffer)

    
    #write all other blocks
    while True:
        buffer = fin.read(chunksize)
        if len(buffer) < chunksize:
            if len(buffer) == 0:
                break
            buffer += b'\x1A' * (chunksize - len(buffer)) # padding the last block
        blocks += 1
        #print(fin.tell(), " ",end = "\r")

        crc = binascii.crc_hqx(buffer,0)
        
        blockhdr = (sbxhdr + crc.to_bytes(2,byteorder='little') +
                    blocks.to_bytes(4, byteorder='little') +
                    sbxflags)
        fout.write(blockhdr+buffer)
                
        
    fout.close()
    fin.close()


    print("\nok!")


if __name__ == '__main__':
    main()
