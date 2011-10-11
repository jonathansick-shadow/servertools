"""
a module for manipulating manifest files without use of EUPS and a installed
software stack.  The main functionality is provided via the Manifest class.
"""
from __future__ import absolute_import
from __future__ import with_statement

import sys, os, re, cStringIO
from subprocess import Popen, PIPE
from copy import copy

from . import version as onvers

defaultColumnNames = \
"pkg flavor version tablefile installation_directory installID".split()
headerLineMagic = "EUPS distribution manifest"
defaultManifestHeader = headerLineMagic + \
""" for %s (%s). Version 1.0
#
"""
headerLineRe = re.compile(headerLineMagic + r" for (\S+) \((\S+)\)")

extension = ".manifest"

class Manifest(object):
    """
    An in-memory representation of a package manifest with built-in
    notions of LSST conventions.
    """

    def __init__(self, name, version, pkgpath=None, flavor="generic"):
        """create a manifest for a given package

        @param name     the name of the product this manifest is for
        @param version  the version of the package
        @param pkgpath  the extra path to the product directory.  For
                          external products, this value is set to 
                          "external"
        @param flavor   the name of the platform type supported by this
                          installation of the package
        """
        self.recs = {}
        self.keys = []
        self.name = name
        self.vers = version
        self.flav = flavor
        self.pkgpath = pkgpath
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
        self.recs[key] = ['#'] + [ '' ] * len(self.colnames)
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
        key = self._reckey(pkgname, flavor, version)
        if not self.recs.has_key(key):
            self.keys.append(key)
            self.recs[key] = [pkgname, flavor, version,
                              tablefile, installdir, installid]

    def addLSSTRecord(self, prodname, version, pkgpath=None, build=None, 
                      flavor="generic", id="lsstbuild", buildqual="+"):
        """append a standard build record for an LSST package.

        @param prodname   the name of the product
        @param version    the version of the product
        @param pkgpath    if non-None, a path to be prepended to the standard
                             package/version install directory (default:
                             None)
        @param flavor     the name of the platform type supported by this
                            installation of the package (default: "generic")
        @param id         the installid or abbreviation (default: "lsstbuild")
        """
        buildsuffix = ''
        if build:
            version = onvers.baseVersion(version)
            buildsuffix = buildqual + str(build)

        srvpath = self.defaultProductPath(prodname, version, pkgpath)
        ipkgpath = srvpath + buildsuffix
        tablepath = os.path.join(srvpath, "%s.table" % prodname)

        self.addRecord(prodname, flavor, version+buildsuffix, tablepath, ipkgpath,
                       self.defaultID(id, prodname, version, path=srvpath))
                                      
                       
    def addExtRecord(self, pkgname, version, pkgpath="external", 
                     build="1", flavor="generic", id="lsstbuild", buildqual="+"):
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
        self.addLSSTRecord(pkgname, version, pkgpath, build, flavor, id, buildqual)

    def addSelfRecord(self, flavor="generic", id="lsstbuild"):
        """append a standard build record for the package that this
        manifest is for

        @param flavor     the name of the platform type supported by this
                            installation of the package (default: "generic")
        @param id         the installid or abbreviateion (default: "pacman")
        """
        vbits = onvers.splitToReleaseBuild(self.vers)
        self.addLSSTRecord(self.name, vbits[0], self.pkgpath, vbits[2], flavor, 
                           id, vbits[1])

    def defaultProductPath(self, prodname, version, pkgpath=None):
        """
        create a path for the product directory on the server.  
        """
        ver = onvers.baseVersion(version)
        path = "%s/%s" % (prodname, ver)
        if pkgpath:
            path = "%s/%s" % (pkgpath, path)
            
        return path

    def defaultID(self, id, prodname, version, pkgpath=None, flavor=None, path=None):
        """
        create an installid from an abbreviation that is consistent
        with the package name and version.  If the input id is not
        recognized as an abbreviation, it is returned untransformed.

        Recognized ids include "lsstbuild", representing a standard LSST
        build script having the name of the form, "package.bld".  

        @param id    either an id abbreviation or a full installid
        @param prodname   the name of the product
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        """
        if not path:
            path = self.defaultProductPath(prodname, version, pkgpath)
            if flavor and flavor != "generic":
                path += "/%s" % flavor

        if (id == 'lsstbuild' or id == 'tarball'):
            id = "lsstbuild:%s/%s-%s.tar.gz" % (path, prodname, version)
        elif (id == 'bld'):
            id = "lsstbuild:%s/%s.bld" % (path, prodname)
        return id

    def hasRecord(self, pkgname, flavor, version):
        """return true if this manifest has a record matching the
        package name, flavor, and version

        @param pkgname    the name of the package
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        """
        return self.recs.has_key(self._reckey(pkgname, flavor, version))

    def hasProduct(self, prodname):
        """return true if this manifest has a record matching the
        package name

        @param prodname    the name of the package
        """
        return bool(filter(lambda k: k.startswith(prodname+':'), self.keys))

    def getSelf(self):
        """
        return the record data that applies to the owning product itself.
        """
        return self.recs.get(self._reckey(self.name, self.flav, self.vers))

    def getRecord(self, prodname, version, flavor="generic"):
        """
        return the record data that applies to the owning product itself.
        """
        return self.recs.get(self._reckey(prodname, flavor, version))

    def getProduct(self, prodname):
        """
        return the last occurance of the record for the given product name
        in the manifest or None if it is not found in this manifest.  Normally,
        there should only be one occurance of a product in the manifest.
        @param prodname    the name of the product for which a record is desired
        """
        keys = filter(lambda k: k.startswith(prodname+':'), self.keys)
        if len(keys) == 0:
            return None
        return self.recs[keys[-1]]

    def recordToString(self, pkgname, flavor, version):
        """return the requested record in manifest format.
        @param pkgname    the name of the package
        @param flavor     the name of the platform type supported by this
                            installation of the package
        @param version    the version of the package
        """
        if (not self.hasRecord(pkgname, flavor, version)):
            raise RuntimeError("record not found in manifest")
        return " ".join(self.recs(self._reckey(pkgname, flavor, ver)))

    def _reckey(self, pkgname, flavor, version):
        return ":".join([pkgname, flavor, version])

    def __repr__(self):
        """return all lines of the manifest in proper manifest format"""
        out = cStringIO.StringIO()
        self.write(out)
        return out.getvalue()

    def str(self):
        """return all lines of the manifest in proper manifest format"""
        return str(self)

    def write(self, strm):
        """print the lines of the manifest to a give output stream.

        @param strm  the output stream to write the records to
        """
        collen = self._collen()
        fmt = "%%-%ds %%-%ds %%-%ds %%-%ds %%-%ds %%s\n" % tuple(collen[:-1])
        
        strm.write(self.hdr % (self.name, self.vers))
        strm.write((fmt % tuple(self.colnames)))
        strm.write("#" + " ".join(map(lambda x: '-' * x, collen))[1:109])
        strm.write("\n")

        for key in self.keys:
            if key.startswith('#'):
                strm.write("# %s\n" % self.recs[key][-1])
            else:
                strm.write(fmt % tuple(self.recs[key]))

    class _iterator(object):
        def __init__(self, manifest):
            self._keys = manifest.keys[:]
            self._recs = manifest.recs.copy()
            self._nxtIdx = (len(self._keys) and 0) or 1
        def __iter__(self):
            return self
        def next(self):
            if self._nxtIdx >= len(self._keys):
                raise StopIteration()
            try:
                return self._recs[self._keys[self._nxtIdx]]
            finally:
                self._nxtIdx += 1

    def __iter__(self):
        return self._iterator(self)
            
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

                parts = re.split(r'\s+', line, len(defaultColumnNames))
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

