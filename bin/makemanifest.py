#! /usr/bin/env python
#
from __future__ import with_statement
import sys, os, cStringIO, re, errno, optparse
from copy import copy

defaultManifestHeader = \
"""EUPS distribution manifest for %s (%s). Version 1.0
#
"""
headerLineMagic = r"EUPS distribution manifest"
headerLineRe = re.compile(r"%s for (\S.*) \((\S*\S)\). Version 1.0" % headerLineMagic)
spaceRe = re.compile(r"\s+")
commentRe = re.compile(r"\s*#")
directiveRe = re.compile(r"^\s*>(\S+)")
dmspkgs = "/lsst_ibrix/lsst/softstack/dmspkgs"
destpkgs = "/lsst_ibrix/lsst/softstack/pkgs/test/dc4"

defaultColumnNames = \
"pkg flavor version tablefile installation_directory installID".split()

class Manifest(object):
    """an in-memory representation of a package manifest."""

    def __init__(self, name, version, flavor="generic"):
        """create a manifest for a given package

        @param name     the name of the package this manifest is for
        @param version  the version of the package
        @param flavor   the name of the platform type supported by this
                          installation of the package
        """
        self.recs = {}
        self.keys = []
        self.name = name
        self.vers = version
        self.flav = flavor
        self.hdr = defaultManifestHeader
        self.colnames = copy(defaultColumnNames)
        self.colnames[0] = "# " + self.colnames[0]
        self.commcount = 0

    def getNameVerFlav(self):
        """return the package name, version, and flavor as a 3-tuple"""
        return (self.name, self.vers, self.flav)

    def addComment(self, comment):
        """append a comment to the manifest"""
        self.commcount += 1
        key = '#'+str(self.commcount)
        self.keys.append(key)
        self.recs[key] = [ '' ] * len(self.colnames)
        self.recs[key][-1] = comment

    def addRecord(self, pkgname, flavor, version,
                  tablefile, installdir, installid):
        """append a record to the manifest list.  This method does not
        prevent duplicate records.

        @param pkgname    the name of the package
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        @param tablefile  the name of the EUPS table file for this package
        @param installdir the directory (relative to $LSST_HOME) where
                             this package should be installed by default.
        @param installid  a complete handle for the deployment bundle.
        """
        key = ":".join([pkgname, flavor, version])
        if not self.recs.has_key(key):
            self.keys.append(key)
            self.recs[key] = [pkgname, flavor, version,
                              tablefile, installdir, installid]

    def addLSSTRecord(self, pkgname, version, pkgpath=None, build="1", 
                      flavor="generic", id="lsstbuild"):
        """append a standard build record for an LSST package.

        @param pkgname    the name of the package
        @param version    the version of the package
        @param pkgpath    if non-None, a path to be prepended to the standard
                             pkgname/version install directory (default:
                             None)
        @param flavor     the name of the platform type supported by this
                            installation of the package (default: "generic")
        @param id         the installid or abbreviation (default: "lsstbuild")
        """
        fpkgpath = "%s/%s" % (pkgname, version)
        if (pkgpath is not None and len(pkgpath) > 0):
            fpkgpath = "%s/%s" % (pkgpath, fpkgpath)
        ipkgpath = "%s+%s" % (fpkgpath, build)
        tablepath = os.path.join(fpkgpath, "%s.table" % pkgname)
        bversion = "%s+%s" % (version, build)

        self.addRecord(pkgname, flavor, bversion, tablepath, ipkgpath,
                       self.defaultID(id, pkgname, flavor, version, fpkgpath))
                       
    def addExtRecord(self, pkgname, version, pkgpath="external", 
                     build="1", flavor="generic", id="lsstbuild"):
        """append a standard build record for an LSST package

        @param pkgname    the name of the package
        @param version    the version of the package
        @param pkgpath    if non-None, a path to be prepended to the standard
                             pkgname/version install directory (default:
                             "external")
        @param flavor     the name of the platform type supported by this
                            installation of the package (default: "generic")
        @param id         the installid or abbreviateion (default: "pacman")
        """
        self.addLSSTRecord(pkgname, version, pkgpath, build, flavor, id)

    def addSelfRecord(self, pkgpath=None, build="1",
                      flavor="generic", id="lsstbuild"):
        """append a standard build record for the package that this
        manifest is for

        @param pkgpath    if non-None, a path to be prepended to the standard
                             pkgname/version install directory (default:
                             None)
        @param flavor     the name of the platform type supported by this
                            installation of the package (default: "generic")
        @param id         the installid or abbreviateion (default: "pacman")
        """
        self.addLSSTRecord(self.name, self.vers, pkgpath, build, flavor, id)

    def defaultID(self, id, pkgname, flavor, version, path):
        """create an installid from an abbreviation that is consistent
        with the package name and version.  If the input id is not
        recognized as an abbreviation, it is returned untransformed.

        Recognized ids include "lsstbuild", representing a standard LSST
        build script having the name of the form, "package.bld".  

        @param pkgname    the name of the package
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        @param id    either an id abbreviation or a full installid
        """
        if (id == 'lsstbuild' or id == 'tarball'):
            id = "lsstbuild:%s/%s-%s.tar.gz" % (path, pkgname, version)
        elif (id == 'bld'):
            id = "lsstbuild:%s/%s.bld" % (path, pkgname)
        return id

    def hasRecord(self, pkgname, flavor, version):
        """return true if this manifest has a record matching the
        package name, flavor, and version

        @param pkgname    the name of the package
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        """
        return self.recs.has_key(":".join([pkgname, flavor, version]))

    def hasProduct(self, pkgname):
        """return true if this manifest has a record matching the
        package name

        @param pkgname    the name of the package
        """
        return bool(filter(lambda k: k.startswith(pkgname+':'), self.keys))

    def recordToString(self, pkgname, flavor, version):
        """return the requested record in manifest format.
        @param pkgname    the name of the package
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        """
        if (not self.hasRecord(pkgname, flavor, version)):
            raise RuntimeError("record not found in manifest")
        return " ".join(self.recs(":".join([pkgname, flavor, version])))

    def __repr__(self):
        """return all lines of the manifest in proper manifest format"""
        out = cStringIO.StringIO()
        self.printRecord(out)
        return out.getvalue()

    def str(self):
        """return all lines of the manifest in proper manifest format"""
        return str(self)

    def printRecord(self, strm):
        """print the lines of the manifest to a give output stream.

        @param strm  the output stream to write the records to
        """
        collen = self._collen()
        fmt = "%%-%ds %%-%ds %%-%ds %%-%ds %%-%ds %%s\n" % tuple(collen[:-1])
        
        strm.write(self.hdr % (self.name, self.vers))
        strm.write((fmt % tuple(self.colnames)))
        strm.write("#" + " ".join(map(lambda x: '-' * x, collen))[1:79])
        strm.write("\n")

        for key in self.keys:
            if key.startswith('#'):
                strm.write("# %s\n" % self.recs[key][-1])
            else:
                strm.write(fmt % tuple(self.recs[key]))
            
    def _collen(self):
        x = self.recs.values()
        x.append(self.colnames)
        return map(lambda y: max(map(lambda x: len(x[y]), x)),
                   xrange(0,len(self.colnames)))
    
    def fromFile(filename, flavor="generic", product=None, version=None):
        """
        create a manifest from the contents of existing one
        """
        with open(filename) as fd:
            line = fd.readline()
            if line.startswith(headerLineMagic):
                mat = headerLineRe.search(line)
                if not mat and (not product or not version):
                    raise RuntimeError(filename+": Can't determine product/version due to bad opening line")
                if not product:
                    product = mat.group(1)
                if not version:
                    version = mat.group(2)
            if not product or not version:
                raise RuntimeError(filename+": Can't determine product/version due to missing header line")

            out = Manifest(product, version, flavor)

            for line in fd:
                if line.startswith('#'):
                    continue

                parts = spaceRe.split(line, len(defaultColumnNames))
                if len(parts) < 4:
                    continue
                if len(parts) < len(defaultColumnNames):
                    parts += [""] * (len(defaultColumnNames) - len(parts))
                out.addRecord(*parts[:len(defaultColumnNames)])

            return out

    fromFile = staticmethod(fromFile)

    def merge(self, other):
        """
        merge the dependencies in the given manifest in to this manifest
        """
        for key in other.keys:
            if not self.hasProduct(other.recs[key][0]):
                self.addRecord(*other.recs[key])

