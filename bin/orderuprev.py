#! /usr/bin/env python
#
from __future__ import with_statement
import sys, os, re, optparse

from lsstdistrib.manifest import BuildDependencies, DeployedManifests, DeployedProductNotFound, Manifest

prog = os.path.basename(sys.argv[0])
if prog.endswith(".py"):
    prog = prog[:-3]

usage = "%prog [ -h ] [ -p ] -d DIR product ..."
description = \
"""
Create a dependency-ordered list of packages that will need to be up-reved
as a result of a simultaneous release of a given set of products.  
"""

def setOptions():
    parser = optparse.OptionParser(prog=prog, usage=usage, 
                                   description=description)
    parser.add_option("-p", "--prog-format", action="store_true",
                      dest="progformat", default=False, 
                      help="use product/version format for scripting purposes")
    parser.add_option("-a", "--all-dependents", action="store_true",
                      dest="alldeps", default=False, 
                      help="list all dependents rather than just intermediate ones needed for testing requested packages")
    parser.add_option("-d", "--server-dir", action="store", dest="serverdir",
                      metavar="DIR", 
                      help="the root directory of the distribution server")
    return parser

def main():
    cl = setOptions()
    (opts, args) = cl.parse_args()

    bdeps = BuildDependencies(opts.serverdir)
    deployed = DeployedManifests(bdeps.mDir)

    requested = {}
    for prod in args:
        parts = prod.split('/', 1)
        prodname = parts.pop(0)
        version = ((len(parts) > 0) and parts[0]) or None
        requested[prodname] = version

        try:
            bdeps.mergeProduct(prodname, version)
        except DeployedProductNotFound:
            try:
                bdeps.mergeProduct(prodname)
            except DeployedProductNotFound:
                man = Manifest(prodname, version)
                man.addSelfRecord()
                bdeps.mergeFromManifest(man)

    deps = bdeps.getDeps()

    # now trim down the dependencies starting with the dependencies of
    # the "earliest" specified product
    for i in xrange(len(deps)):
        dep = deps[0]
        if requested.has_key(dep.data[dep.NAME]):
            break
        deps.pop(0)

    # remove any dependency that is not also a dependent
    dependents = set()
    last = deps[-1]
    for prodname, version in requested.items():
        if prodname == last.data[last.NAME]:
            continue
        if not os.path.exists(bdeps.manifestFile(prodname, version)):
            version = None
        itsdependents = map(lambda p: p[0],
                            deployed.dependsOn(prodname, version))
        dependents = dependents.union(itsdependents)
    deps = filter(lambda d: d.data[d.NAME] in requested.keys() or
                            d.data[d.NAME] in dependents,
                  deps)

    # print what we have:
    delim = (opts.progformat and '/') or " "
    for dep in deps:
        print "%s%s%s" % (dep.data[dep.NAME], delim, dep.data[dep.VERSION])

    # finally append the dependents for the last product
    if opts.alldeps:
        for pv in deployed.dependsOn(last.data[last.NAME],
                                     last.data[last.VERSION]):
            if pv[0] == last.data[last.NAME]:
                continue
            print "%s%s%s" % (pv[0], delim, pv[1])

    return 0


if __name__ == "__main__":
    sys.exit(main())

        
