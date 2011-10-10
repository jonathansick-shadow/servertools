"""
functions related to releasing new versions of products.
"""
from __future__ import absolute_import

import sys, os
from .manifest import DeployedManifests, Manifest, Dependency
from .server   import Repository
from . import version as onvers

class UpdateDependents(object):
    """
    An operations class that can create new build-increments on all 
    dependents of (products that depende on) a specific set of new 
    software releases.  That is, given a set of products that have 
    recently been released (i.e. manifests deployed into the manifests 
    directory), this will create new manifest files for all dependents
    of those products, ready for release.  

    The creation of of updated manifests is normally done by 
       1) instaniating this class with a given set of recently 
          released products (referred to here as the "target 
          products").
       2) calling createManifests().  
    createManifests() returns a list of tuples, one for each dependent, 
    giving its name, version, new build number, and path to the new 
    manifest file.  That manifest file is ready for release (i.e. copying 
    into the manifests directory).  

    It's possible to tweak the the creation of manifests by calling one 
    or more of the functions that createManifests() calls internally first.  
    These include:
      getDependencies()             generates the list of dependencies for 
                                      the target products
      setUpgradedBuildNumbers()     generates the new build numbers for the 
                                      dependents that will be upgraded.
      setUpgradedManifestRecords()  generates updated manifest records for 
                                      all of the dependents.  

    In detail, one can

    1) Modify the list of dependent products to create udated manifests for.
       To do this, one would,
       a) call getDependents() to return the auto-generated list of dependents
            of the target products.  This list is returned as a dictionary 
            mapping product names to the latest, previously-released versions.  
       b) manipulate the list by either modifying the versions for certain 
            products, removing products, or adding products.
       c) calling setDependents() with the updated list

    2) Modify the build numbers that will be used for the newly generated 
       manifests.  To do this one would, 
       a) call getDependents() to the list products that will be updated
       b) call setDependents() (if desired; see #1 above)
       c) create a dictionary that maps product names to new build numbers 
          and pass it to setUpgradedBuildNumbers():

            r = UpdateDependents(prods, rootdir)
            bn = { "python", 5 }  # or { "python", "5" } 
            setUpgradedBuildNumbers(bn)

          OR, call setUpgradedBuildNumbers() first, manipulate the returned 
          dictionary, and call setUpgradedBuildNumbers() again:

            r = UpdateDependents(prods, rootdir)
            bn = r.setUpgradedBuildNumbers()
            if int(bn['python']) < 5:
                bn['python'] = 5
            r.setUpgradedBuildNumbers(bn)

    3) Modify the new manifest records for some of the dependents.  To do 
       this, one would:
       a) cal getDependencies() to get a list of products to upgraded (if
          needed).
       b) call setUpgradedBuildNumbers() to get the build numbers that are 
          going to be used (if needed).  
       c) create a dictionary of manifest records, perhaps with the help 
          of getUpdatedRecordFor()
       d) pass the dictionary to setUpgradedManifestRecords().  

       For example, 

            r = UpdateDependents(prods, rootdir)
            deps = r.getDependencies()
            if deps.has_key('python'):
                bn = r.setUpgradedBuildNumbers()
                rec = r.getUpdatedRecordFor('python', deps['python'],
                                            bn['python'])
                iid = rec[Dependency.INSTALLID]
                iid = re.sub(r'\.bld', 
                             '+%s.bld' % str(bn['python']), 
                             iid)
                rec[Dependency.INSTALLID] = iid
                r.setUpgradedManifestRecords({'python': rec})

       Alternatively, one could first call 
       setUpgradedManifestRecords() first to get the default 
       generated records, manipulate it as needed, and pass the updated
       dictionary to a second call to setUpgradedManifestRecords().
       
       Finally, after any custom tweaking, one would call 
       createManifests() to apply the customizations.  
    """

    def __init__(self, prodvers, rootdir, vercmp=None, log=None):
        """
        create an instance
        @param prodvers   the list of product-version tuple-pairs that represent
                          the packages that have been release and whose 
                          dependents, therefore, need build increments.  
        @param mandir     the path to the manifests directory
        @param vercmp     the version compare function to use to sort 
                             product version strings.  If None, a default
                             will be used.
        @param log        a file stream to report messages to.  If None (default)
                             messages will not be written.
        """
        self.prods = prodvers
        self.deps = None
        self.upgblds = None
        self.upgrecs = None
        self.vcmp = vercmp
        if self.vcmp == None:
            self.vcmp = onvers.defaultVersionCompare
        self.server = Repository(self.rootdir)
        self.deployed = DeployedManifests(self.server.getManifestDir(), 
                                          self.vcmp)
        self.log = log

    def getDependents(self):
        """
        return a dictionary of product-version pairs for the latest products 
        that are dependents of our target set.  The first call to this 
        function triggers the creation of the internally-stored dictionary.  
        """
        if self.deps is None:

            # loop on the products in target set...
            out = {}
            for prod in self.prods:

                # merge list of dependents into full list
                deps = self.deployed.dependsOn(prod[0], prod[1])
                for dep in deps:
                    if not out.has_key(dep[0]) or \
                       self.vcmp(dep[1], out[dep[0]]) > 0:
                        out[dep[0]] = dep[1]

            self.deps = out

        return self.deps

    def setDependents(self, lookup):
        """
        set the product-version pairs that should be update and rebuilt
        as dependents of our target set.  When called before createManifests(),
        this list will over-ride the list computed by default based on 
        deployed manifests.
        """
        self.deps = lookup
        self.upgblds = None

    def setUpgradedBuildNumbers(self, upgblds=None):
        """
        determine the new build numbers to use for the updgraded dependents and 
        return them as a by-product-namme dictionary.  recommendNextBuildNumber()
        is used to determine the new build number for each dependent.  The 
        resulting dictionary is also stored internally for use when creating the 
        new manifests via createManifest().  One can explicitly set the next build 
        number for any of the products by sending in an initial dictionary; any 
        dependent products missing from the dictionary will be added.

        Normally, this function is called implicitly via createManifests() and thus, 
        only needs to be called explicitly if one wants to tweak the build numbers 
        used.  Thus, if this is called, it should be called before calling 
        createManifests() or setUpgradedManifestRecords().
        @param upgblds   an initial dictionary mapping product names to upgraded
                           build numbers, over-riding the automatically determined
                           ones. 
        @return dictionary  the resulting mapping of product names to upgraded
                           build numbers
        """
        self.upgrecs = None
        if upgblds is not None or self.upgblds is None:
            upgblds = {}

            deps = self.getDependents()
            for name in deps.keys():
                if not upgblds.has_key(name):
                    self.upgblds[name] = self.recommendNextBuildNumber(name, deps[name])
                # self.upgblds[name] = onvers.substituteBuild(deps[name], nextBuild)

            self.upgblds = upgblds

        return self.upgblds

    def recommendNextBuildNumber(self, prodname, version):
        """
        return a recommended next build number.  It will return one plus
        the highest number found for the tagged release version both 
        deployed (in the manifests directory) and undeployed (in the product 
        directory) to avoid any name clashes.
        @param prodname     the name of the product
        @param version      the version.  If this includes a build number,
                                it will be dropped and ignored.
        """
        deplbuild = self.deployed.getLatestBuildNumber(prodname, version)
        undeplbuild = self.getLatestUndeployedBuildNumber(prodname, version)
        return max(deplbuild, undeplbuild) + 1
             
    def createManifests(self):
        """
        Create a new manifest file for each of the dependents of the 
        target set of products and write it into the dependent's product 
        directory.  Each file is written via with writeUpgradedManifest() 
        using a filename of the form "b*.manifest" where * is the new 
        build number.  
        @return list of four-tuples containing the product, base version, build, 
                          and updated manifest file created
        """
        if not self.upgrecs:
            self.setUpgradedManifestRecords()

        out = []
        for prod in self.upgrecs:
            man = self.createUpgradeManifestRecords(prod, self.upgrecs)
            fname = self.writeUpgradedManifest(man, prod, self.deps[prod], 
                                               self.upgblds[prod])

            out.append( (prod, onvers.baseVersion, self.upgblds[prod], fname) )

        # report the new products 
        return out

    def writeUpgradedManifest(self, manifest, prod, version, build, filename=None):
        """
        write out a manifest to its product directory.  The filename, by 
        default, will have the form "b*.manifest" where * is the new build 
        number.
        @param manifest   the Manifest instance to write out
        @param prodname   the name of the product the manifest describes
        @param version    the version of the product the manifest describes.  
                            If this includes a build number, it will be dropped 
                            and ignored.
        @param build      the build number of the version    
        @param filename   the name to give the manifest file.  If None, the 
                            default "b*.manifest" will be used.
        @return str   the full path to the written manifest
        """
        if not filename:
            filename = "b%s.manifest" % str(build)
        version = onvers.baseVersion(version)

        pdir = self.server.getProductDir(prodname, version)
        out = os.path.join(pdir, filename)
        if os.path.exists(out):
            raise RuntimeError("Manifest file already exists; won't overwrite: " + out)

        with open(out, 'w') as fout:
            man.write(fout)

        return out

    def createUpgradedManifest(self, prodname, upgradedRecords=None):
        """
        return an updated manifest for a given dependent (as a Manifest 
        instance).
        @param prodname         the name of the product
        @param upgradedRecords  a by-product-name dictionary of manifest 
                                  records for substitution into the 
                                  output manifest.  
        """
        if not upgradedRecords:
            upgradedRecords = self.makeUpgradedManifestRecords()

        latest = self.deployed.getLatestVersion(prodname)
        if not latest:
            raise DeployedProductNotFound(prodname)
        man = self.deployed.getManifest(prodname, latest)

        newman = Manifest(prodname, upds[prodname])
        for rec in man:
            if rec[0] == '#':
                newman.addComment(rec[-1])
            else:
                rec = Dependency(rec)
                if rec.data[rec.NAME] in upgradedRecords:
                    newman.addRecord(*upgradedRecords[rec.data[rec.NAME]])
                else:
                    newman.addRecord(*rec.data)

        return newman

    def setUpgradedManifestRecords(self, upgrecs=None, uselatest=True):
                                    
        """
        create an updated manifest record for each the dependents to be used 
        in their upgraded manifests, and return them in a by-product-name 
        dictionary.  getUpdatedRecordFor() is used to create a dependent's 
        updated record.  The resulting dictionary is also stored internally 
        for use when creating the new manifests via createManifest().  One can 
        explicitly set updated records for any of the products by sending an
        inition dictionary; any dependent products missing from the dictionary 
        will be added.

        Normally, this function is called implicitly via createManifests() and thus, 
        only needs to be called explicitly if one wants to tweak the build numbers 
        used.  Thus, if this is called, it should be called before calling 
        createManifests().
        @param upgrecs    an initial dictionary mapping product names to updated
                             manifest records.  Records are represented as an array
                             of manifest file column data (in order of product,
                             flavor, version, table path, install path, and 
                             install ID).
        @param uselatest  if True, ensure that the latest deployed build of the 
                             dependent product will be used to create an updated 
                             manifest record.  If False, the build specified in 
                             the version returned in the getDependents() list will 
                             be used (which may or may not be the latest build)
        @return dictionary  the resulting mapping of product names to updated
                             manifest records (in the same format as upgrecs).  
        """
        if self.upgblds is None:
            self.upgblds = self.getUpgradedDependents();
        if upgrecs is None:
            upgrecs = {}

        for prod in self.deps:
            if upgrecs.has_key(prod):
                continue

            vers = self.deps[prod]
            if uselatest:
                lastbuild = self.deployed.getLatestBuildNumber(prod, version)
                vers = onvers.substituteBuild(version, lastbuild)

            rec = self.getUpdatedRecordFor(prod, vers, self.upgblds[prod])
            if rec:
                # rec could be null if this is a pseudo product
                # (which shouldn't happen)
                upgrecs[prod] = rec

        self.upgrecs = upgrecs
        return upgrecs

    def getUpdatedRecordFor(self, prodname, oldversion, newbuild):
        """
        Extract a manifest record for building a given product from
        a previously deployed manifest for the product and return an updated
        version.  The prototype of the record is gotten by opening the manifest 
        for the given version and extracting the (last) record that builds that
        product itself.  The build number that appears in that record is then
        substituted with the given new build number.
        @param prodname    the name of the product to get record for
        @param oldversion  a previously deployed version (including the build 
                              number) of the product.  This version will be used
                              to extract the template.  
        @param newbuild    the build number for the upgraded product to use in the 
                              updated record.  
        @return list   manifest column data for the requested product
        """
        # open up the specified version of this dependency
        man = self.deployed.getManifest(prodname, oldvers)
        rec = Dependency(man.getSelf())

        newversion = onvers.substituteBuild(oldversion, newbuild)
        if oldversion != rec[rec.VERSION]:
            # warn
            pass
        oldversion = rec[rec.VERSION]

        # updated references to the old version
        for col in xrange(len(rec)):
            p = idir.find(oldversion)
            if p >= 0:
                rec[col] = rec[col][:p] + newversion + rec[col][len(oldversion):]

        return rec

    def getManifestFilenames(self):
        return map(lambda p: self.deployed.manifestFilename(p[0], p[1]), 
                   self.getUpdatedDependents().items())
        


