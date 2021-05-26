#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""A simple script to extract makeself-based self-extracting archives
(eg. MojoSetup installers) without running untrusted code.

NOTE: Extracted tarballs may still contain absolute or ancestor relative paths.
Use appropriate flags when extracting if you don't trust the file's source.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__authors__ = [
    "Stephan Sokolow (deitarion/SSokolow)",
    "Thiago Jung Bauermann",
]
__author__ = ', '.join(__authors__)
__appname__ = "[application name here]"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import logging, os, shlex, subprocess, zipfile
log = logging.getLogger(__name__)

# -- Code Here --

def accum_find(lexer, target, stop_token=None, limit=None):
    """Walk the lexer forward until we find the given string."""
    target_str = b''.join(target)
    target_remaining, accum = [], b''

    for token in lexer:
        # XXX: There might be cases like "---tar" but valid that break this.
        if target_remaining and token == target_remaining[0]:
            accum += token
            target_remaining.pop(0)
        elif token == target[0]:
            accum += token
            target_remaining = target[1:]
        else:
            target_remaining = target[:]
            accum = b''

        # We do this here so we don't pop the next token from the lexer
        if accum == target_str or token == stop_token:
            return accum

        # Avoid traversing too far into large makeself bundles
        if limit and lexer.lineno >= limit:
            return

def parse_int_list(lexer):
    """Parse a space-separated list of integers in a string after being lined
    up using accum_find."""
    return [int(x) for x in shlex.split(lexer.get_token())[0].split()]

def get_offsets(path):
    """Parse the shell portion of a makeself archive to find the offsets and
       lengths of the embedded tar archives.
    """

    # TODO: Figure out how to make this Python3 compatible
    with open(path, 'r') as fobj:
        lexer = shlex.shlex(fobj)

        # Cheap cop-out for parsing command substitutions
        lexer.quotes += '`'

        # Extract the list of filesizes for the first stage of makeself
        accum_find(lexer, [b'filesizes', b'='], limit=200)
        filesizes = parse_int_list(lexer)

        if not accum_find(lexer, [b'-', b'-', b'tar'], limit=1024):
            raise ValueError("Could not find definition of --tar")

        if not accum_find(lexer, [b'offset', b'='], stop_token=';;'):
            raise ValueError("Could not find offset definition")

        offset_cmd = shlex.split(lexer.get_token()[1:-1])
        expected = [b'head', b'-n', b'0', b'$0', b'|',
                    b'wc', b'-c', b'|',
                    b'tr', b'-d', b' ']

        skip_lines = expected[2] = offset_cmd[2]
        assert offset_cmd == expected, "\nExpected %r\nBut got  %r" % (
                expected, offset_cmd)

        # We'll rely on the default error message to say what we got
        skip_lines = int(skip_lines)

        fobj.seek(0)
        for _ in range(skip_lines):
            fobj.readline()

        offsets = []
        prev_offset = fobj.tell()
        for size in filesizes:
            offsets.append((prev_offset, size))
            prev_offset = offsets[-1][1]
        return offsets

def read_in_chunks(file_object, offset, size=None, chunk_size=1024*1024):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1 MiB. Based on code from:
    https://stackoverflow.com/questions/519633/lazy-method-for-reading-big-file-in-python
    """
    file_object.seek(offset)
    remaining = None if size is None else size

    while True:
        if remaining is None:
            this_chunk_size = chunk_size
        else:
            this_chunk_size = remaining if remaining < chunk_size else chunk_size
            remaining -= this_chunk_size

        data = file_object.read(this_chunk_size)
        if not data:
            break
        yield data

def write_to_file(in_fobj, out_path, offset, size=None):
    """Writes bytes size bytes starting at offset from in_fobj (file object) to file
       at out_path (string)"""
    with open(out_path, 'wb') as oobj:
        for chunk in read_in_chunks(in_fobj, offset, size):
            oobj.write(chunk)

def split_archive(path, offsets, target, mojo=False):
    """Given a list of offsets, extract data hunks from a makeself file."""
    with open(path, 'rb') as fobj:
        results = []
        hunk_num = 1
        end_offset = sum(offsets[-1])
        end_size = os.stat(path).st_size - end_offset

        if mojo:
            tgt_path = target
        else:
            for offset, size in offsets:
                log.info("Unpacking %s byte file at offset %s", size, offset)
                # TODO: Extract to a temporary path and header detect filetype
                tgt_path = os.path.join(target, '%s.tgz' % (hunk_num))
                results.append(tgt_path)
                write_to_file(fobj, tgt_path, offset, size)
                hunk_num += 1
            tgt_path = os.path.join(target, '%s.bin' % (hunk_num))

        if end_size:
            log.info("Found extra data after tarball (MojoSetup content?)")
            write_to_file(fobj, tgt_path, end_offset)
            if zipfile.is_zipfile(tgt_path):
                new_tgt = os.path.splitext(tgt_path)[0] + '.zip'
                os.rename(tgt_path, new_tgt)
                tgt_path = new_tgt
            results.append(tgt_path)

        return [results]

def main():
    """The main entry point, compatible with setuptools entry points."""
    from argparse import ArgumentParser
    parser = ArgumentParser(usage="%(prog)s [options] <argument> ...",
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_argument('--version', action='version',
            version="%%(prog)s v%s" % __version__)
    parser.add_argument('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_argument('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    parser.add_argument('-o', '--outdir', default=os.getcwd(),
        help="The target directory to unpack to")
    parser.add_argument('--mojo', action="store_true", default=False,
        help="Assume the file is a MojoSetup installer and call p7zip or "
        "unzip to unpack only the application data.")
    parser.add_argument('--no-containing-folder', action="store_true",
        default=False, help="Don't create a containing folder named after each"
        " source archive.")
    parser.add_argument('files', nargs='+')
    # Reminder: %(default)s can be used in help strings.

    args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose - args.quiet, len(log_levels) - 1)
    args.verbose = max(args.verbose, 0)
    logging.basicConfig(level=log_levels[args.verbose],
                        format='%(levelname)s: %(message)s')

    for path in args.files:
        offsets = get_offsets(path)
        target = args.outdir
        if not args.no_containing_folder:
            target = os.path.join(target, os.path.basename(
                os.path.splitext(path)[0]))

        if os.path.exists(target):
            raise Exception("Target path already exists: %s" % target)
        else:
            os.makedirs(target)

        if args.mojo:
            zippath = target + '.zip'
            split_archive(path, offsets, zippath, mojo=True)

            if not zipfile.is_zipfile(zippath):
                log.warning("Not a clean Zip file: %s", zippath)

            # Fallback chain to ensure the best possible chance of success
            # (7zip is most versatile, unzip is safer than pre-2.7.4 Python
            #  zipfile module in the presence of absolute content paths)
            try:
                subprocess.check_call(['7z', 'x', zippath], cwd=target)
            except OSError:
                try:
                    subprocess.check_call(['unzip', zippath], cwd=target)
                except OSError:
                    zobj = zipfile.ZipFile(zippath)
                    zobj.extractall(target)

            # If we didn't die with subprocess.CalledProcessError, or
            # zipfile.BadZipFile, remove the temporary zip file.
            os.remove(zippath)
        else:
            split_archive(path, offsets, target, mojo=False)

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
