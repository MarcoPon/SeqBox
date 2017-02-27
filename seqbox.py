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

PROGRAM_VER = "0.02a"

def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)



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

def banner():
    print("\nSeqBox - Sequenced Box Container v%s - (C) 2017 Marco Pontello\n"
           % (PROGRAM_VER))

def usage():
    print("""usage:

seqbox e file.sbx file encode file in file.sbx
seqbox d file.sbx file decode file from file.sbx
seqbox i file.sbx show information on file.sbx
seqbox t file.sbx test file.sbx for integrity
seqbox r [-d path] filenames [filenames ...] recover sbx files from filenames
         and store in path
    """)

def getcmdargs():
    res = {}

    if len(sys.argv) == 1:
        usage()
        errexit(1)
    elif sys.argv[1] in ["?", "-?", "-h", "--help"]:
        usage()
        errexit(0)

    res["cmd"] = sys.argv[1].lower()

    if res["cmd"] in ["e"]:
        if len(sys.argv) == 4:
            res["sbxfile"] = sys.argv[2]
            res["file"] = sys.argv[3]
        else:
            usage()
            errexit(1)
    else:
        errexit(1, "command %s not yet implemented." % res["cmd"])
    
    return res


class sbxBlock():
    """
    Implement a basic SBX block
    """
    def __init__(self, ver):
        self.ver = ver
        if ver in [0,1]:
            self.blocksize = 512
            self.hdrsize = 16
        self.reset()
    def __str__(self):
        return "SBX Block ver: '%i', size: %i, hdr size: %i" % \
               (self.ver, self.blocksize, self.hdrsize)

    def reset(self):
        self.buffer = ""



def main():
    sbxblocksize = 512
    sbxhdrsize = 16

    banner()

    cmdline = getcmdargs()

    filename = cmdline["file"]
    sbxfilename = cmdline["sbxfile"]
    
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
            #padding the last block
            buffer += b'\x1A' * (chunksize - len(buffer)) 
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
