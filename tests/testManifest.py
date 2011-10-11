"""
test the manifest module
"""

import os, sys, re, unittest, pdb
from cStringIO import StringIO

from lsstdistrib.manifest import Dependency, Manifest, DeployedManifests
from lsstdistrib.manifest import DeployedProductNotFound

testdir = os.path.join(os.getcwd(), "tests")

class DependencyTestCase(unittest.TestCase):

    def setUp(self):
        self.data = "python generic 2.7.2+5 external/python/2.7.2/python.table external/python/2.7.2+5 lsstbuild:external/python/2.7.2/python.bld".split()

    def tearDown(self):
        pass

    def testAccess(self):
        dep = Dependency(self.data)
        self.assertEquals("python", dep.data[dep.NAME])
        self.assertEquals("generic", dep.data[dep.FLAVOR])
        self.assertEquals("2.7.2+5", dep.data[dep.VERSION])
        self.assertEquals("external/python/2.7.2/python.table", 
                          dep.data[dep.TABLEFILE])
        self.assertEquals("external/python/2.7.2+5", dep.data[dep.INSTALLDIR])
        self.assertEquals("lsstbuild:external/python/2.7.2/python.bld", 
                          dep.data[dep.INSTALLID])

    def testMatches(self):
        dep = Dependency(self.data)
        self.assert_(dep.matches("python"))
        self.assert_(not dep.matches("swig"))
        self.assert_(dep.matches("python", "2.7.2+5"))
        self.assert_(not dep.matches("python", "2.7.2+4"))
        self.assert_(not dep.matches("swig", "2.7.2+5"))
        self.assert_(dep.matches("python", "2.7.2+5", "generic"))
        self.assert_(not dep.matches("python", "2.7.2+5", "Linux64"))
        self.assert_(not dep.matches("python", "2.7.2+3", "generic"))
        self.assert_(not dep.matches("swig", "2.7.2+5", "generic"))

