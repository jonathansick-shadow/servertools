#! /usr/bin/env python
#
import os, sys, optparse, re
from lsstdistrib.manifest import Manifest
from lsstdistrib.tags import TagDef

extRe = re.compile(r"([\+\-])(\d+)$")
textRe = re.compile(r"([\+\-])(\d+)")

def options():
    usage="%prog [ -t TAG ] -d DIR manifest [ tagfile ]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--server-directory", dest="sdir", action="store",
                      metavar="DIR", help="the root directory for the server")
    parser.add_option("-t", "--tag", dest="tag", action="store",
                      default="current",
                      help="the tag whose definitions we should adjust to")
    parser.add_option("-b", "--build-number", dest='bnum', action="store",
                      metavar="NUM",
                     help="update build number for the primary product to NUM")

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
                # dep.data[dep.FLAVOR] = "generic"

                if opts.bnum:
                    if extRe.search(dep.data[dep.VERSION]):
                      dep.data[dep.VERSION] = extRe.sub(r"\g<1>%s" % opts.bnum,
                                                        dep.data[dep.VERSION])
                      dep.data[dep.INSTALLDIR] = extRe.sub(r"\g<1>%s" % opts.bnum,
                                                     dep.data[dep.INSTALLDIR])
                    else:
                        dep.data[dep.VERSION]    += "+%s" % opts.bnum
                        dep.data[dep.INSTALLDIR] += "+%s" % opts.bnum
                        
                adjusted.insert(0, dep)
            else:
                depver = tagged.getVersion(dep.data[dep.NAME])
                if depver:
                    mfile = os.path.join(mdir, "%s-%s.manifest" %
                                         (dep.data[dep.NAME], depver))
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

    if opts.bnum:
        version = textRe.sub(r"\g<1>%s" % opts.bnum, version)
    outman = Manifest(prodname, version)
    for dep in adjusted:
        outman.addRecord(*dep.data)

    outman.write(sys.stdout)

if __name__ == "__main__":
    main()


