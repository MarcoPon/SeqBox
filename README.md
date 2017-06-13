# SeqBox - Sequenced Box container
### A single file container/archive that can be reconstructed even after total loss of file system structures.
![SBX-Logo](http://i.imgur.com/Ewper2w.png)

An SBX container exists both as a normal file in a mounted file system, and as a collection of recognizable blocks at a lower level.

SBX blocks have a size sub-multiple/equal to that of a sector, so they can survive any level of fragmentation. Each block have a minimal header that include a unique file identifier, block sequence number, checksum, version.
Additional, non critical info/metadata are contained in block 0 (like name, file size, crypto-hash, other attributes, etc.).

If disaster strikes, recovery can be performed simply scanning a volume/image, reading sector sized slices and checking blocks signatures and then CRCs to detect valid SBX blocks. Then the blocks can be grouped by UIDs, sorted by sequence number and reassembled to form the original SeqBox containers.

![It's Magic](http://i.imgur.com/DQZDO0P.gif)

It's also possible and entirely transparent to keep multiple copies of a container, in the same or different media, to increase the chances of recoverability. In case of corrupted blocks, all the good ones can be collected and reassembled from all available sources.

The UID can be anything, as long as is unique for the specific application. It could be random generated (probably the most common option), or a hash of the file content, or a simple sequence, etc.

Overhead is minimal: for SBX v1 is 16B/512B (+1 optional 512B block), or < 3.5%.

## Demo tour

The two main tools are obviously the encoder & decoder:
 - SBXEnc: encode a file to a SBX container
 - SBXDec: decode SBX back to original file; can also show info on a container and tests for integrity against a crypto-hash
  
The other two are the recovery tools: 
 - SBXScan: scan a set of files (raw images, or even block devices on Linux) to build a Sqlite db with the necessary recovery info
 - SBXReco: rebuild SBX files using data collected by SBXScan

There are in some case many parameters but the default are sensible so it's generally pretty simple.

Now to a practical example: let's see how 2 photos and their 2 SBX encoded versions go trough a fragmented floppy disk that have lost its FAT (and any other system part). We start with the 2 pictures, about 200KB and 330KB:

![Castle](http://i.imgur.com/Qf0qrUp.jpg) ![Lake](http://i.imgur.com/9rH6tMf.jpg)

We encode using SBXEnc, and then test the new file with SBXDec, to be sure all is OK:

```
C:\t>sbxenc Lake.jpg
hashing file 'Lake.jpg'...
SHA256 3cfc376b6362444d2d25ebedb19e7594000f2ce2bdbb521d98f6c59b5adebfdc
creating file 'Lake.jpg.sbx'...
100%
SBX file size: 343040 - blocks: 670 - overhead: 3.4%

C:\t>sbxdec -t Lake.jpg.sbx
decoding 'Lake.jpg.sbx'...
metadata block found!
SBX decoding complete
SHA256 3cfc376b6362444d2d25ebedb19e7594000f2ce2bdbb521d98f6c59b5adebfdc
hash match!
```

Same for the other file. Now we put both the JPEG and the SBX files in a floppy disk image already about half full, that have gone trough various cycles of updating and deleting. As a result the data is laid out like this:

![Disk Layout](http://i.imgur.com/cBoXONY.png)

Normal files (pictures included) are in green, and the two SBX in different shades of blue.
Then with an hex editor we zap the first system sectors and the FAT (in red)!
Time for recovery!

We start with the free (GPLV v2+) [PhotoRec](http://www.cgsecurity.org/wiki/PhotoRec), which is the go-to tool for these kind of jobs. Parameters are set to "Paranoid : YES (Brute force enabled)" & "Keep corrupted files : Yes", to search the entire data area. 
As the files are fragmented, we know we can't expect miracles. The starting sector of the photos will be surely found, but as soon as the first contiguous fragment end, it's anyone guess.

![PhotoRec results](http://i.imgur.com/qa0PySP.png)

As expected, something has been recovered. But the 2 files size are off (280K and 400KB). The very first parts of the photos are OK, but then they degrade quickly as other random blocks of data where mixed in. We have all seen JPEGs ending up like this:

![Castle](http://i.imgur.com/kP0jwyC.jpg) ![Lake](http://i.imgur.com/GyOonct.jpg)

Other popular recovery tools lead to the same results. It's not anyone fault: it's just not possible to know how the various fragment are concatenated, without an index or some kind of list (there are approaches based on file type validators that can in at least some cases differentiate between spurious and *valid* blocks, but that's beside the point).

But with a SBX file it's a different story. Each one of its block can't be fragmented more, and contains all the needed data to be put in its proper place in sequence. So let's proceed with the recovery of the SBX files.
To spice things up, the disk image file is run trough a scrambler, that swaps variable sized blocks of sectors around. The resulting layout is now this:

![Scrambled](http://i.imgur.com/jmOWult.png)

Pretty nightmarish! Now on to SBXScan to search for pieces of SBX files around, and SBXReco to get a report of the collected data:

```
C:\t\recovered\sbx>sbxscan \t\scrambled.IMA
creating 'sbxscan.db3' database...
scanning file/device '\t\scrambled.IMA' (1/1)...
100.0% blocks: 1087 - meta: 2 - files: 2 - 89.97MB/s
scan completed!

C:\t\recovered\sbx>sbxreco sbxscan.db3 -i
opening 'sbxscan.db3' recovery info database...

"UID", "filesize", "sbxname", "filename"
"2818b123c00b", 206292, "Castle.jpg.sbx", "Castle.jpg"
"76fe4a49ebf2", 331774, "Lake.jpg.sbx", "Lake.jpg"
```

The 2 SBX container have been found, with all the metadata. So the original filesizes are also known, along with the names of the SBX files and the original ones. At this point it would be possible to recover singles files or a group of them, by UID or names, but we opt to recover everything:

```
C:\t\recovered\sbx>sbxreco sbxscan.db3 --all
opening 'sbxscan.db3' recovery info database...
recovering SBX files...
UID 2818b123c00b (1/2)
  blocks: 417 - size: 213504 bytes
  to: 'Castle.jpg.sbx'
  100.0%   (missing blocks: 0)
UID 76fe4a49ebf2 (2/2)
  blocks: 670 - size: 343040 bytes
  to: 'Lake.jpg.sbx'
  100.0%   (missing blocks: 0)

done.
all SBx files recovered with no errors!
```

All SBX files seems to have been recovered correctly. We start decoding:

```
C:\t\recovered\sbx>sbxdec Lake.jpg.sbx
decoding 'Lake.jpg.sbx'...
metadata block found!
creating file 'Lake.jpg'...
SBX decoding complete
SHA256 3cfc376b6362444d2d25ebedb19e7594000f2ce2bdbb521d98f6c59b5adebfdc
hash match!
```

And sure enough:

![Castle](http://i.imgur.com/Qf0qrUp.jpg) ![Lake](http://i.imgur.com/9rH6tMf.jpg)

N.B. Here's a [7-Zip archive](http://mark0.net/download/sbxdemo-diskimages.7z) with the 2 disk images used in the demo (542KB).

## Possible / hypothetical / ideal uses cases
 - **Last step of a backup**. After creating a compressed archive of something, the archive could be SeqBox encoded to increase recovery chances in the event of some software/hardware issues that cause logic / file system's damages.
 - **Exchange data between different systems**. Regardless of the file system used, an SBX container can always be read/extracted.
 - **Long term storage**. Since each block is CRC tagged, and a crypto-hash of the original content is stored, bitrot can be easily detected. In addition, if multiple copies are stored, in the same or different media, the container can be correctly restored with high degree of probability even if all the copies are subject to some damages (in different blocks).  
 - **Encoding of photos on a SDCard**. Loss of images on perfectly functioning SDCards are known occurrences in the photography world, for example when low on battery and maybe with a camera/firmware with suboptimal monitoring & management strategies. If the photo files are fragmented, recovery tools can usually help only to a point. 
 - **On-disk format for a File System**. The trade-off in file size and performance (both should be fairly minimal anyway) could be interesting for some application. Maybe it could be a simple option (like compression in many FS). I plan to build a simple/toy FS with FUSE to test the concept, time permitting.
 - **Easy file splitting**. Probably less interesting, but a SeqBox container can also be splitted with no particular precautions aside from doing that on block size boundaries. Additionally, there's no need to use special naming conventions, numbering files, etc., as the SBX container can be reassembled exactly like when doing a recovery. 
 - **Data hiding**. SeqBox containers (or even fragments of them) can be put inside other files (for example at the end of a JPEG, in the middle of a document, etc.), sprayed somewhere in the unused space, between partitions, and so on. 
Incidentally, that means that if you are in the digital forensics sector, now you have one more thing to check for!
If a password is used, the entire SBX file is *mangled* to look pseudo-random, and SBXScan, SBXReco & SBXDec will not be able to recognize it unless the same password is provided.

## Tests

SeqBox recoverability have been practically tested with a number of File Systems. The procedure involved using a Virtual Machine (or a full blown emulator) to format a small disk image with a certain FS, filling it with a number of small files, then deleting some of them randomly to free enough space to copy a series of SBX files. This way every SBX file results fragmented in a lot of smaller pieces. Then the image was quick-formatted, wipefs-ed and the VM shutdown.
After that, from the host OS, recovery of the SBX files was attempted using SBXScan & SBXReco on the disk image.  

- **Working**: [ADFS](https://en.wikipedia.org/wiki/Advanced_Disc_Filing_System), [AFFS](https://en.wikipedia.org/wiki/Amiga_Fast_File_System), [APFS](https://en.wikipedia.org/wiki/Apple_File_System), [BeFS](https://en.wikipedia.org/wiki/Be_File_System), [BtrFS](https://en.wikipedia.org/wiki/Btrfs), [EXT2/3/4](https://en.wikipedia.org/wiki/Extended_file_system), [F2FS](https://en.wikipedia.org/wiki/F2FS), [FATnn/VFAT/exFAT](https://en.wikipedia.org/wiki/File_Allocation_Table), [HAMMER](https://en.wikipedia.org/wiki/HAMMER), [HFS](https://en.wikipedia.org/wiki/Hierarchical_File_System), [HFS+](https://en.wikipedia.org/wiki/HFS_Plus), [HPFS](https://en.wikipedia.org/wiki/High_Performance_File_System), [JFS](https://en.wikipedia.org/wiki/JFS_(file_system)), [MFS](https://en.wikipedia.org/wiki/Macintosh_File_System), [MINIX FS](https://en.wikipedia.org/wiki/MINIX_file_system), [NTFS](https://en.wikipedia.org/wiki/NTFS), [ProDOS](https://en.wikipedia.org/wiki/Apple_ProDOS), [ReFS](https://en.wikipedia.org/wiki/ReFS), [ReiserFS](https://en.wikipedia.org/wiki/ReiserFS), [UFS](https://en.wikipedia.org/wiki/Unix_File_System), [XFS](https://en.wikipedia.org/wiki/XFS), [ZFS](https://en.wikipedia.org/wiki/ZFS).

- **Not working**: [OFS](https://en.wikipedia.org/wiki/Amiga_Old_File_System) (due to 488 data bytes per 512 bytes sector)


**N.B.** Obviously SBX blocks can't be found if File System encryption is used. Compression too (mostly, but not always). Striping/RAID instead is usually not a problem. 

Being written in Python 3, SeqBox tools are naturally multi-platform and have been tested successfully on various versions of Windows, on OS X & macOS, on some Linux distros either on x86 or ARM, on FreeBSD and on Android (via QPython).   

***

## Tech spec
Byte order: Big Endian
### Common blocks header:

| pos | to pos | size | desc                                |
|---- | ---    | ---- | ----------------------------------- |
|  0  |      2 |   3  | Recoverable Block signature = 'SBx' |
|  3  |      3 |   1  | Version byte |
|  4  |      5 |   2  | CRC-16-CCITT of the rest of the block (Version is used as starting value) |
|  6  |     11 |   6  | file UID                            |
| 12  |     15 |   4  | Block sequence number               |

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

### Versions:
N.B. Current versions differs only by blocksize.

| ver | blocksize | note    |
|---- | --------- | ------- |
|  1  | 512       | default |
|  2  | 128       |         |
|  3  | 4096      |         |

### Metadata encoding:

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
| FDT | date & time (8 bytes, seconds since epoch) |
| SDT | sbx date & time (8 bytes) |
| HSH | crypto hash (SHA256, using [Multihash](http://multiformats.io) protocol) |
| PID | parent UID (*not used at the moment*)|

(others IDs for file dates, attributes, etc. will be added...)

## Final notes
The code was quickly hacked together in spare slices of time to verify the basic idea, so it's not optimized for speed and will benefit for some refactoring, in time.
Still, the current block format is stable and some precautions have been taken to ensure that any encoded file could be correctly decoded. For example, the SHA256 hash that is stored as metadata is calculated before any other file operation.
So, as long as a newly created SBX file is checked as OK with SBXDec, it should be OK.
Also, SBXEnc and SBXDec by default don't overwrite files, and SBXReco uniquify the recovered ones.
Finally, the file content is not altered in any way (except if a password is used), just re-framed.

## Related tools

Check my [BlockHashLoc](https://github.com/MarcoPon/BlockHashLoc) for a different/sinergic approach to obtaining a similar degree of recoverability, but using a parallel, small hashes file instead of a standalone container. It's probably more suited to protect existing files, when it isn't practical to touch/re-encode them.

## Links

 - [SeqBox home page](http://mark0.net/soft-seqbox-e.html)
 - [SeqBox GitHub repository](https://github.com/MarcoPon/SeqBox)

## Contacts

If you need more info, want to get in touch, or donate: [Marco Pontello](http://mark0.net/contacts-e.html)

**Bitcoin**: 1Mark1tF6QGj112F5d3fQALGf41YfzXEK3

![Qr-Code](http://mark0.net/images/qrcode.png) 