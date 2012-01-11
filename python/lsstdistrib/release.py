"""
functions related to releasing new versions of products.
"""
from __future__ import with_statement
from __future__ import absolute_import

import sys, os, re, shutil
from .manifest import DeployedManifests, Manifest, Dependency, DeployedProductNotFound
from .server   import Repository
from .tags     import TagDef
from . import version as onvers

class UprevProduct(object):
    """
    An operations class that will create an up-reved manifest using
    the latest updated product dependencies.
    """

    def __init__(self, serverdir, updatedeps=None, deployedmans=None):
        """
        @param serverdir     the root directory of the distribution server.
        @param updatedeps    an UpdateDependents instance to use
        @param deployedmans  a DeployedManifest instance to use
        """
        self.sdir = serverdir
        self.server = Repository(self.sdir)
        self.uprevdeps = updatedeps
        self.deployed = deployedmans
        if not self.uprevdeps:
            self.uprevdeps = BuildDependencies(self.sdir, deployedmans)
        if not self.deployed:
            self.deployed = self.uprevdeps._deployed

    def uprev(self, prodname, version, filename=None):
        """
        create an up-reved manifest and return the name of the file.
        """
        newbn = self.recommendNextBuildNumber(prodname, version)
        newver = onvers.substituteBuild(version, newbn)
        
        oldman = self.deployed.getManifest(prodname, version)
        newman = Manifest(prodname, newver)
        for rec in oldman:
            if rec[0] == prodname:
                newman.addSelf()
            elif rec[0] == '#':
                newman.addComment(rec[-1])
            else:
                if self.uprevdeps.hasProduct(rec[0]):
                    dep = self.uprevdeps.getDepForProduct(rec[0])
                newman.addRecord(*dep.data)

        if not filename:
            filename = "b%s.manifest" % str(build)
        newver = onvers.baseVersion(newver)
        pdir = self.server.getProductDir(prodname, version)
        out = os.path.join(pdir, filename)
        if os.path.exists(out):
            raise RuntimeError("Manifest file already exists; " +
                               "won't overwrite: " + out)

        with open(out, 'w') as fout:
            newman.write(fout)
        return out

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
        undeplbuild = self.server.getLatestUndeployedBuildNumber(prodname, version)
        return max(deplbuild, undeplbuild) + 1
             
        
        

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
      getDependents()               generates the list of dependencies for 
                                      the target products
      setUpgradedBuildNumbers()     generates the new build numbers for the 
                                      dependents that will be upgraded.
      setUpgradedManifestRecords()  generates updated manifest records for 
                                      all of the dependents.  

    In detail, one can

    1) Modify the list of dependent products to create updated manifests for
       them.  To do this, one would,
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
       a) cal getDependendents() to get a list of products to upgraded (if
          needed).
       b) call setUpgradedBuildNumbers() to get the build numbers that are 
          going to be used (if needed).  
       c) create a dictionary of manifest records, perhaps with the help 
          of getUpdatedRecordFor()
       d) pass the dictionary to setUpgradedManifestRecords().  

       For example, 

            r = UpdateDependents(prods, rootdir)
            deps = r.getDependendents()
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
        self.tagged = None
        if self.vcmp == None:
            self.vcmp = onvers.defaultVersionCompare
        self.server = Repository(rootdir)
        self.deployed = DeployedManifests(self.server.getManifestDir(), 
                                          self.vcmp)
        self.log = log

    def updateFromTag(self, tag):
        tagfile = self.server.getTagListFile(tag)
        if self.tagged:
            self.tagged.merge(tagfile)
        else:
            self.tagged = TagDef(tagfile)

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
                deps = self.deployed.dependsOn(prod[0])
                for dep in deps:
                    if dep[0] == prod[0]:
                        continue
                    try:
                        self.server.getProductDir(dep[0], dep[1])
                    except DeployedProductNotFound:
                        print >> self.log, \
                          "Note: No product directory for %s %s; skipping." % \
                          (dep[0], dep[1])
                        continue
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
                    upgblds[name] = self.recommendNextBuildNumber(name, deps[name])
                # upgblds[name] = onvers.substituteBuild(deps[name], nextBuild)

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
        try:
            deplbuild = self.deployed.getLatestBuildNumber(prodname, version)
            undeplbuild = self.server.getLatestUndeployedBuildNumber(prodname, version)
            return max(deplbuild, undeplbuild) + 1
        except DeployedProductNotFound, ex:
            return 1
             
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
        for prod in self.upgblds:
            man = self.createUpgradedManifest(prod, self.upgrecs)
            fname = self.writeUpgradedManifest(man, prod, self.deps[prod], 
                                               self.upgblds[prod])

            out.append( (prod, onvers.baseVersion(self.deps[prod]), 
                         self.upgblds[prod], fname) )

        # report the new products 
        return out

    def writeUpgradedManifest(self, manifest, prodname, version, build, 
                              filename=None):
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
            manifest.write(fout)

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
            upgradedRecords = self.setUpgradedManifestRecords()

        version = None
        if self.tagged:
            # up-rev the tagged version
            version = self.tagged.getVersion(prodname)
        if not version:
            # up-rev the latest deployed version
            version = self.deployed.getLatestVersion(prodname)
        if not version:
            raise DeployedProductNotFound(prodname)
        man = self.deployed.getManifest(prodname, version)

        # update the manifest
        newbuild = self.upgblds.get(prodname)
        if not newbuild:
            newbuild = self.recommendNextBuildNumber(prodname, version)
        version = onvers.substituteBuild(version, newbuild)
        newman = Manifest(prodname, version)
        for rec in man:
            if rec[0] == '#':
                newman.addComment(rec[-1])
            else:
                rec = Dependency(rec)
                if rec.getName() in upgradedRecords:
                    newman.addRecord(*upgradedRecords[rec.getName()])
                elif self.tagged:
                    pname = rec.getName()
                    dver = self.tagged.getVersion(pname)
                    dman = self.deployed.getManifest(pname, dver)
                    if dman:
                        rec = dman.getSelf()
                        upgradedRecords[pname] = rec
                    newman.addRecord(*rec)
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
            self.upgblds = self.setUpgradedBuildNumbers();
        if upgrecs is None:
            upgrecs = {}

        # first go through the dependents
        for prod in self.deps:
            if upgrecs.has_key(prod):
                continue

            vers = self.deps[prod]
            if uselatest:
                lastbuild = self.deployed.getLatestBuildNumber(prod, vers)
                vers = onvers.substituteBuild(vers, lastbuild)

            rec = self.getUpdatedRecordFor(prod, vers, self.upgblds[prod])
            if rec:
                # rec could be null if this is a pseudo product
                # (which shouldn't happen)
                upgrecs[prod] = rec

        # next put in the target products (so as not to override)
        for prod in self.prods:
            if upgrecs.has_key(prod[0]):
                continue
            # open up the manifest for that product:
            man = self.deployed.getManifest(prod[0], prod[1])
            rec = man.getSelf()
            if not rec:
                # this may be a pseudo product
                continue
            upgrecs[prod[0]] = rec

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
        man = self.deployed.getManifest(prodname, oldversion)
        rec = man.getSelf()
        if not rec:
            return None
        rec = Dependency(rec)

        newversion = onvers.substituteBuild(oldversion, newbuild)
        if oldversion != rec.data[rec.VERSION]:
            # warn
            pass
        oldversion = rec.data[rec.VERSION]

        # updated references to the old version
        for col in xrange(len(rec.data)):
            p = rec.data[col].find(oldversion)
            if p >= 0:
                rec.data[col] = rec.data[col][:p] + newversion + \
                    rec.data[col][p+len(oldversion):]

        return rec.data

    def getManifestFilenames(self):
        return map(lambda p: self.deployed.manifestFilename(p[0], p[1]), 
                   self.getUpdatedDependents().items())
        

