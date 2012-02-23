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
    pseudoDirName = "pseudo"
    manifestDirName = "manifests"
    externalDirName = "external"
    undeployedManifestFileRe = re.compile(r'^b(\d+)' + manifest.extension + '$')

    def __init__(self, rootdir):
        self.root = rootdir

    def getPseudoProductRoot(self):
        return os.path.join(self.root, self.pseudoDirName)        

    def getManifestDir(self):
        return os.path.join(self.root, self.manifestDirName)

    def getManifestFile(self, product, version):
        return os.path.join(self.getManifestDir(), 
                            "%s-%s%s" % (product, version, manifest.extension))

    def getExternalProductRoot(self):
        return os.path.join(self.root, self.externalDirName)

    def getTagListFile(self, tagname):
        return os.path.join(self.root, "%s.list" % tagname)

    def getProductDir(self, prodname, version=None, flavor=None, category=None):
        """
        return the directory that contains the product artifacts
        @param prodname   the name of the product of interest
        @param version    the version of the product.  If not provided, the parent
                             directory containing all versions is returned
        @param category   the category of the product.  Recognized categories are 
                             currently "external" and "pseudo".  If set explicitly 
                             to a empty string, the product will be interpreted 
                             explicitly as an LSST product.  If None (default),
                             this function will figure out the category.  
        """
        if category == '':
            pdir = os.path.join(self.root, prodname)
        elif category:
            pdir = os.path.join(self.root, category, prodname)
        else:
            lpdir = os.path.join(self.root, prodname)
            epdir = os.path.join(self.getExternalProductRoot(), prodname)
            ppdir = os.path.join(self.getPseudoProductRoot(), prodname)

            # try to figure it out
            if os.path.exists(lpdir):
                pdir = lpdir
            elif os.path.exists(epdir):
                pdir = epdir
            elif os.path.exists(ppdir):
                pdir = ppdir
            else:
                msg = "No product directory found for " + prodname
                raise manifest.DeployedProductNotFound(prodname, msg=msg)

        if not version: 
            return pdir

        pdir = os.path.join(pdir, onvers.baseVersion(version))

        if not flavor:
            return pdir
        return os.path.join(pdir, flavor)

    def _getUndeployedManifestsFor(self, prodname, version, flavor=None):
        pdir = self.getProductDir(prodname, version, flavor)

        files = []
        for filenm in os.listdir(pdir):
            mat = self.undeployedManifestFileRe.match(filenm)
            if mat:
                files.append((filenm, int(mat.group(1))))

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

