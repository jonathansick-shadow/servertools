"""
test the release module
"""

import os, sys, re, unittest, pdb, shutil
from cStringIO import StringIO

from lsstdistrib.release import UpdateDependents
from lsstdistrib.manifest import Manifest, DeployedProductNotFound

testdir = os.path.join(os.getcwd(), "tests")

class UpdateDependentsCheckTestCase(unittest.TestCase):

    def setUp(self):
        self.serverroot = os.path.join(testdir, "server")

    def tearDown(self):
        pass

    def testDependents(self):
        rel = UpdateDependents([("numpy", "1.6.1+1")], self.serverroot)
        deps = rel.getDependents();
        self.assertEquals(2, len(deps.keys()))
        pnames = deps.keys()
        self.assert_("pyfits" in deps.keys())
        self.assert_("matplotlib" in deps.keys())
        self.assertEquals("2.4.0+1", deps.get("pyfits"))
        self.assertEquals("1.0.1+1", deps.get("matplotlib"))

        rel = UpdateDependents([("tcltk", "8.5.9+1")], self.serverroot)
        deps = rel.getDependents();
        self.assertEquals(8, len(deps.keys()))
        self.assertEquals("2.7.2+2", deps.get("python"))

    def testUpgBuildNum(self):
        rel = UpdateDependents([("numpy", "1.6.1+1")], self.serverroot)
        nums = rel.setUpgradedBuildNumbers()
        self.assert_(all(map(lambda p: p == 2, nums.values())))

        rel = UpdateDependents([("tcltk", "8.5.9+1")], self.serverroot)
        nums = rel.setUpgradedBuildNumbers()
        self.assertEquals(8, len(nums.keys()))
        self.assertEquals(2, nums.get('numpy'))
        self.assertEquals(3, nums.get('python'))

    def testUpgManRecs(self):
        rel = UpdateDependents([("numpy", "1.6.1+1")], self.serverroot)

        rec = rel.getUpdatedRecordFor("pyfits", "2.4.0+1", 2)
        self.assertEquals(6, len(rec))
        self.assertEquals("pyfits", rec[0])
        self.assertEquals("generic", rec[1])
        self.assertEquals("2.4.0+2", rec[2])
        self.assertEquals("external/pyfits/2.4.0/pyfits.table", rec[3])
        self.assertEquals("external/pyfits/2.4.0+2", rec[4])
        self.assertEquals("lsstbuild:external/pyfits/2.4.0/pyfits-2.4.0.tar.gz", rec[5])

        recs = rel.setUpgradedManifestRecords()
        self.assertEquals(3, len(recs.keys()))
        self.assert_(recs.has_key("pyfits"))
        self.assertEquals("2.4.0+2", recs['pyfits'][2])
        self.assert_(recs.has_key("matplotlib"))
        self.assert_(recs.has_key("numpy"))
        
        rel = UpdateDependents([("tcltk", "8.5.9+1")], self.serverroot)
        recs = rel.setUpgradedManifestRecords()
        self.assertEquals(9, len(recs.keys()))
        self.assert_(recs.has_key("tcltk"))
        self.assert_(recs.has_key("python"))
        self.assertEquals("2.7.2+3", recs['python'][2])

    def testCreateManifest(self):
        rel = UpdateDependents([("numpy", "1.6.1+1")], self.serverroot)

        man = rel.createUpgradedManifest("pyfits")
        rec = man.getProduct("pyfits")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.4.0+2")
        rec = man.getProduct("python")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.7.2+1")

        rel = UpdateDependents([("tcltk", "8.5.9+1")], self.serverroot)
        man = rel.createUpgradedManifest("pyfits")
        rec = man.getProduct("pyfits")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.4.0+2")
        rec = man.getProduct("python")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.7.2+3")

        self.assertRaises(DeployedProductNotFound, 
                          rel.createUpgradedManifest, "goob")

    def testMulti(self):
        rel = UpdateDependents([("numpy", "1.6.1+1"), 
                                ("python", "2.7.2+2")],
                               self.serverroot)

        deps = rel.getDependents()
        self.assert_(deps.has_key("numpy"))

        man = rel.createUpgradedManifest("pyfits")
        rec = man.getProduct("pyfits")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.4.0+2")
        man = rel.createUpgradedManifest("numpy")
        rec = man.getProduct("numpy")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "1.6.1+2")
        


class UpdateDependentsWriteTestCase(unittest.TestCase):

    def setUp(self):
        origroot = os.path.join(testdir, "server")
        self.serverroot = os.path.join(testdir, "server-tmp")

        self.tearDown()
        shutil.copytree(origroot, self.serverroot, True)

    def tearDown(self):
        if os.path.exists(self.serverroot):
            shutil.rmtree(self.serverroot)

    def testWrite1(self):
        self.assertEquals("server-tmp", os.path.basename(self.serverroot))
        self.assert_(os.path.exists(self.serverroot))

        newpyfitsfile = "tests/server-tmp/external/pyfits/2.4.0/b2.manifest"
        newmplfile = "tests/server-tmp/external/matplotlib/1.0.1/b2.manifest"

        self.assert_(not os.path.exists(newpyfitsfile))
        self.assert_(not os.path.exists(newmplfile))

        rel = UpdateDependents([("numpy", "1.6.1+1")], self.serverroot)
        updated = rel.createManifests()
        self.assertEquals(2, len(updated))

        prod = filter(lambda p: p[0] == "pyfits", updated)
        self.assertEquals(1, len(prod))
        prod = prod[0]
        self.assertEquals("2.4.0", prod[1])
        self.assertEquals(2, prod[2])
        self.assert_(prod[3].endswith(newpyfitsfile))
        prod = filter(lambda p: p[0] == "matplotlib", updated)
        self.assertEquals(1, len(prod))
        prod = prod[0]
        self.assertEquals("1.0.1", prod[1])
        self.assertEquals(2, prod[2])
        self.assert_(prod[3].endswith(newmplfile))

        self.assert_(os.path.exists(newpyfitsfile))
        self.assert_(os.path.exists(newmplfile))

        man = Manifest.fromFile(newpyfitsfile)
        rec = man.getProduct("pyfits")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.4.0+2")
        rec = man.getProduct("python")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "2.7.2+1")

        man = Manifest.fromFile(newmplfile)
        rec = man.getProduct("matplotlib")
        self.assert_(rec is not None)
        self.assertEquals(rec[2], "1.0.1+2")





if __name__ == "__main__":
    unittest.main()

