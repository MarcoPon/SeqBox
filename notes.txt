SeqBox - Sequenced Box container (SEQBOX/SBX)
===========================================

Encode a file in a container that can be reconstructed even after total
loss of file system structures. Use a blocksize equal or submultiple of a
sector/cluster size, with a minimal header that include block sequence
number, checksum and other info. 
Additional, non critical info/metadata are contained in block 0 (like name,
file size, other attributes, etc.).

Recovery can be performed simply scanning a disk / image, reading
sector/cluster sized slices and checking block signature and then CRC to
detect valid SeqBox blocks. Then blocks can be sorted by UID's and sequence
numbers.

Optionally blocks can be freely duplicated and/or stored in different media
to enhance recoverability.

The UID can be anything, as long as is unique for the specific application. 
It could be random generated, or a hash of the file content, or a simple
sequence, etc. For the tools is just a sequence of bytes.

Overhead is minimal: from 16B/512B (+1 512B block) to 16B/32KB (+1 32KB block)

Could become part of a File System.

Command line tools to:
- sbxenc: encode file to SBX
- sbxdec: decode SBX to file (and also test or get info)
- sbxscan: scan files to build an Sqlite db of blocks positions, num, uid
           and a detailed log (in various formats, to enable other tools)
- sbxrec: rebuild sbx files using previous scanned info


Common blocks header:

  0-  2   3 Recoverable Block signature = 'SBx'
  3-  3   1 Version byte 
  4-  5   2 Block CRC-16 (Version is used as starting value)
  6- 11	  6 file UID (MD5 or other 32bit hash) 
 12- 15   4 Block sequence number

------------------------

Block sequence = 0

 16-nnn nnn encoded metadata
nnn-blksize padding (0x1A)
------------------------

Block sequence > 0:

 16-nnn nnn data  
nnn-blksize padding (0x1A) (for the last block)
 
------------------------

metadata encoding:
3 bytes str ID + 1 byte length + data

ID:
FNM filename (utf-8)
SNM sbx filename (utf-8)
FSZ filesize 8 bytes
HSH SHA256 crypto hash
