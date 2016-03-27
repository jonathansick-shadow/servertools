#! /usr/bin/env python
#
from __future__ import with_statement
from __future__ import absolute_import
import sys
import os
import re
import optparse

from lsstdistrib.tags import TagDef
from lsstdistrib.manifest import Manifest
from lsstdistrib import version as onvers

prog = os.path.basename(sys.argv[0])
if prog.endswith(".py"):
    prog = prog[:-3]

usage = "%prog [ -h ] [ -b DIR -t tag -T tag] [ -iD ] product  ..."
description = \
    """Create a new manifest file for a product given updates to its dependencies.
"""

defaultServerRoot = None
buildExtRe = re.compile(r'([\+\-])(\d+)$')


def setopts():
    parser = optparse.OptionParser(prog=prog, usage=usage,
                                   description=description)
    parser.add_option("-b", "--base-dir", action="store", dest="stackbase",
                      metavar="DIR",
                      help="the root directory of the distribution server")
    parser.add_option("-s", "--server-dir", action="store", dest="serverdir",
                      metavar="DIR",
                      help="the root directory of the distribution server")
    parser.add_option("-r", "--reference-dir", action="store", dest="refstack",
                      metavar="DIR",
                      help="the root directory of the reference stack")
    parser.add_option("-t", "--tag", action="store", dest="tag",
                      metavar="TAG",
                      help="when deploying, tag the release with the given tag name")
    parser.add_option("-T", "--reference-tag", action="store", dest="reftag",
                      metavar="TAG", default="current",
                      help="use the given tag a guide for choosing dependency versions")
    parser.add_option("-u", "--use-file", action="store", dest="usefile",
                      metavar="FILE",
                      help="load a list of products to up-rev against from the given file")
    parser.add_option("-U", "--use-stdin", action="store_true",
                      dest="usestdin",
                      help="load a list of products to up-rev against from standard input")

    return parser


def main():
    cl = setopts()
    (opts, args) = cl.parse_args()

    if not opts.refstack or not opts.serverdir:
        if not opts.stackbase:
            fail("-b option missing from arguments", 2)
            if not os.path.isdir(opts.stackbase):
                fail("distrib root given with -b is not an existing directory:\n" +
                     opts.stackbase, 2)
    if not opts.refstack:
        opts.refstack = os.path.join(opts.stackbase, "ref")
    if not opts.serverdir:
        opts.serverdir = os.path.join(opts.serverdir, "www")
    if not os.path.isdir(opts.serverdir):
        fail("server dir does not exist as a directory: " + opts.serverdir)
    if not os.path.isdir(opts.refstack):
        fail("reference stack dir does not exist as a directory: " +
             opts.refstack)

    # read in list of products to base up-reved manifest on
    useprods = {}
    if opts.usestdin and opts.usefile:
        warn("both -u and -U given; reading both file and standard in")
    if opts.usefile:
        uf = open(opts.usefile)
        useprods.update(loadProductList(uf))
    if opts.usestdin:
        useprods.update(loadProductList(sys.stdin))

    # open up our reference tag file
    reftagfile = os.path.join(opts.serverdir, "%s.list" % opts.reftag)
    reftags = TagDef(reftagfile)

    # use a previous manifest of our product as the template for the up-reved
    # one
    prodname = args[0]
    manifest = getBestManifest(prodname, useprods, reftags)

    # update the manifest accordingly


def loadProductList(strm):
    out = {}
    for line in strm:
        for prod in line.strip().split():
            prodver = parseProduct(prod)
            out[prodver[0]] = prodver[1]
    return out


def parseProduct(prodver):
    parts = prodver.split('/', 1)
    if len(parts) < 2:
        parts.append(None)
    return parts


def getBestManifest(prodname, useprods, reftags):
    manfile = None
    if prodname in useprods:
        # instructed to use a specific version
        ver = useprods[prodname]

        # look for a deployed version
        manfile = os.path.join(opts.serverdir, "manifests",
                               "%s-%s.manifest" % (prodname, ver))
        if not os.path.exists(manfile):
            manfile = getUndeployedManifestFile(prodname, ver)

    if not manfile or not os.path.exists(manfile):
        # consult the tag file
        ver = reftags.getVersion(prodname)
        manfile = os.path.join(opts.serverdir, "manifests",
                               "%s-%s.manifest" % (prodname, ver))

    if not os.path.exists(manfile):
        manfile = getUndeployedManifestFile(prodname, ver)
    if not os.path.exists(manfile):
        raise RuntimeError("Can't find a manifest file for %s %s" %
                           (prodname, ver))

    return Manifest.fromFile(manfile)


def getUndeployedManifestFile(prodname, version):
    manfile = None
    mat = buildExtRe.search(ver)
    if mat and mat.group(1) == '+':
        bn = mat.group(2)
        version = buildExtRe.sub('', version)
        manfile = os.path.join(opts.serverdir, prodname, version,
                               "b%s.manifest" % bn)
    return manfile


def warn(msg):
    print >> sys.stderr, msg


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

