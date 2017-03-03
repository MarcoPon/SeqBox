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
import binascii
import random


class sbxBlock():
    """
    Implement a basic SBX block
    """
    def __init__(self, ver=0, uid="r"):
        self.ver = ver
        if ver in [0,1]:
            self.blocksize = 512
            self.hdrsize = 16
        else:
            raise version_not_supported #put in a proper exception
        self.datasize = self.blocksize - self.hdrsize
        self.magic = b'SBx' + ver.to_bytes(1, byteorder='big', signed=True)
        self.blocknum = 0

        if uid == "r":
            random.seed()
            self.uid = random.getrandbits(48)
        else:
            self.uid = 0

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
                self.data += b"NM" + len(bb).to_bytes(1, byteorder='little') + bb
            if "filesize" in self.metadata:
                bb = self.metadata["filesize"].to_bytes(8, byteorder='little', signed=True)
                self.data += b"SZ" + len(bb).to_bytes(1, byteorder='little') + bb
            if "hash" in self.metadata:
                bb = self.metadata["hash"]
                self.data += b"HS" + len(bb).to_bytes(1, byteorder='little') + bb
        
        data = self.data + b'\x1A' * (self.datasize - len(self.data))
        buffer = (self.uid.to_bytes(6, byteorder='little') +
                  self.blocknum.to_bytes(4, byteorder='little') +
                  data)
        crc = binascii.crc_hqx(buffer,0).to_bytes(2,byteorder='little')
        return (self.magic + crc + buffer)

    def decode(self, buffer):
        #check the basics
        if len(buffer) != self.blocksize:
            return False
        if buffer[:3] != self.magic[:3]:
            return False
        print("Magic: OK!")
        if not buffer[3] in [0,1]:
            return False
        print("Version:", buffer[3])

        #check CRC of rest of the block
        crc = int.from_bytes(buffer[4:6], byteorder='little') 
        if crc != binascii.crc_hqx(buffer[6:],0):
            return False
        print("CRC: OK!")

        self.uid = int.from_bytes(buffer[6:12], byteorder='little') 
        self.blocknum = int.from_bytes(buffer[12:16], byteorder='little') 
        self.data = buffer[16:]

        if self.blocknum == 0:
            #decode meta data
            pass

        return True


def main():
    print("SeqBox module!")
    sys.exit(0)

if __name__ == '__main__':
    main()
