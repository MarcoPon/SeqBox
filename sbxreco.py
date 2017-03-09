#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBxReco - Sequenced Box container Recover
#s
# Created: 08/03/2017
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
import sqlite3

import seqbox

PROGRAM_VER = "0.62a"

BLOCKSIZE = 512

def banner():
    """Display the usual presentation, version, (C) notices, etc."""
    print("\nSeqBox - Sequenced Box container - Recover v%s" % (PROGRAM_VER),
          " - (C) 2017 by M.Pontello\n")


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="recover SeqBox containers",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SBxRecover v%s' % PROGRAM_VER)
    parser.add_argument("dbfilename", action="store", metavar="filename",
                        help="database with recovery info")
    parser.add_argument("destpath", action="store", nargs="?", metavar="path",
                        help="destination path for recovered sbx files")
    parser.add_argument("-file", action="store", nargs="+", metavar="filename",
                        help="original filename(s) to recover")
    parser.add_argument("-sbx", action="store", nargs="+", metavar="filename",
                        help="SBx filename(s) to recover")
    parser.add_argument("-uid", action="store", nargs="+", metavar="uid",
                        help="UID(s) to recover")
    parser.add_argument("-all", action="store_true", help="recover all")
    parser.add_argument("-i", "--info", action="store_true", default=False,
                        help="show info on recoverable sbx file(s)")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing sbx file(s)")
    res = parser.parse_args()
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)


def dbGetMetaFromUID(c, uid):
    meta = {}
    c.execute("SELECT * from sbx_meta where uid = '%i'" % uid)
    res = c.fetchone()
    if res:
        meta["filesize"] = res[1]
        meta["filename"] = res[2]
        meta["sbxname"] = res[3]
    return meta

def dbGetUIDFromFileName(c, filename):
    c.execute("select uid from sbx_meta where name = '%s'" % (filename))
    res = c.fetchone()
    if res:
        return(res[0])

def dbGetUIDFromSbxName(c, sbxname):
    c.execute("select uid from sbx_meta where sbxname = '%s'" % (sbxname))
    res = c.fetchone()
    if res:
        return(res[0])

def dbGetBlocksCountFromUID(c, uid):
    c.execute("SELECT uid from sbx_blocks where uid = '%i' group by num order by num" % (uid))
    return len(c.fetchall())

def dbGetBlocksListFromUID(c, uid):
    c.execute("SELECT num, fileid, pos from sbx_blocks where uid = '%i' group by num order by num" % (uid))
    return c.fetchall()


def report(c):
    """Create a detailed report with the info obtained by SbxScan"""

    #test
    c.execute("SELECT uid from sbx_blocks group by uid order by uid")
    for row in c.fetchall():
        uid = row[0]
        hexdigits = binascii.hexlify(uid.to_bytes(6, byteorder="big")).decode()
        metadata = dbGetMetaFromUID(c, uid)
        blocksnum = dbGetBlocksCountFromUID(c, uid)
        filename = metadata["filename"] if "filename" in metadata else ""
        sbxname = metadata["sbxname"] if "sbxname" in metadata else ""

        if "filesize" in metadata:
            filesize = metadata["filesize"]
            est = ""
        else:
            filesize = blocksnum * BLOCKSIZE
            est = chr(126)
        
        print("%s %i %i%s '%s'" % (hexdigits, blocksnum, filesize, est, sbxname))

def main():

    banner()
    cmdline = get_cmdline()

    dbfilename = cmdline.dbfilename
    if not os.path.exists(dbfilename) or os.path.isdir(dbfilename):
        errexit(1,"file '%s' not found!" % (dbfilename))

    #open database
    print("opening '%s' database..." % (dbfilename))
    conn = sqlite3.connect(dbfilename)
    c = conn.cursor()

    if cmdline.info:
        report(c)
        errexit(0)

    #build a list of uid to recover:
    uid_list = []
    if cmdline.uid:
        for hexuid in cmdline.uid:
            if len(hexuid) % 2 != 0:
                errexit(1, "invalid UID!")
            uid = int.from_bytes(binascii.unhexlify(hexuid),
                                 byteorder="big")
            #just a stub to notify immediately
            if dbGetBlocksCountFromUID(c, uid):
                uid_list.append(uid)
            else:
                errexit(1,"no recoverable UID '%s'" % (hexuid))
    if cmdline.sbx:
        for sbxname in cmdline.sbx:
            uid = dbGetUIDFromSbxName(c, sbxname)
            if uid:
                uid_list.append(uid)
            else:
                errexit(1,"no recoverable sbx file '%s'" % (sbxname))
    if cmdline.file:
        for filename in cmdline.file:
            uid = dbGetUIDFromFileName(c, filename)
            if uid:
                uid_list.append(uid)
            else:
                errexit(1,"no recoverable file '%s'" % (filename))

    print("recovering SBx files...")
    uid_list = sorted(set(uid_list))

    #open the list of sources - need to be built !TEMP!
    finlist = {}
    finlist[1] = open(r"\t\msx.ima", "rb", buffering=1024*1024)

    uidcount = 0
    for uid in uid_list:
        uidcount += 1
        hexuid = binascii.hexlify(uid.to_bytes(6, byteorder="big")).decode()
        print("UID %s (%i/%i)" % (hexuid, uidcount, len(uid_list)))

        blocksnum = dbGetBlocksCountFromUID(c, uid)
        print("  blocks: %i - size: %i bytes" %
              (blocksnum, blocksnum * BLOCKSIZE))

        fout = open(r"\t\out.sbx", "wb", buffering = 1024*1024)

        blockdatalist = dbGetBlocksListFromUID(c, uid)
        for blockdata in blockdatalist:
            print(blockdata)
            fin = finlist[blockdata[1]]
            bpos = blockdata[2]
            fin.seek(bpos, 0)
            buffer = fin.read(BLOCKSIZE)
            fout.write(buffer)
        fout.close()



if __name__ == '__main__':
    main()
