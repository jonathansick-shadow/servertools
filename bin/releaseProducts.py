#! /usr/bin/env python
#
from __future__ import with_statement
import sys
import os
import re
import optparse
import shutil

defaultBaseDir = "/lsst/DC3/distrib/w12"

opts = None
builddir = None
fulllog = None
serverdir = None

from lsstdistrib.release import UpdateDependents, UprevProduct
from lsstdistrib.manifest import BuildDependencies, SortProducts, Manifest, DeployedManifests
from lsstdistrib import version as onvers
from lsstdistrib.tags import TagDef

prog = os.path.basename(sys.argv[0])
if prog.endswith(".py"):
    prog = prog[:-3]

usage = "%prog [ -h ] -b DIR [-r DIR -l DIR] [-j NUM -t TAG -T TAG -f] product/version ..."
description = \
    """
Test and release one or more products, up-reving their dependent packages automatically
as necessary and desired.
"""


def setopts():
    parser = optparse.OptionParser(prog=prog, usage=usage,
                                   description=description)
    parser.add_option("-b", "--distrib-base-dir", action="store", dest="basedir",
                      metavar="DIR", default=defaultBaseDir,
                      help="the root directory of the distribution server")
    parser.add_option("-r", "--ref-stack-dir", action="store", dest="refstack",
                      metavar="DIR",
                      help="the root directory of the distribution server")
    parser.add_option("-l", "--log-dir", action="store", dest="logdir",
                      metavar="DIR",
                      help="the directory where to write logs")
    parser.add_option("-T", "--reference-tag", action="store", dest="reftag",
                      metavar="TAG", default="current",
                      help="use the given tag as a guide for choosing dependency versions")
    parser.add_option("-t", "--tag", action="store", dest="tagas",
                      metavar="TAG",
                      help="assign any newly deployed versions the given tag")
    parser.add_option("-j", "--thread-count", action="store", dest="threadCount",
                      metavar="TAG", default=4, type="int",
                      help="use the given tag as a guide for choosing dependency versions")
    parser.add_option("-f", "--full-uprev", action="store_true", dest="fulluprev",
                      default=False,
                      help="up-rev all dependents of given products, not just those necessary for releasing the specified products")

    return parser


def main():
    global opts
    global builddir
    global serverdir
    global fulllog

    cl = setopts()
    (opts, args) = cl.parse_args()

    if not opts.basedir:
        fail("Need a base directory; use -b")
    if not opts.refstack:
        opts.refstack = os.path.join(opts.basedir, "ref")
    if not os.path.exists(opts.refstack):
        fail("Reference stack not found: " + opts.refstack)
    builddir = os.path.join(opts.basedir, "build")
    if not os.path.exists(builddir):
        fail("Build directory not found: " + builddir)
    serverdir = os.path.join(opts.basedir, "www")
    if not os.path.exists(serverdir):
        fail("Build directory not found: " + serverdir)
    if not opts.logdir:
        opts.logdir = builddir
    if not os.path.exists(opts.logdir):
        fail("Log directory not found: " + opts.logdir)

    global fulllog
    fulllog = os.path.join(opts.logdir, "releaseProducts-%d.log" % os.getpid())

    products = map(lambda p: p.split('/', 1), args)
    bad = filter(lambda p: len(p) < 2, products)
    if len(bad) > 0:
        fail("Bad products syntax: version is missing.", 1)

    # put requested products in dependency order
    products = sortProducts(products)

    deployed = DeployedManifests(os.path.join(serverdir, "manifests"))
    uprevdata = BuildDependencies(serverdir, deployed)
    uprevver = UprevProduct(serverdir, uprevdata, deployed)
    dependents = lookupDependents(deployed, products)

    # iterate through products
    for i in xrange(products):
        prodname, version = products[i]

        # validate the release of this product
        runValidateRelease(prodname, version)

        # update our uprev data used for making uprev manifests
        manifest = deployed.getManifest(prodname, version)
        uprevdata.mergeManifest(manifest)

        # determine the intermediate dependents we need to uprev
        uprevdeps = getUprevSet(prodname, dependents)

        # up-rev the intermediates needed for next products
        for prod in uprevdeps:
            nmanfile = uprevver.uprev(prod[0], prod[1])
            deployManifest(nmanfile)

        # remove lists for this product for next time
        del dependents[prodname]


def deployManifest(manifestfile):
    # copy the as-yet unreleased manifest file and to the manifests directory,
    # sync it to the real server, and install its product
    global fulllog
    global opts
    global serverdir

    cmd = "releaseAndInstall.sh -d %s " % serverdir
    if opts.tag:
        cmd += "-t %s " % opts.tag
    cmd += manifestfile

    with open(fulllog, 'a') as fd:
        print >> fd, cmd

    notok = os.system(cmd)
    if notok:
        raise RuntimeError("Detected failure from releaseAndInstall (%d)" %
                           notok)


def sortProducts(products):
    global serverdir
    global opts
    sorter = SortProducts(serverdir, products)
    if opts.reftag:
        sorter.preferTag(opts.reftag)
    return sorter.sort()


def lookupDependents(deployed, products):
    global serverdir
    global opts

    tagged = None
    if opts.reftag:
        tagged = tags.TagDef(serverdir, opts.reftag)

    out = {}  # dependendents
    for prod in products:
        version = None
        if tagged:
            version = opts.reftag.getVersion(prod[0])
        if not version:
            version = deployed.getLatestVersion(prod[0])

        if not version:
            out[prod[0]] = []
        else:
            out[prod[0]] = deployed.dependsOn(prod[0], version)

    return out


def getUprevSet(fromprod, dependents):
    # figure out the set we'll uprev between fromprod and any other product(s)
    # start with the dependents of fromprod
    prods = map(lambda d: d[0], dependents[fromprod])

    # eliminate products that are dependents of any other products
    for other in depenedents.keys():
        if other == fromprod:
            continue
        deps = map(lambda d: d[0], dependendents[other]) + [other]
        prods = filter(lambda p: p not in deps, prods)

    # return an ordered list
    out = filter(lambda d: d[0] in prods, dependents[fromprod])
    return out


def runValidateRelease(prodname, version):
    global fulllog
    global opts

    cmd = "validateRelease.sh -p -b %s -r %s -j %d" % \
          (opts.basedir, opts.refstack, opts.threadCount)
    if opts.tagas:
        cmd += "-t %s " % opts.tagas
    cmd += "%s %s complete" % (prodname, version)

    with open(fulllog, 'a') as fd:
        fd.write("\n")
        print >> fd, "Validating and deploying", prodname, version
        print >> fd, cmd
        fd.write("\n")

    cmd += " | tee -a %s" % fulllog

    notok = os.system(cmd)
    if notok:
        raise RuntimeError("Detected failure from validateRelease (%d)" % notok)


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