class Dependency(object):
    """
    a light weight container of the data from one record in a manifest
    """
    NAME       = 0
    FLAVOR     = 1
    VERSION    = 2
    TABLEFILE  = 3
    INSTALLDIR = 4
    INSTALLID  = 5

    def __init__(self, data):
        """
        initialize the Dependency
        @param data    the list containing the manifest record data, in the 
                         that they appear in the file.  For efficiency, the 
                         list is not copied but rather stored by reference.
        """
        self.data = data

    def matches(self, prodname, version=None, flavor=None):
        if prodname != self.data[self.NAME]:
            return False
        if version is not None and version != self.data[self.VERSION]:
            return False
        if flavor is not None and flavor != self.data[self.FLAVOR]:
            return False
        return True

class DeployedManifests(object):
    """
    the set of deployed manifests represented by the manifests directory
    and the manifest files it contains.  
    """

    def __init__(self, mandir, versionCompare=None):
        """
        initialize to a given manifests directory
        @param mandir          the directory containing the manifests
        @param versionCompare  the comparator functor that can be used 
                                  for sorting versions.  If not provided,
                                  a default will be used.
        """
        self.dir = mandir
        if versionCompare is None:
            versionCompare = onvers.VersionCompare()
        self.vcmp = versionCompare
        self.extension = extension

    def dependsOn(self, prodname, version=None, flavor=None):
        """
        return a list of product-version pairs of products that depends
        the given product.
        """
        # this implementation uses grep for maximum performance search 
        # through many files.  
        mprod = "^\s*%s\s"
        mflav = "\s*%s\s"
        mvers = "\s*%s\s"

        pattern = mprod % prodname
        if flavor or version:
            pattern += mflav % (flavor or "\S+")
            if version:
                pattern += mvers % re.sub(r'\+', r'\+', version)

        cmd = "grep -lP".split()
        cmd.append(pattern)
        cmd += self.latestManifestFiles()

        srch = Popen(cmd, executable="/bin/grep", stdout=PIPE, stderr=PIPE, 
                     cwd=self.dir)
        (cmdout, cmderr) = srch.communicate()
        matchedFiles = cmdout.strip().split("\n")
        if srch.returncode:
            msg = "Problem scanning manifest files:\n" + cmderr
            raise RuntimeError(msg)

        return map(lambda f: self.productFromFilename(f), matchedFiles)
        
        
    def _paircmp(self, pair1, pair2):
        cmpson = cmp(pair1[0], pair2[0])
        if cmpson != 0:
            return cmpson
        if pair1[1] == pair2[1]:
            return 0
        if pair1[1] is None:
            return -1
        if pair2[1] is None:
            return  1
        return self.vcmp(pair1[1], pair2[1])

    def listAll(self):
        """
        return a list of all products (as product-version tuple-pairs)
        deployed as determined by manifests files in the manifests 
        directory
        """
        return map(lambda m: self.productFromFilename(m),
                  filter(lambda f: f.endswith(self.extension), 
                         os.listdir(self.dir)))

    def getVersions(self, prodname):
        """
        return an ordered list of versions that have been deployed for a 
        given product.
        """
        out = map(lambda p: p[1], 
                  filter(lambda m: m[0] == prodname, self.listAll()))
        out.sort(self.vcmp)
        return out

    def getLatestVersion(self, prodname):
        """
        return the latest deployed version of a product
        """
        vers = self.getVersions(prodname)
        if not vers:
            raise DeployedProductNotFound(prodname)
        return vers[-1]

    def latestProducts(self, mandir=None):
        """
        return a list of products representing the latest versions of 
        those products that have been released (i.e. have an entry in the 
        manifests directory).
        @param mandir   the manifests directory to search.  If None, the 
                            directory that this class was instantiated against
                            will be searched.
        """
        # list the manifest files and parse each into a product and version
        mfs =self.listAll()
        if len(mfs) == 0:
            return []

        # collect products together and sort by version order
        mfs.sort(self._paircmp)  

        out = []
        while len(mfs) > 0:
            # the last of a product with a given name is the latest
            if len(mfs) == 1 or mfs[0][0] != mfs[1][0]:
                out.append(mfs[0])
            mfs.pop(0)

        return out

    def latestManifestFiles(self):
        """
        return the paths to the manifest files for the products returned 
        by latestProducts()
        """
        return map(lambda f: os.path.join(self.dir, f), 
                   map(lambda p: self.manifestFilename(*p), 
                       self.latestProducts()))

    def getLatestBuildNumber(self, prodname, version):
        """
        return the largest build number that has been deployed for the given 
        version of a product.  
        @param prodname    the name of the product
        @param version     the version of the product.  If the value includes 
                             a build number, it will be ignored.  
        """
        version = onvers.baseVersion(version)
        buildRe = re.compile("\+(\d+)$")
        versions = self.getVersions(prodname)
        if not versions:
            raise DeployedProductNotFound(prodname, version)
        versions = filter(lambda b: buildRe.search(b), 
                          filter(lambda v: v.startswith(version+"+"), 
                                 versions))
        versions.sort(self.vcmp)
        return int(buildRe.search(versions[-1]).group(1))

    def manifestFilename(self, prodname, version, flavor=None):
        """
        return the name of the manifest file for the given product within
        manifests directory.
        @param prodname    the name of the product
        @param version     the version of the product (including any 
                             build number qualifier)
        @param flavor      the name of the flavor for the flavor-specific 
                             version of the product.  If None, defaults 
                             to "generic".
        """
        out = "%s-%s%s" % (prodname, version, self.extension)
        if flavor:
            out = os.path.join(flavor, out)
        return out

    def productFromFilename(self, fname):
        """
        return a tuple-pair containing the product name and version that 
        the file with the given manifest filename describes.  It assumes
        the filename is of the form, "product-version.manifest".  The 
        trailing ".manifest" extension is optional.  The version (the second 
        element) will be None if the name does not encode a version (i.e. does 
        not have a "-").  
        @param fname    the filename
        @return tuple   the product-version pair.  
        """
        fname = os.path.basename(fname)
        if fname.endswith(self.extension):
            fname = fname[:-1*len(self.extension)]

        out = fname.split('-', 1)
        if len(out) < 2:
            out.append(None)
        return (out[0], out[1])

    def getManifest(self, prodname, version, flavor=None):
        """
        open the manifest file for a given product and return its contents
        as a Manifest instance
        """
        filename = os.path.join(self.dir, 
                                self.manifestFilename(prodname, version, flavor))
        if not os.path.exists(filename):
            raise DeployedProductNotFound(prodname, version, flavor)
        if not flavor:  
            flavor = "generic"
        return Manifest.fromFile(filename, flavor, prodname, version)


class DeployedProductNotFound(Exception):
    """
    an exception indicating that a manifest file for a product could not 
    be found in the manifests directory
    """

    def __init__(self, prodname, version=None, flavor=None, msg=None):
        if not flavor:
            flavor = "generic"
        ver = version or ""
        if not msg:
            msg = "Product not deployed: %s %s (%s)" % (prodname, ver, flavor)
                
        Exception.__init__(self, msg)

        self.name = prodname
        self.verison = version
        self.flavor = flavor