class ManifestTestCase(unittest.TestCase):
    def setUp(self):
        self.data = "python generic 2.7.2+5 external/python/2.7.2/python.table external/python/2.7.2+5 lsstbuild:external/python/2.7.2/python.bld".split()
        self.server = os.path.join(testdir, "server")

    def tearDown(self):
        pass


    def testCtor(self):
        man = Manifest("numpy", "1.6.1+1")
        id = man.getNameVerFlav()
        self.assertEquals("numpy", id[0])
        self.assertEquals("1.6.1+1", id[1])
        self.assertEquals("generic", id[2])

        man = Manifest("numpy", "1.6.1+1", "external")
        id = man.getNameVerFlav()
        self.assertEquals("numpy", id[0])
        self.assertEquals("1.6.1+1", id[1])
        self.assertEquals("generic", id[2])

        man = Manifest("numpy", "1.6.1+1", flavor="Darwin86")
        id = man.getNameVerFlav()
        self.assertEquals("numpy", id[0])
        self.assertEquals("1.6.1+1", id[1])
        self.assertEquals("Darwin86", id[2])

        man = Manifest("numpy", "1.6.1+1", "external", flavor="Darwin86")
        id = man.getNameVerFlav()
        self.assertEquals("numpy", id[0])
        self.assertEquals("1.6.1+1", id[1])
        self.assertEquals("Darwin86", id[2])

    def testDefaultProductPath(self):
        man = Manifest("numpy", "1.6.1+1")
        self.assertEquals("afw/4.5", man.defaultProductPath("afw", "4.5"))
        self.assertEquals("external/afw/4.5", 
                          man.defaultProductPath("afw", "4.5", "external"))
        self.assertEquals("goofy/afw/4.5", 
                          man.defaultProductPath("afw", "4.5", "goofy"))
        self.assertEquals("afw/4.5", man.defaultProductPath("afw", "4.5+3"))
                          

    def testDefaultId(self):
        man = Manifest("numpy", "1.6.1+1")
        self.assertEquals("lsstbuild:afw/4.5/afw-4.5.tar.gz", 
                          man.defaultID("tarball", "afw", "4.5"))
        self.assertEquals("lsstbuild:external/afw/4.5/afw-4.5.tar.gz", 
                          man.defaultID("tarball", "afw", "4.5", "external"))
        self.assertEquals("lsstbuild:external/afw/4.5/Linux/afw-4.5.tar.gz", 
                          man.defaultID("tarball", "afw", "4.5", "external", "Linux"))
        self.assertEquals("lsstbuild:afw-4.5/afw-4.5.tar.gz", 
                          man.defaultID("tarball", "afw", "4.5", path="afw-4.5"))

        self.assertEquals("lsstbuild:afw/4.5/afw-4.5.tar.gz", 
                          man.defaultID("lsstbuild", "afw", "4.5"))
        self.assertEquals("lsstbuild:external/afw/4.5/afw-4.5.tar.gz", 
                          man.defaultID("lsstbuild", "afw", "4.5", "external"))
        self.assertEquals("lsstbuild:external/afw/4.5/Linux/afw-4.5.tar.gz", 
                          man.defaultID("lsstbuild", "afw", "4.5", "external", "Linux"))
        self.assertEquals("lsstbuild:afw-4.5/afw-4.5.tar.gz", 
                          man.defaultID("lsstbuild", "afw", "4.5", path="afw-4.5"))

        self.assertEquals("lsstbuild:afw/4.5/afw.bld", 
                          man.defaultID("bld", "afw", "4.5"))
        self.assertEquals("lsstbuild:external/afw/4.5/afw.bld", 
                          man.defaultID("bld", "afw", "4.5", "external"))
        self.assertEquals("lsstbuild:external/afw/4.5/Linux/afw.bld", 
                          man.defaultID("bld", "afw", "4.5", "external", "Linux"))
        self.assertEquals("lsstbuild:afw-4.5/afw.bld", 
                          man.defaultID("bld", "afw", "4.5", path="afw-4.5"))

    def testAddRecord(self):
        man = Manifest("numpy", "1.6.1+1")
        self.assert_(not man.hasProduct("python"))

        man.addRecord("python", "generic", "2.7.2+2", 
                      "external/python/2.7.2/python.table", 
                      "external/python/2.7.2+2", 
                      "lsstbuild:external/python/2.7.2/python.bld")
        self.assert_(man.hasProduct("python"))
        self.assert_(man.hasRecord("python", "generic", "2.7.2+2"))
        self.assert_(not man.hasRecord("python", "generic", "2.7.2"))

        rec = man.getRecord("python", "2.7.2+2")
        self.assert_(rec)
        dep = Dependency(rec)
        self.assertEquals("python", dep.data[dep.NAME])
        self.assertEquals("generic", dep.data[dep.FLAVOR])
        self.assertEquals("2.7.2+2", dep.data[dep.VERSION])
        self.assertEquals("external/python/2.7.2/python.table", 
                          dep.data[dep.TABLEFILE])
        self.assertEquals("external/python/2.7.2+2", dep.data[dep.INSTALLDIR])
        self.assertEquals("lsstbuild:external/python/2.7.2/python.bld", 
                          dep.data[dep.INSTALLID])

    def testAddLSSTRecord(self):
        man = Manifest("numpy", "1.6.1+1")
        self.assert_(not man.hasProduct("python"))

        man.addLSSTRecord("python", "2.7.2", "external", build=2)
        self.assert_(man.hasProduct("python"))
        self.assert_(man.hasRecord("python", "generic", "2.7.2+2"))
        self.assert_(not man.hasRecord("python", "generic", "2.7.2"))

        rec = man.getRecord("python", "2.7.2+2")
        self.assert_(rec)
        dep = Dependency(rec)
        self.assertEquals("python", dep.data[dep.NAME])
        self.assertEquals("generic", dep.data[dep.FLAVOR])
        self.assertEquals("2.7.2+2", dep.data[dep.VERSION])
        self.assertEquals("external/python/2.7.2/python.table", 
                          dep.data[dep.TABLEFILE])
        self.assertEquals("external/python/2.7.2+2", dep.data[dep.INSTALLDIR])
        self.assertEquals("lsstbuild:external/python/2.7.2/python-2.7.2.tar.gz", 
                          dep.data[dep.INSTALLID])

    def testAddExtRecord(self):
        man = Manifest("numpy", "1.6.1+1")
        self.assert_(not man.hasProduct("python"))

        man.addExtRecord("python", "2.7.2", build=2, id="bld")
        self.assert_(man.hasProduct("python"))
        self.assert_(man.hasRecord("python", "generic", "2.7.2+2"))
        self.assert_(not man.hasRecord("python", "generic", "2.7.2"))

        rec = man.getRecord("python", "2.7.2+2")
        self.assert_(rec)
        dep = Dependency(rec)
        self.assertEquals("python", dep.data[dep.NAME])
        self.assertEquals("generic", dep.data[dep.FLAVOR])
        self.assertEquals("2.7.2+2", dep.data[dep.VERSION])
        self.assertEquals("external/python/2.7.2/python.table", 
                          dep.data[dep.TABLEFILE])
        self.assertEquals("external/python/2.7.2+2", dep.data[dep.INSTALLDIR])
        self.assertEquals("lsstbuild:external/python/2.7.2/python.bld", 
                          dep.data[dep.INSTALLID])

    def testAddSelfRecord(self):
        man = Manifest("python", "2.7.2+5", "external")
        self.assert_(not man.hasProduct("python"))
        self.assert_(man.getSelf() is None)

        # pdb.set_trace()
        man.addSelfRecord();
        self.assert_(man.hasProduct("python"))

        rec = man.getSelf()
        self.assert_(rec)
        dep = Dependency(rec)
        self.assertEquals("python", dep.data[dep.NAME])
        self.assertEquals("generic", dep.data[dep.FLAVOR])
        self.assertEquals("2.7.2+5", dep.data[dep.VERSION])
        self.assertEquals("external/python/2.7.2/python.table", 
                          dep.data[dep.TABLEFILE])
        self.assertEquals("external/python/2.7.2+5", dep.data[dep.INSTALLDIR])
        self.assertEquals("lsstbuild:external/python/2.7.2/python-2.7.2.tar.gz", 
                          dep.data[dep.INSTALLID])
        
    def testFromFile(self):
        path = os.path.join(self.server, "manifests", "numpy-1.6.1+1.manifest")
        man = Manifest.fromFile(path)

        id = man.getNameVerFlav()
        self.assertEquals("numpy", id[0])
        self.assertEquals("1.6.1+1", id[1])
        self.assertEquals("generic", id[2])

        self.assert_(man.hasProduct("tcltk"))
        self.assert_(man.hasProduct("python"))
        self.assert_(man.hasProduct("numpy"))

        rec = man.getRecord("python", "2.7.2+1")
        self.assert_(rec)
        dep = Dependency(rec)
        self.assertEquals("python", dep.data[dep.NAME])
        self.assertEquals("generic", dep.data[dep.FLAVOR])
        self.assertEquals("2.7.2+1", dep.data[dep.VERSION])
        self.assertEquals("external/python/2.7.2/python.table", 
                          dep.data[dep.TABLEFILE])
        self.assertEquals("external/python/2.7.2+1", dep.data[dep.INSTALLDIR])
        self.assertEquals("lsstbuild:external/python/2.7.2/python.bld", 
                          dep.data[dep.INSTALLID])

    def testRoundTrip(self):
        path = os.path.join(self.server, "manifests", "numpy-1.6.1+1.manifest")
        filecontents = StringIO()
        line = None
        with open(path) as fd:
            for line in fd:
                filecontents.write(line)

        man = Manifest.fromFile(path)
        mancontents = StringIO()
        man.write(mancontents)

        self.assertEquals(filecontents.getvalue(), mancontents.getvalue())

