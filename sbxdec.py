#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBXDec - Sequenced Box container Decoder
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
import time

import seqbox

PROGRAM_VER = "1.0.2"


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="decode a SeqBox container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Decoder v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("sbxfilename", action="store", help="SBx container")
    parser.add_argument("filename", action="store", nargs='?', 
                        help="target/decoded file")
    parser.add_argument("-t","--test", action="store_true", default=False,
                        help="test container integrity")
    parser.add_argument("-i", "--info", action="store_true", default=False,
                        help="show informations/metadata")
    parser.add_argument("-c", "--continue", action="store_true", default=False,
                        help="continue on block errors", dest="cont")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
    parser.add_argument("-p", "--password", type=str, default="",
                        help="encrypt with password", metavar="pass")
    res = parser.parse_args()
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        sys.stderr.write("%s: error: %s\n" %
                         (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)


def lastEofCount(data):
    count = 0
    for b in range(len(data)):
        if data[-b-1] != 0x1a:
            break
        count +=1
    return count


def main():

    cmdline = get_cmdline()

    sbxfilename = cmdline.sbxfilename
    filename = cmdline.filename

    if not os.path.exists(sbxfilename):
        errexit(1, "sbx file '%s' not found" % (sbxfilename))
    sbxfilesize = os.path.getsize(sbxfilename)

    print("decoding '%s'..." % (sbxfilename))
    fin = open(sbxfilename, "rb", buffering=1024*1024)

    #check magic and get version
    header = fin.read(4)
    fin.seek(0, 0)
    if cmdline.password:
        e = seqbox.EncDec(cmdline.password, len(header))
        header= e.xor(header)
    if header[:3] != b"SBx":
        errexit(1, "not a SeqBox file!")
    sbxver = header[3]
    
    sbx = seqbox.SbxBlock(ver=sbxver, pswd=cmdline.password)
    metadata = {}
    trimfilesize = False

    hashtype = 0
    hashlen = 0
    hashdigest = b""
    hashcheck = False

    buffer = fin.read(sbx.blocksize)

    try:
        sbx.decode(buffer)
    except seqbox.SbxDecodeError as err:
        if cmdline.cont == False:
            print(err)
            errexit(errlev=1, mess="invalid block at offset 0x0")

    if sbx.blocknum > 1:
        errexit(errlev=1, mess="blocks missing or out of order at offset 0x0")
    elif sbx.blocknum == 0:
        print("metadata block found!")
        metadata = sbx.metadata
        if "filesize" in metadata:
            trimfilesize = True
        if "hash" in metadata:
            hashtype = metadata["hash"][0]
            if hashtype == 0x12:
                hashlen = metadata["hash"][1]
                hashdigest = metadata["hash"][2:2+hashlen]
                hashcheck = True
        
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
        if metadata:
            print("metadata:")
            if "sbxname" in metadata:
                print("  SBX name : '%s'" % (metadata["sbxname"]))
            if "filename" in metadata:
                print("  file name: '%s'" % (metadata["filename"]))
            if "filesize" in metadata:
                print("  file size: %i bytes" % (metadata["filesize"]))
            if "sbxdatetime" in metadata:
                print("  SBX date&time : %s" %
                      (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["sbxdatetime"]))))
            if "filedatetime" in metadata:
                print("  file date&time: %s" %
                      (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["filedatetime"]))))
            if "hash" in metadata:
                if hashtype == 0x12:
                    print("  SHA256: %s" % (binascii.hexlify(
                        hashdigest).decode()))
                else:
                    print("  hash type not recognized!")
        sys.exit(0)

    #evaluate target filename
    if not cmdline.test:
        if not filename:
            if "filename" in metadata:
                filename = metadata["filename"]
            else:
                filename = os.path.split(sbxfilename)[1] + ".out"
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

    if hashtype == 0x12:
        d = hashlib.sha256()
    lastblocknum = 0

    filesize = 0
    blockmiss = 0
    updatetime = time.time() 
    while True:
        buffer = fin.read(sbx.blocksize)
        if len(buffer) < sbx.blocksize:
            break

        try:
            sbx.decode(buffer)
            if sbx.blocknum > lastblocknum+1:
                if cmdline.cont:
                    blockmiss += 1
                    lastblocknum += 1
                else:
                    errexit(errlev=1, mess="block %i out of order or missing"
                             % (lastblocknum+1))    
            lastblocknum += 1
            if trimfilesize:
                filesize += sbx.datasize
                if filesize > metadata["filesize"]:
                    sbx.data = sbx.data[:-(filesize - metadata["filesize"])]
            if hashcheck:
                d.update(sbx.data) 
            if not cmdline.test:
                fout.write(sbx.data)

        except seqbox.SbxDecodeError as err:
            if cmdline.cont:
                blockmiss += 1
                lastblocknum += 1
            else:
                print(err)
                errexit(errlev=1, mess="invalid block at offset %s" %
                        (hex(fin.tell()-sbx.blocksize)))

        #some progress report
        if time.time() > updatetime: 
            print("  %.1f%%" % (fin.tell()*100.0/sbxfilesize),
                  end="\r", flush=True)
            updatetime = time.time() + .1

    fin.close()
    if not cmdline.test:
        fout.close()
        if metadata:
            if "filedatetime" in metadata:
                os.utime(filename,
                         (int(time.time()), metadata["filedatetime"]))

    print("SBX decoding complete")
    if blockmiss:
        errexit(1, "missing blocks: %i" % blockmiss)

    if hashcheck:
        if hashtype == 0x12:
            print("SHA256", d.hexdigest())

        if d.digest() == hashdigest:
            print("hash match!")
        else:
            errexit(1, "hash mismatch! decoded file corrupted!")
    else:
        print("can't check integrity via hash!")
        #if filesize unknown, estimate based on 0x1a padding at block's end
        if not trimfilesize:
            c = lastEofCount(sbx.data[-4:])
            print("EOF markers at the end of last block: %i/4" % c)


if __name__ == '__main__':
    main()
