#! /usr/bin/env python
#
import os, sys, optparse
from lsstdistrib.manifest import Manifest
from lsstdistrib.tags import TagDef

def options():
    usage="%prog [ -t ] -d DIR manifest [ tagfile ]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--server-directory", dest="sdir", action="store",
                      help="the root directory for the server")
    parser.add_option("-t", "--tag", dest="tag", action="store",
                      default="current",
                      help="the tag whose definitions we should adjust to")

    return parser.parse_args()

def main():
    (opts, args) = options()

    if len(args) < 1:
        raise RuntimeError("Missing manifest and tag file names")
    if not opts.sdir:
        raise RuntimeError("Missing server directory")
    sdir = opts.sdir
    mdir = os.path.join(sdir, "manifests")
    
    inman = Manifest.fromFile(args[0])
    prodname = inman.name
    version = inman.vers

    if len(args) > 1:
        tagfile = args[1]
    elif opts.tag:
        tagfile = os.path.join(sdir, "%s.list" % opts.tag)
    else:
        raise RuntimeError("No tag or tagfile specified")
    tagged = TagDef(tagfile)
    
    deps = inman.getDeps()
    adjusted = []
    depnames = set()
    # iterate backwards
    for i in range(-1, -1*len(deps)-1, -1):
        dep = deps[i]
        if dep.data[dep.NAME] not in depnames:
            if dep.data[dep.NAME] == prodname:
                adjusted.insert(0, dep)
            else:
                depver = tagged.getVersion(dep.data[dep.NAME])
                if depver:
                    mfile = os.path.join(mdir, "%s-%s.manifest" %
                                         (dep.data[dep.NAME],
                                          dep.data[dep.VERSION]))
                if not depver or not os.path.exists(mfile):
                    adjusted.insert(0, dep)
                else:
                    adeps = Manifest.fromFile(mfile).getDeps()
                    for j in range(-1, -1*len(adeps)-1, -1):
                        adep = adeps[j]
                        if adep.data[adep.NAME] not in depnames:
                            adjusted.insert(0, adep)
                            depnames.add(adep.data[adep.NAME])
            depnames.add(dep.data[dep.NAME])
        else:
            p = map(lambda p1: p1[0],
                    filter(lambda i: i[1].data[0] == dep.data[dep.NAME],
                           enumerate(adjusted)))
            if len(p) > 1:
                raise RuntimeError("corrupted dep list: too many entries for product " + dep.data[dep.NAME])
            if len(p) == 0:
                raise RuntimeError("corrupted dep list: missing entry for product " + dep.data[dep.NAME])
            adjusted.insert(0, adjusted.pop(p[0]))

    outman = Manifest(prodname, version)
    for dep in adjusted:
        outman.addRecord(*dep.data)

    outman.write(sys.stdout)

if __name__ == "__main__":
    main()


