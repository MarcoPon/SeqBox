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


def main():
    rbxblocksize = 512
    rbxhdrsize = 16

    res = get_cmdline()
    filename = res.filename

    rbxhdr = bytes(rbxhdrsize)
    print("reading %s..." % filename)
    f = open(filename, "rb")
    totsize = 0
    for data in chunked(f, rbxblocksize - rbxhdrsize):
        totsize += len(data)
        print(totsize)
    f.close()
    print("ok!")


if __name__ == '__main__':
    main()
