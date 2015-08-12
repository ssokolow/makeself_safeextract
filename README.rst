=======================
makeself_safeextract.py
=======================

A simple script to unpack makeself-generated self-extractors without running
the possibly untrusted shell script.

It works by parsing shell script and, so far, it's only been tested on a couple
of GOG.com's new MojoSetup installers, so please do report issues so I can fix
any cases where it fails.

Dependencies
============

1. Python 2.x (I didn't have time to reconcile the need to get byte offsets
   with the need for Unicode strings in Python 3.x's shlex.)

Will also use p7zip or unzip in preference to Python's built-in zipfile module
if present.

Usage
=====

``makeself_safeextract.py [--mojo] <archive path> ...``

The ``--mojo`` flag will instruct it to assume that it's dealing with a
MojoSetup installer and:

1. Only unpack the data ``.zip``.
2. Decompress and then delete the Zip file.

See the ``--help`` output for more advanced usage.

(And see lgog_grab.sh for a proof-of-concept wrapper script using this.)

TODO
====

1. Use header detection to give the extracted files extensions rather than
   just assuming that makeself used gzip to compress its tarball and that
   any "cruft" following the makeself-expected content is either a Zip file
   or unknown binary data.

Ideas
=====

1. Rather than parsing shell script, scan through the file looking for gzip,
   zip, etc. headers. (Incrementally so that, once an archive is identified,
   it can be parsed and the region its headers describe excluded from
   consideration to prevent false positives.)
