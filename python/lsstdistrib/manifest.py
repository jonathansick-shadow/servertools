"""
a module for manipulating manifest files without use of EUPS and a installed
software stack.  The main functionality is provided via the Manifest class.
"""

defaultColumnNames = \
"pkg flavor version tablefile installation_directory installID".split()

class Manifest(object):
    """
    An in-memory representation of a package manifest with built-in
    notions of LSST conventions.
    """

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

