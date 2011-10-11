#! /usr/bin/env python
#
from __future__ import with_statement
import sys, os, re, optparse

from lsstdistrib.release import UpdateDependents

prog = os.path.basename(sys.argv[0])
if prog.endswith(".py"):
    prog = prog[:-3]

usage = "%(prog)s [ -h ] [ -vs ] -d DIR product ..."
description = \
"""Create new manifest files for all dependents of the given products, up-reving them
to use this products.  Normally, the products that are specified have been recently
released.  
"""

log = sys.stderr

def main():
    cl = setopts()
    (opts, args) = cl.parse_args()

    if not opts.serverdir:
        fail("-d option missing from arguments", 2)
    if not os.path.isdir(opts.serverdir):
        fail("server root given with -d is not an existing directory:\n" + 
             opts.serverdir, 2)
    if len(args) < 1:
        fail("no products specified", 2)

    if opts.silent:
        log = None

    products = []
    for arg in args:
        products.append(parseProduct(arg))

    uprev = UpdateDependents(products, opts.serverdir)
    updated = uprev.createManifests()

    if not opts.silent:
        for prod in updated:
            filepath = prod[3]
            if filepath.startswith(opts.serverdir + '/'):
                filepath = filepath[len(opts.serverdir)+1:]
            print filepath

def parseProduct(prodpath):
    fields = prodpath.split('/')
    if len(fields) < 2:
        raise Runtime("bad product name syntax: " + prodpath)
    out = fields[-2:]
    isext = len(fields) > 2 and fields[-3] == 'external'
    out.append(isext)
        
    return out

def setopts():
    parser = optparse.OptionParser(prog=prog, usage=usage, 
                                   description=description)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      default=0, help="print extra messages")
    parser.add_option("-s", "--silent", action="store_true", dest="silent",
                      default=False, help="suppress all output")
    parser.add_option("-d", "--server-dir", action="store", dest="serverdir",
                      metavar="DIR", 
                      help="the root directory of the distribution server")

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


        