class Loader(object):

    def __init__(self, name, version, build="1", flavor="generic"):
        self.man = Manifest(name, version, flavor)
        self.build = build
        self.oldcurrent = Current(os.path.join(dmspkgs, "current.list"))
        self.newcurrent = Current(os.path.join(destpkgs, "current.list"))
        self.pkgPath = {}

    def fillFrom(self, themanifest, doself=True):
        with open(themanifest) as fd:
            for line in fd:
                if line.startswith(headerLineMagic) or commentRe.match(line):
                    continue
                if line.strip() == '':
                    continue
                mat = directiveRe.match(line)
                if mat:
                    directive = mat.group(1)
                    data = spaceRe.split(directiveRe.sub('', line).strip())
                    parms = {}
                    for item in data:
                        if not item:  continue
                        pair = item.split('=', 1)
                        if len(pair) < 2:
                            print >> sys.stderr, "bad directive syntax:", item
                            continue
                        parms[pair[0]] = pair[1]
                    if directive == "merge":
                        self._merge(parms)
                    elif directive == "self" and doself:
                        self._addself(parms)
                else:
                    data = line.split()
                    self.man.addRecord(*data)

    def _merge(self, parms):
        curinfo = self.newcurrent.lookup(parms['pkg'])
        if not curinfo:
            raise RuntimeError("Dependency not found: " + parms['pkg'])
        parms['ver'] = curinfo[0]
        version = parms['ver']
        p = version.find('+');
        build = "1"
        if (p >= 0):
            version = parms['ver'][:p]
            build = parms['ver'][p+1:]

        id = "tarball"
        if not parms.has_key("pkgpath"):
            parms['pkgpath'] = None
            if curinfo and len(curinfo) > 1:
                parms['pkgpath'] = curinfo[1]

            if parms.get('installFile','').endswith('.bld'):
                id="lsstbuild:"
                if parms['pkgpath']: id += parms['pkgpath']
                id = os.path.join(id, parms['pkg'], version,
                                  parms['installFile'])

        dep = os.path.join(destpkgs, "manifests",
                           "%s-%s.manifest" % (parms['pkg'], parms['ver']))
                           
        self.man.merge(Manifest.fromFile(dep))
        
            

    def _addself(self, parms):
        if not parms.has_key("pkg"):
            parms['pkg'] = self.man.name
        if not parms.has_key("vers"):
            parms['ver'] = self.man.vers
        if not parms.has_key("flavor"):
            parms['flavor'] = self.man.flav

        id = "tarball"
        if not parms.has_key("pkgpath"):
            curinfo = self.oldcurrent.lookup(parms['pkg'])
            parms['pkgpath'] = None
            if curinfo and len(curinfo) > 1:
                parms['pkgpath'] = curinfo[1]

            if parms.get('installFile','').endswith('.bld'):
                id="lsstbuild:"
                if parms['pkgpath']: id += parms['pkgpath']
                id = os.path.join(id, parms['pkg'], parms['ver'],
                                  parms['installFile'])

        self.man.addSelfRecord(parms['pkgpath'], self.build, id=id)

    def getManifest(self):
        return self.man
            
