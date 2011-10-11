"""
functions related to the storage of products artifacts on the server
"""
from __future__ import absolute_import

import sys, os, re
from . import version as onvers
from . import manifest 


class Repository(object):
    """
    a class that represents the model for how the product artifacts are 
    organized on the server disk.  
    """
    manifestDirName = "manifests"
    externalDirName = "external"
    undeployedManifestFileRe = re.compile(r'^b(\d+)' + manifest.extension)

    def __init__(self, rootdir):
        self.root = rootdir

    def getManifestDir(self):
        return os.path.join(self.root, self.manifestDirName)

    def getManifestFile(self, product, version):
        return os.path.join(self.getManifestDir(), 
                            "%s-%s%s" % (product, version, manifest.extension))

    def getExternalProductRoot(self):
        return os.path.join(self.root, self.externalDirName)

    def getTagListFile(self, tagname):
        return os.path.join(self.root, "%s.list" % tagname)

    def getProductDir(self, prodname, version=None, flavor=None, asExt=None):
        """
        return the directory that contains the product artifacts
        @param asExt    if None, expect the directory to exist and find it.
                          If True, treat product explicitly as an external
                          product; False, as an LSST product.
        """
        lpdir = os.path.join(self.root, prodname)
        epdir = os.path.join(self.getExternalProductRoot(), prodname)
        if asExt is None:
            # try to figure it out
            if os.path.exists(lpdir):
                pdir = lpdir
            elif os.path.exists(epdir):
                pdir = epdir
            else:
                raise ProductNotFound(prodname)
        elif asExt:
            pdir = epdir
        else:
            pdir = lpdir

        if not version: 
            return pdir

        pdir = os.path.join(pdir, onvers.baseVersion(version))

        if not flavor:
            return pdir
        return os.path.join(pdir/flavor)

    def _getUndeployedManifestsFor(self, prodname, version, flavor=None):
        pdir = self.getProductDir(prodname, version, flavor)

        files = []
        for filenm in os.listdir(pdir):
            mat = self.undeployedManifestFileRe.match(filenm)
            if mat:
                files.append((filenm, mat.group(1)))

        files.sort(lambda f1, f2: cmp(f1[1], f2[1]))
        return files

    def getUndeployedManifestsFor(self, prodname, version, flavor=None):
        """
        return a list of manifest filenames store in the given product's
        product directory.  
        """
        return map(lambda m: m[0], 
                   self._getUndeployedManifestsFor(prodname, version, flavor))

    def getLatestUndeployedManifestFile(self, prodname, version, flavor=None):
        """
        return the manifest filename representing 
        product directory.  
        """
        files = self._getUndeployedManifestsFor(prodname, version, flavor)
        if not files: 
            return None
        return files[-1][0]

    def getLatestUndeployedBuildNumber(self, prodname, version, flavor=None):
        """
        return the manifest filename representing 
        product directory.  
        """
        files = self._getUndeployedManifestsFor(prodname, version, flavor)
        if not files: 
            return 0
        return int(files[-1][1])

    manifestTemplate = "b%d.manifest"
                       
    def getNextUndeployedBuildFilename(self, prodname, version, flavor=None):
        n = self.getLatestUndeployedBuildNumber(prodname, version, flavor) + 1
        return self.manifestTemplate % n

