#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBxDec - Sequenced Box container Decoder
#
# Created: 03/03/2017
#
# Copyright (C) 2017 Marco Pontello - http://mark0.net/
#
# Licence:
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#--------------------------------------------------------------------------

import os
import sys
import hashlib
import argparse
import binascii
from functools import partial
from time import time

import seqbox

PROGRAM_VER = "0.7.0b"


def banner():
    """Display the usual presentation, version, (C) notices, etc."""
    print("\nSeqBox - Sequenced Box container - Decoder v%s" % (PROGRAM_VER),
          " - (C) 2017 by M.Pontello\n")


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="decode a SeqBox container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SBxDecoder v%s' % PROGRAM_VER)
    parser.add_argument("sbxfilename", action="store", help="SBx container")
    parser.add_argument("filename", action="store", nargs='?', 
                        help="target/decoded file")
    parser.add_argument("-t","--test", action="store_true", default=False,
                        help="test container integrity")
    parser.add_argument("-i", "--info", action="store_true", default=False,
                        help="show informations/metadata")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
    res = parser.parse_args()
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)


def getsha256(filename):
    with open(filename, mode='rb') as fin:
        d = hashlib.sha256()
        for buf in iter(partial(fin.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()


def lastEofCount(data):
    count = 0
    for b in range(len(data)):
        if data[-b-1] != 0x1a:
            break
        count +=1
    return count


def main():

    banner()
    cmdline = get_cmdline()

    sbxfilename = cmdline.sbxfilename
    filename = cmdline.filename

    if not os.path.exists(sbxfilename):
        errexit(1, "sbx file '%s' not found" % (sbxfilename))
    sbxfilesize = os.path.getsize(sbxfilename)

    print("decoding '%s'..." % (sbxfilename))
    fin = open(sbxfilename, "rb", buffering=1024*1024)

    #check magic and get version
    if fin.read(3) != b"SBx":
        errexit(1, "not a SeqBox file!")
    sbxver = ord(fin.read(1))
    fin.seek(0, 0)
    
    sbx = seqbox.sbxBlock(ver=sbxver)
    metadata = {}
    metadatafound = False
    trimfilesize = False

    buffer = fin.read(sbx.blocksize)
    if not sbx.decode(buffer):
        errexit(errlev=1, mess="invalid block at offset 0x0")
    if sbx.blocknum > 1:
        errexit(errlev=1, mess="blocks missing or out of order at offset 0x0")
    elif sbx.blocknum == 0:
        print("metadata block found!")
        metadatafound = True
        metadata = sbx.metadata
        trimfilesize = True
    else:
        #first block is data, so reset from the start
        print("no metadata available")
        fin.seek(0, 0)

    #display some info and stop
    if cmdline.info:
        print("\nSeqBox container info:")
        print("  file size: %i bytes" % (sbxfilesize))
        print("  blocks: %i" % (sbxfilesize / sbx.blocksize))
        print("  version: %i" % (sbx.ver))
        print("  UID: %s" % (binascii.hexlify(sbx.uid).decode()))
        if metadatafound:
            print("metadata:")
            print("  SBx name : '%s'" % (metadata["sbxname"]))
            print("  file name: '%s'" % (metadata["filename"]))
            print("  file size: %i bytes" % (metadata["filesize"]))
            print("  SHA256: %s" % (binascii.hexlify(metadata["hash"]
                                                   ).decode()))
        sys.exit(0)

    #evaluate target filename
    if not cmdline.test:
        if not filename:
            if "filename" in metadata:
                filename = metadata["filename"]
            else:
                filename = sbxfilename + ".out"
        elif os.path.isdir(filename):
            if "filename" in metadata:
                filename = os.path.join(filename, metadata["filename"])
            else:
                filename = os.path.join(filename,
                                        os.path.split(sbxfilename)[1] + ".out")

        if os.path.exists(filename) and not cmdline.overwrite:
            errexit(1, "target file '%s' already exists!" % (filename)) 
        print("creating file '%s'..." % (filename))
        fout= open(filename, "wb", buffering=1024*1024)

    lastblocknum = 0
    d = hashlib.sha256()
    filesize = 0
    updatetime = time() 
    while True:
        buffer = fin.read(sbx.blocksize)
        if len(buffer) < sbx.blocksize:
            break
        if not sbx.decode(buffer):
            errexit(errlev=1, mess="invalid block at offset %s" %
                    (hex(fin.tell()-sbx.blocksize)))
        else:
            if sbx.blocknum > lastblocknum+1:
                errexit(errlev=1, mess="block %i out of order or missing"
                         % (lastblocknum+1))    
            lastblocknum += 1
            if trimfilesize:
                filesize += sbx.datasize
                if filesize > metadata["filesize"]:
                    sbx.data = sbx.data[:-(filesize - metadata["filesize"])]
            d.update(sbx.data)
            if not cmdline.test:
                fout.write(sbx.data)

            #some progress report
            if time() > updatetime: 
                print("  %.1f%%" % (fin.tell()*100.0/sbxfilesize),
                      end="\r", flush=True)
                updatetime = time() + .1

    fin.close()
    if not cmdline.test:
        fout.close()

    print("SBx decodeding complete")
    if "hash" in metadata:
        print("SHA256",d.hexdigest())
        if d.digest() ==  metadata["hash"]:
            print("hash match!")
        else:
            errexit(1, "hash mismatch! decoded file corrupted!")
    else:
        #if filesize unknown, estimate based on 0x1a padding at block's end
        c = lastEofCount(sbx.data[-4:])
        print("EOF markers at the end of last block: %i/4" % c)


if __name__ == '__main__':
    main()
