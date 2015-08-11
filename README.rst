=======================
makeself_safeextract.py
=======================

A simple script to unpack makeself-generated self-extractors without running
the possibly untrusted shell script.

It works by parsing shell script and, so far, it's only been tested on one of
GOG.com's new MojoSetup installers, so please do report issues so I can fix any
cases where it fails.

Dependencies
============

1. Python 2.x (I didn't have time to reconcile the need to get byte offsets
   with the need for Unicode strings in Python 3.x's shlex.)

Ideas
=====

1. Rather than parsing shell script, scan through the file looking for gzip,
   zip, etc. headers. (Incrementally so that, once an archive is identified,
   it can be parsed and the region its headers describe excluded from
   consideration to prevent false positives.)
