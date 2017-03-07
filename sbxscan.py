#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBxEnc - Sequenced Box container Scanner
#
# Created: 06/03/2017
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
import fnmatch
from functools import partial
from time import sleep, time
import sqlite3

import seqbox

PROGRAM_VER = "0.10a"

def banner():
    """Display the usual presentation, version, (C) notices, etc."""
    print("\nSeqBox - Sequenced Box container - Scanner v%s" % (PROGRAM_VER),
          " - (C) 2017 by M.Pontello\n")


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description=("scan files/disks for SBx blocks and create a "+
                          "detailed report plus an index to be used with "+
                          "SBxResq"),
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-/+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SBxScanner v%s' % PROGRAM_VER)
    parser.add_argument("filenames", action="store", nargs="+",
                        help="files to scan (can include paths & wildcards)")
    parser.add_argument("-r", "--recurse", action="store_true", default=False,
                        help="recurse subdirs")
    parser.add_argument("-d", "--database", action="store", dest="dbfilename",
                        metavar="dbfilename", help="database for recovery info",
                        default="sbxscan.db")
    parser.add_argument("-l", "--list", action="store", dest="listfilename",
                        help=("report with detailed listing of scan results"),
                        metavar="listfilename", default="sbxscan.csv")
    parser.add_argument("-o", "--offset", type=int, default=0,
                        help=("offset from the start (to be used with non-raw "+
                              "disk images with some header"), metavar="n")
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBx blocks version to search for", metavar="v")
    res = parser.parse_args()
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)
      


def main():

    banner()
    cmdline = get_cmdline()

    filenames = []
    for filespec in cmdline.filenames:
        filepath, filename = os.path.split(filespec)
        if not filepath:
            filepath = "."
        if not filename:
            filename = "*"
        for wroot, wdirs, wfiles in os.walk(filepath):
            if not cmdline.recurse:
                wdirs[:] = []
            for fn in fnmatch.filter(wfiles, filename):
                filenames.append(os.path.join(wroot, fn))
    filenames = sorted(set(filenames), key=os.path.getsize)

    #create database file and tables
    dbfilename = cmdline.dbfilename
    print("creating '%s' database..." % (dbfilename))
    if os.path.exists(dbfilename):
        os.remove(dbfilename)
    conn = sqlite3.connect(dbfilename)
    c = conn.cursor()
    c.execute("CREATE TABLE files (id INTEGER, name TEXT)")
    c.execute("CREATE TABLE sbx (uid INTEGER, size INTEGER, name TEXT, sbxname TEXT, fileid INTEGER)")
    c.execute("CREATE TABLE blocks (uid INTEGER, num INTEGER, fid INTEGER, pos INTEGER )")


    #scan all the files/devices 
    sbx = seqbox.sbxBlock(ver=cmdline.sbxver)
    offset = cmdline.offset
    filenum = 0
    uids = {}
    magic = b'SBx' + cmdline.sbxver.to_bytes(1, byteorder='big', signed=True)

    for filename in filenames:
        filenum += 1
        print("scanning file/device '%s' (%i/%i)..." %
              (filename, filenum, len(filenames)))
        filesize = os.path.getsize(filename)
        blocksnum = (filesize - offset) // sbx.blocksize

        c.execute("INSERT INTO files (id, name) VALUES (?, ?)",
          (filenum, filename))

        fin = open(filename, "rb")
        fin.seek(offset, 0)
        blocksfound = 0
        blocksmetafound = 0
        updatetime = time()
        starttime = time()
        docommit = False
        for b in range(blocksnum):
            p = fin.tell()
            buffer = fin.read(sbx.blocksize)
            #check for magic
            if buffer[:4] == magic:
                #check for valid block
                if sbx.decode(buffer):
                    #used to keep a quick in memory list of the uids/files found
                    uids[sbx.uid] = True
                    blocksfound+=1
                    #update blocks table
                    c.execute(
                        "INSERT INTO blocks (uid, num, fid, pos) VALUES (?, ?, ?, ?)",
                        (int.from_bytes(sbx.uid, byteorder='big'),
                        sbx.blocknum, filenum, p))
                    docommit = True

                    if sbx.blocknum == 0:
                        blocksmetafound += 1
                        


            #fakedelay
            #sleep(.01)            
            
            #status update
            if (time() > updatetime) or (b == blocksnum-1):
                print("%5.1f%% blocks: %i - meta: %i - UIDs: %i - %.2fMB/s" %
                      ((b+1)*100.0/blocksnum, blocksfound, blocksmetafound,
                       len(uids), b*512/(1024*1024)/(time()-starttime)),
                      end = "\r", flush=True)
                if docommit:
                    conn.commit()
                    docommit = False
                updatetime = time() + .5

        fin.close()
        print()
        

    c.close()
    conn.close()

    print("scan completed!")    


if __name__ == '__main__':
    main()