class Current(object):

    def __init__(self, file):
        self.file = file
        self.pkgPath = {}

    def lookup(self, pkgname):
        """look up the current version of and relative path to a given
        package. 

        This specifically finds the path to the package name directory
        (containing the various version directories) relative to the
        base directory.
        @param pkgname   the name of the package to look up
        @return an array [] where the first element is the version,
                    the second is the relative path (which may be an empty
                    string), and the third (which may be empty) is the
                    package directory (overriding the default pkg/ver
                    pattern)
        """
        if self.pkgPath.has_key(pkgname):
            return self.pkgPath[pkgname]

        with open(self.file) as cf:
            parts = []
            for line in cf:
                line = line.strip()
                if line.startswith('#'):
                    continue

                parts = re.findall(r"\S+", line)
                if len(parts) > 0 and parts[0] == pkgname:
                    break

        out = []
        if len(parts) < 3 or parts[0] != pkgname:
            return out

        out.append(parts[2])
        if len(parts) > 3:
            out.append(parts[3])
        if len(parts) > 4:
            out[2] = parts[4]

        self.pkgPath[pkgname] = out
        return out

        
                   
        
def options():
    parser = optparse.OptionParser()
    parser.add_option("-E", "--as-external", dest="isext",
                      action="store_true", default=False)
    parser.add_option("-L", "--as-lsst", dest="isext", action="store_false")
    parser.add_option("-B", "--with-bld", dest="withbld",
                      action="store_true", default=False)
    parser.add_option("-b", "--build", dest="bnum", action="store", default="1")
    parser.add_option("-c", "--current-list", dest="current", action="store")
    parser.add_option("-m", "--manifest", dest="manfile", action="store")
    parser.add_option("-T", "--transfer", dest="dotrx", action="store_true",
                      default=False)

    return parser.parse_args()

def parseProduct(prodpath):
    fields = prodpath.split('/')
    if len(fields) < 2:
        raise Runtime("bad product name syntax: " + prodpath)
    out = fields[-2:]
    isext = len(fields) > 2 and fields[-3] == 'external'
    out.append(isext)
        
    return out

def buildNewManifest(prod, version, isext, args, opts):
    m = Manifest(prod, version)
    type = (opts.withbld and "bld") or "tarball"

    while len(args):
        next = Manifest.fromFile(args.pop(0))
        m.merge(next)
    if isext:
        m.addExtRecord(prod, version, build=opts.bnum, id=type)
    else:
        m.addLSSTRecord(prod, version, build=opts.bnum, id=type)
    sys.stdout.write(str(m))

def transferManifest(prod, version, isext, args, opts):
    loader = Loader(prod, version, opts.bnum)

    loader.fillFrom(opts.manfile)
    sys.stdout.write(str(loader.getManifest()))
    

if __name__ == "__main__":
    (opts, args) = options()
    if len(args) < 1:
        raise RuntimeError("Missing product")
    path = args.pop(0)
    (prod, version, isext) = parseProduct(path)
    
    if opts.dotrx:
        if not opts.manfile:
            opts.manfile = os.path.join(path, "the.manifest")
            # raise RuntimeError("need to set --manifest (-m) to old manifest")
        
        transferManifest(prod, version, isext, args, opts)
    else:
        buildNewManifest(prod, version, isext, args, opts)


    
