This rtp packetizer script was developed for my master thesis in advanced media technology.

It's purpose is to investigate the possiblity of creating uncompressed video streams entirely in software.
The script creates a binary file that contains packets with a length of 1400 bytes. A corresponding streaming program can load each packet and send it via UDP.
The packets follow SMPTE ST 2110-20 and RFC 4175.