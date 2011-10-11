#! /usr/bin/env python
#
from __future__ import with_statement
import sys, os, re, optparse, pdb

from lsstdistrib.release import Release

prog = os.path.basename(sys.argv[0])
if prog.endswith(".py"):
    prog = prog[:-3]

usage = "%(prog)s [ -h ] [ -vs ] -d DIR manifest ..."
description = \
"""Copy new manifest files into the manifests directory.  
"""

log = sys.stderr

defaultServerRoot=None

def main():
    cl = setopts()
    (opts, args) = cl.parse_args()

    if not opts.serverdir:
        fail("-d option missing from arguments", 2)
    if not os.path.isdir(opts.serverdir):
        fail("server root given with -d is not an existing directory:\n" + 
             opts.serverdir, 2)
    if len(args) < 1:
        fail("no manifests specified", 2)

    global log
    if opts.silent:
        log = None

    manifests = []
    for arg in args:
        manifests.append(Release.parseProductManifestPath(arg))

    releaser = Release(manifests, opts.serverdir, log)
    failed = releaser.releaseAll(opts.overwrite, opts.atomic)


def setopts():
    parser = optparse.OptionParser(prog=prog, usage=usage, 
                                   description=description)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      default=0, help="print extra messages")
    parser.add_option("-s", "--silent", action="store_true", dest="silent",
                      default=False, help="suppress all output")
    parser.add_option("-d", "--server-dir", action="store", dest="serverdir",
                      metavar="DIR", default=defaultServerRoot,
                      help="the root directory of the distribution server")
    parser.add_option("-a", "--atomic", action="store_true", dest="atomic", 
                      default=False,
                      help="roll back any successfully copied manifests upon" + 
                      " eror")
    parser.add_option("-o", "--overwrite", action="store_true", dest="overwrite",
                      default=False,
                      help="roll back any successfully copied manifests upon" + 
                      " eror")

    return parser

def fail(msg, exitcode=1):
    raise FatalError(msg, exitcode)

class FatalError(Exception):
    def __init__(self, msg, exitcode):
        Exception.__init__(self, msg)
        self.exitcode = exitcode


if __name__ == "__main__":
    try:
        main()
    except FatalError, ex:
        if log:
            print >> log, "%s: %s" % (prog, str(ex))
        sys.exit(ex.exitcode)