class DeployedManifestsTestCase(unittest.TestCase):

    def setUp(self):
        self.server = os.path.join(testdir, "server")
        self.mandir = os.path.join(self.server, "manifests")
        self.deployed = DeployedManifests(self.mandir)

    def tearDown(self):
        pass

    def testManifestFilename(self):
        self.assertEquals("goob-8.9.1.manifest", 
                          self.deployed.manifestFilename("goob", "8.9.1"))
        self.assertEquals("goofy/goob-8.9.1.manifest", 
                          self.deployed.manifestFilename("goob", "8.9.1", "goofy"))

    def testProductFromFilename(self):
        self.assertEquals(("sconsUtils", "3.4.5+1"), 
                          self.deployed.productFromFilename("sconsUtils-3.4.5+1.manifest"))
        self.assertEquals(("python", "2.7.2+2"), 
                          self.deployed.productFromFilename("python-2.7.2+2.manifest"))
        self.assertEquals(("lsst", "4.4.0.1+1"), 
                          self.deployed.productFromFilename("lsst-4.4.0.1+1.manifest"))

    def testListAll(self):
        prods = self.deployed.listAll()
        self.assertEquals(22, len(prods))

        lsstp = filter(lambda p: p[0] == "lsst", prods)
        self.assertEquals(2, len(lsstp))
        versions = map(lambda p: p[1], lsstp)
        self.assert_("1.0.2+1" in versions)
        self.assert_("4.4.0.1+1" in versions)

    def testGetVersions(self):
        versions = self.deployed.getVersions("lsst")
        self.assert_(versions is not None)
        self.assertEquals(2, len(versions))
        self.assert_("1.0.2+1" in versions)
        self.assert_("4.4.0.1+1" in versions)

        self.assert_(self.deployed.getVersions("goob") == [])
        
    def testGetLatestVersion(self):
        self.assertEquals("2.7.2+2", self.deployed.getLatestVersion("python"))
        self.assertEquals("1.2.19", self.deployed.getLatestVersion("eups"))
        self.assertEquals("4.4.0.1+1", self.deployed.getLatestVersion("lsst"))
        self.assertRaises(DeployedProductNotFound, 
                          self.deployed.getLatestVersion, "goob")
        
    def testLatestProducts(self):
        prods = self.deployed.latestProducts()
        self.assertEquals(17, len(prods))
        names = set(map(lambda p: p[0], prods))
        self.assertEquals(17, len(names))
        self.assertEquals("2.7.2+2", 
                          map(lambda p: p[1], 
                              filter(lambda k: k[0] == "python", prods))[0])
        self.assertEquals("1.2.19", 
                          map(lambda p: p[1], 
                              filter(lambda k: k[0] == "eups", prods))[0])
        self.assertEquals("4.4.0.1+1", 
                          map(lambda p: p[1], 
                              filter(lambda k: k[0] == "lsst", prods))[0])

    def testGetLatestBuildNumber(self):
        self.assertEquals(2, self.deployed.getLatestBuildNumber("python", "2.7.2"))
        self.assertEquals(1, self.deployed.getLatestBuildNumber("python", "2.7.1"))
        self.assertEquals(1, self.deployed.getLatestBuildNumber("python", "2.7.1+3"))
        self.assertEquals(1, self.deployed.getLatestBuildNumber("lsst", "4.4.0.1"))
        self.assertRaises(DeployedProductNotFound, 
                          self.deployed.getLatestBuildNumber, "goob", "1.0")

    def testGetManifest(self):
        man = self.deployed.getManifest("numpy", "1.6.1+1")
        
        id = man.getNameVerFlav()
        self.assertEquals("numpy", id[0])
        self.assertEquals("1.6.1+1", id[1])
        self.assertEquals("generic", id[2])

        self.assert_(man.hasProduct("tcltk"))
        self.assert_(man.hasProduct("python"))
        self.assert_(man.hasProduct("numpy"))

    def testDependsOn(self):
        deps = self.deployed.dependsOn("numpy", "1.6.1+1")
        self.assertEquals(3, len(deps))
        pnames = map(lambda p: p[0], deps)
        self.assert_("matplotlib" in pnames)
        self.assert_("pyfits" in pnames)
        self.assert_("numpy" in pnames)
        
        deps = self.deployed.dependsOn("tcltk", "8.5.9+1")
        self.assertEquals(9, len(deps))
        pydep = map(lambda y: y[1], 
                    filter(lambda p: p[0] == "python", deps))
        self.assertEquals("2.7.2+2", pydep[0])

        deps = self.deployed.dependsOn("matplotlib")
        self.assertEquals(1, len(deps))

if __name__ == "__main__":
    unittest.main()
