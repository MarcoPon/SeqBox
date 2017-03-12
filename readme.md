# SeqBox - Sequenced Box container

> A single file container/archive that can be reconstructed even after total loss of file system structures.

A SeqBox container ese a blocksize sub/equal to that of a sector, so can survive any level of fragmentation. Eeach block have a minimal header that include a unique file identifier, block sequence number, checksum, version.
Additional, non critical info/metadata are contained in block 0 (like name, file size, crypto-hash, other attributes, etc.).

If disaster strikes, recovery can be performed simply scanning a volume/image, reading sector sized slices and checking blocks signatures and then CRCs to detect valid SBX blocks. Then the blocks can be grouped by UIDs, sorted by sequence number and reassembled to form the original SeqBox containers.

![It's Magic](http://i.imgur.com/DQZDO0P.gif)

It's also possible and entirely transparent to keep multiple copies of a container, in the same or different media, to increase the chances of recoverability. In case of corrupted blocks, all the good ones can be collected and reassembled from all available sources.

The UID can be anything, as long as is unique for the specific application. It could be random generated (probably the most common option), or a hash of the file content, or a simple sequence, etc.

Overhead is minimal: for SBX v1 is 16B/512B (+1 optional 512B block), or < 3.5%.

## Possible / hypotetic / ideal uses cases
 - Last step of a backup - after creating a compressed archive of something, the archive could be SeqBox encoded to increase recovery chances in the event of some software/hardware issues that cause logic / file system's damages.
 - Encoding of photos on a SDCard - loss of images on perfectly functioning SDCards are known occurances in the photography world, for example when low on battery and maybe with a camera/firmware with suboptimal monitoring & management strategies. If the photo files are fragmented, recovery tools can usually help only to a point. 
 - On-disk format for a File System. The tradeoff in file size and performance (both should be fairly minimal anyway) could be interesting for some application. Maybe it could be a simple option (like compression in many FS). I plan to build a simple/toy FS with FUSE to test the concept, time permitting.
 - Probably less interesting, but a SeqBox container can also be splitted very easily, with no particular precautions aside from doing that on blocksize multiples. So any tool that have for example 1KB granularity, can be used. Additionaly, there's no need to use special naming conventions, numbering files, etc., as the SBX container can be reassembled exactly like when doing a recovery. 

## Usage

The two main tools are obviously the encoder & decoder:
 - SBXEnc: encode a file to a SBX container
 - SBXDec: decode SBX back to original file; can also show info on a container and tests for integrity against a crypto-hash
  
The other two are the recovery tools: 
 - SBXScan: scan a set of files (raw images, or even block devices on Linux) to build a Sqlite db with the necessary recovery info
 - SBXReco: rebuild SBX files using data collected by SBXScan

> (to be completed... in the mean time, -h will do)

## Tech spec

### Common blocks header:

| pos | to pos | size   | desc              |
|---- | ---    | ---- | ----------------- |
|  0  |      2 |   3  | Recoverable Block signature = 'SBx' |
|  3  |      3 |   1  | Version byte (1) |
|  4  |      5 |   2  | Block CRC-16 CCITT (Version is used as starting value) |
|  6  |     11 |	  6  | file UID |
| 12  |     15 |   4  | Block sequence number |

### Block 0

| pos | to pos   | size | desc             |
|---- | -------- | ---- | ---------------- |
| 16  | n        | var  | encoded metadata |
|  n+1| blockend | var  | padding (0x1a)   |


### Blocks > 0 & < last:

| pos | to pos   | size | desc             |
|---- | -------- | ---- | ---------------- |
| 16  | blockend | var  | data             |

### Blocks == last:

| pos | to pos   | size | desc             |
|---- | -------- | ---- | ---------------- |
| 16  | n        | var  | data             |
| n+1 | blockend | var  | padding (0x1a)   |

#### Metadata encoding:

| Bytes | Field | 
| ----- | ----- |
|    3  | ID    |
|    1  | Len   |
|    n  | Data  |

#### IDs

| ID | Desc |
| --- | --- |
| FNM | filename (utf-8) |
| SNM | sbx filename (utf-8) |
| FSZ | filesize (8 bytes) |
| HSH | SHA256 crypto hash |
(others IDs for file dates, attributes, etc. will be added...)

## Final notes
The code was quickly hacked in spare slices of time to verify the basic idea, so it will benefit for some refactoring, in time.
Still, the current block format is stable and some precautions have been taken to ensure that any encoded file could be correctly decoded. For example, the SHA256 hash that is stored as metadata is calculate before any other file operation.
So, as long as a newly created SBX file is checked as OK with SBXDec, it should be OK.
