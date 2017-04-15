#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBXScan - Sequenced Box container Scanner
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
import argparse
import binascii
from time import sleep, time
import sqlite3

import seqbox

PROGRAM_VER = "1.0.1"

def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description=("scan files/devices for SBx blocks and create a "+
                          "detailed report plus an index to be used with "+
                          "SBXScan"),
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-', fromfile_prefix_chars='@')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Scanner v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("filename", action="store", nargs="+",
                        help="file(s) to scan")
    parser.add_argument("-d", "--database", action="store", dest="dbfilename",
                        metavar="filename",
                        help="where to save recovery info",
                        default="sbxscan.db3")
    parser.add_argument("-o", "--offset", type=int, default=0,
                        help=("offset from the start"), metavar="n")
    parser.add_argument("-st", "--step", type=int, default=0,
                        help=("scan step"), metavar="n")
    parser.add_argument("-b", "--buffer", type=int, default=1024,
                        help=("read buffer in KB"), metavar="n")
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version to search for", metavar="n")
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

      
def getFileSize(filename):
    """Calc file size - works on devices too"""
    ftemp = os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(ftemp, 0, os.SEEK_END)
    finally:
        os.close(ftemp)


def main():

    cmdline = get_cmdline()

    filenames = []
    for filename in cmdline.filename:
        if os.path.exists(filename):
            filenames.append(filename)
        else:
            errexit(1, "file '%s' not found!" % (filename))
    filenames = sorted(set(filenames), key=os.path.getsize)

    dbfilename = cmdline.dbfilename
    if os.path.isdir(dbfilename):
        dbfilename = os.path.join(dbfilename, "sbxscan.db3")

    #create database tables
    print("creating '%s' database..." % (dbfilename))
    if os.path.exists(dbfilename):
        os.remove(dbfilename)
    conn = sqlite3.connect(dbfilename)
    c = conn.cursor()
    c.execute("CREATE TABLE sbx_source (id INTEGER, name TEXT)")
    c.execute("CREATE TABLE sbx_meta (uid INTEGER, size INTEGER, name TEXT, sbxname TEXT, datetime INTEGER, sbxdatetime INTEGER, fileid INTEGER)")
    c.execute("CREATE TABLE sbx_uids (uid INTEGER, ver INTEGER)")
    c.execute("CREATE TABLE sbx_blocks (uid INTEGER, num INTEGER, fileid INTEGER, pos INTEGER )")
    c.execute("CREATE INDEX blocks ON sbx_blocks (uid, num, pos)")

    #scan all the files/devices 
    sbx = seqbox.SbxBlock(ver=cmdline.sbxver,pswd=cmdline.password)
    offset = cmdline.offset
    filenum = 0
    uids = {}
    magic = b'SBx' + bytes([cmdline.sbxver])
    if cmdline.password:
        magic = seqbox.EncDec(cmdline.password, len(magic)).xor(magic)
    scanstep = cmdline.step
    if scanstep == 0:
        scanstep = sbx.blocksize

    for filename in filenames:
        filenum += 1
        print("scanning file/device '%s' (%i/%i)..." %
              (filename, filenum, len(filenames)))
        filesize = getFileSize(filename)

        c.execute("INSERT INTO sbx_source (id, name) VALUES (?, ?)",
          (filenum, filename))
        conn.commit()

        fin = open(filename, "rb", buffering=cmdline.buffer*1024)
        blocksfound = 0
        blocksmetafound = 0
        updatetime = time() - 1
        starttime = time()
        docommit = False
        for pos in range(offset, filesize, scanstep):
            fin.seek(pos, 0)
            buffer = fin.read(sbx.blocksize)
            #check for magic
            if buffer[:4] == magic:
                #check for valid block
                try:
                    sbx.decode(buffer)
                    #update uids table & list
                    if not sbx.uid in uids:
                        uids[sbx.uid] = True
                        c.execute(
                            "INSERT INTO sbx_uids (uid, ver) VALUES (?, ?)",
                            (int.from_bytes(sbx.uid, byteorder='big'),
                             sbx.ver))
                        docommit = True

                    #update blocks table
                    blocksfound+=1
                    c.execute(
                        "INSERT INTO sbx_blocks (uid, num, fileid, pos) VALUES (?, ?, ?, ?)",
                        (int.from_bytes(sbx.uid, byteorder='big'),
                         sbx.blocknum, filenum, pos))
                    docommit = True

                    #update meta table
                    if sbx.blocknum == 0:
                        blocksmetafound += 1
                        if not "filedatetime" in sbx.metadata:
                            sbx.metadata["filedatetime"] = -1
                            sbx.metadata["sbxdatetime"] = -1

                        c.execute(
                            "INSERT INTO sbx_meta (uid , size, name, sbxname, datetime, sbxdatetime, fileid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (int.from_bytes(sbx.uid, byteorder='big'),
                             sbx.metadata["filesize"],
                             sbx.metadata["filename"], sbx.metadata["sbxname"],
                             sbx.metadata["filedatetime"], sbx.metadata["sbxdatetime"],
                             filenum))
                        docommit = True

                except seqbox.SbxDecodeError:
                    pass

            #status update
            if (time() > updatetime) or (pos >= filesize - scanstep):
                etime = (time()-starttime)
                if etime == 0:
                    etime = 1
                print("%5.1f%% blocks: %i - meta: %i - files: %i - %.2fMB/s" %
                      (pos*100.0/(filesize-scanstep), blocksfound,
                       blocksmetafound, len(uids), pos/(1024*1024)/etime),
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
