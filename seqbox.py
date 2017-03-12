#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SeqBox - Sequenced Box container module
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
import binascii
import random


class sbxBlock():
    """
    Implement a basic SBX block
    """
    def __init__(self, ver=1, uid="r"):
        self.supported_vers = [0, 1, 2]
        self.ver = ver
        if ver in [0,1]:
            self.blocksize = 512
            self.hdrsize = 16
        elif ver == 2:
            #just a test to double check all tools works correctly
            #with different parameters. or it could be good for CP/M! :)
            self.blocksize = 128
            self.hdrsize = 16
        else:
            raise version_not_supported #put in a proper exception
        self.datasize = self.blocksize - self.hdrsize
        self.magic = b'SBx' + bytes([ver])
        self.blocknum = 0

        if uid == "r":
            random.seed()
            self.uid = random.getrandbits(6*8).to_bytes(6, byteorder='big')
        else:
            self.uid = (b'\x00'*6 + uid)[-6:]

        self.parent_uid = 0
        self.metadata = {}
        self.data = b""

    def __str__(self):
        return "SBX Block ver: '%i', size: %i, hdr size: %i, data: %i" % \
               (self.ver, self.blocksize, self.hdrsize, self.datasize)

    def encode(self):
        if self.blocknum == 0:
            self.data = b""
            if "filename" in self.metadata:
                bb = self.metadata["filename"].encode()
                self.data += b"FNM" + bytes([len(bb)]) + bb
            if "sbxname" in self.metadata:
                bb = self.metadata["sbxname"].encode()
                self.data += b"SNM" + bytes([len(bb)]) + bb
            if "filesize" in self.metadata:
                bb = self.metadata["filesize"].to_bytes(8, byteorder='big')
                self.data += b"FSZ" + bytes([len(bb)]) + bb
            if "hash" in self.metadata:
                bb = self.metadata["hash"]
                self.data += b"HSH" + bytes([len(bb)]) + bb
        
        data = self.data + b'\x1A' * (self.datasize - len(self.data))
        buffer = (self.uid +
                  self.blocknum.to_bytes(4, byteorder='big') +
                  data)
        crc = binascii.crc_hqx(buffer, self.ver).to_bytes(2,byteorder='big')
        return (self.magic + crc + buffer)

    def decode(self, buffer):
        #check the basics
        if len(buffer) != self.blocksize:
            return False
        if buffer[:3] != self.magic[:3]:
            return False
        if not buffer[3] in self.supported_vers:
            return False

        #check CRC of rest of the block
        crc = int.from_bytes(buffer[4:6], byteorder='big') 
        if crc != binascii.crc_hqx(buffer[6:], self.ver):
            return False

        self.uid = buffer[6:12]
        self.blocknum = int.from_bytes(buffer[12:16], byteorder='big') 
        self.data = buffer[16:]

        if self.blocknum == 0:
            #decode meta data
            p = 0
            while p < (len(self.data)-3):
                metaid = self.data[p:p+3]
                p+=3
                if metaid == b"\x1a\x1a\x1a":
                    break
                else:
                    metalen = self.data[p]
                    metabb = self.data[p+1:p+1+metalen]
                    p = p + 1 + metalen    
                    if metaid == b'FNM':
                        self.metadata["filename"] = metabb.decode('utf-8')
                    if metaid == b'SNM':
                        self.metadata["sbxname"] = metabb.decode('utf-8')
                    if metaid == b'FSZ':
                        self.metadata["filesize"] = int.from_bytes(metabb, byteorder='big')
                    if metaid == b'HSH':
                        self.metadata["hash"] = metabb
        return True


def main():
    print("SeqBox module!")
    sys.exit(0)

if __name__ == '__main__':
    main()