class Release(object):
    """
    An operation class that will deploy manifest files in the product directories
    into the manifests directory, making their products available to users for 
    download.  
    """

    def __init__(self, manifests, rootdir, log=None):
        """
        instantiate the class
        @param manifests   a list of manifests identified by a 3- or 4-tuple.  The 
                             first three elements are the product name, the version
                             (with a build number), and a path to the manifest file.
                             The optional 4th element is a category (either "external"
                             or "pseudo").  If not provided, its category and location
                             will be determined by examinging the server.  
        @param rootdir     the root directory of the distribution server
        @param log         a file stream for sending messages.
        """
        self.repos = Repository(rootdir)
        self.manifests = manifests
        self.log = log

    def parseProductManifestPath(mpath):
        fields = mpath.split('/')
        if len(fields) < 3:
            raise RuntimeError("bad product name syntax: " + mpath)
        out = fields[-3:]

        mat = re.match(r'^b(\d+).manifest', out[2])
        if mat:
            out[1] = onvers.substituteBuild(out[1], mat.group(1))

        if os.path.exists(mpath):
            out[2] = mpath
        if fields[-3] == 'external' or fields[-3] == 'pseudo':
            out.append(fields[-3])

        return out

    parseProductManifestPath = staticmethod(parseProductManifestPath)

    def makeDestPath(self, mandata):
        return self.repos.getManifestFile(mandata[0], mandata[1])

    def releaseAll(self, overwrite=False, atomic=False):
        """
        release all configured manifest files.  
        @param overwrite  if False, the copy will fail if the destination file
                            already exists.  Otherwise, overwrite the destination
                            file if it exists.
        @param atomic     if False, try to copy as many files as possible; 
                            otherwise, attempt an atomic operation, rolling back
                            the copies if any errors are encountered.
        """
        failed = []
        copied = []
        try:
            for man in self.manifests:
                src = man[2]
                if not os.path.exists(src):
                    cat = (len(man) > 3 and man[3]) or None
                    src = os.path.join(
                        self.repos.getProductDir(man[0], man[1], category=cat),
                        os.path.basename(man[2]))

                dest = self.makeDestPath(man)
                if not overwrite and os.path.exists(dest):
                    failed.append( (src, dest, 
                                    "deployed manifest already exists") )
                    if atomic:  
                        raise RuntimeError("%s: %s" % (failed[-1][2], dest))
                    elif self.log:
                        print >> self.log, "Destination file already exists: %s" % dest
                    continue

                try:
                    shutil.copyfile(src, dest)
                    copied.append(dest)
                    if not atomic and self.log:
                        print >> self.log, "Deployed", os.path.basename(dest)
                except OSError, ex:
                    failed.append( (src, dest, str(ex)) )
                    if atomic:  raise
                    elif self.log:
                        print >> self.log, "Trouble copying file: %s: %s" % \
                            (str(ex), man[2])

        finally:
            if atomic and failed:
                for filepath in copied:
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

