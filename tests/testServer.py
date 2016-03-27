"""
test the server module
"""

import os
import sys
import re
import unittest
import pdb
from cStringIO import StringIO

from lsstdistrib.server import Repository

testdir = os.path.join(os.getcwd(), "tests")


class RepositoryTestCase(unittest.TestCase):

    def setUp(self):
        self.serverroot = os.path.join(testdir, "server")
        self.repos = Repository(self.serverroot)

    def tearDown(self):
        pass

    def testGet(self):
        self.assertEquals(os.path.join(self.serverroot, "manifests"),
                          self.repos.getManifestDir())
        self.assertEquals(os.path.join(self.serverroot, "external"),
                          self.repos.getExternalProductRoot())
        self.assertEquals(os.path.join(self.serverroot, "current.list"),
                          self.repos.getTagListFile('current'))
        self.assertEquals(os.path.join(self.serverroot, "manifests"),
                          self.repos.getManifestDir())
        self.assertEquals(os.path.join(self.serverroot,
                                       "manifests/python-2.7.2.manifest"),
                          self.repos.getManifestFile("python", "2.7.2"))

    def testGetProductDir(self):
        self.assertEquals(os.path.join(self.serverroot, "lsst/4.4.0.1"),
                          self.repos.getProductDir("lsst", "4.4.0.1+1",
                                                   category=''))
        self.assertEquals(os.path.join(self.serverroot, "external/lsst/4.4.0.1"),
                          self.repos.getProductDir("lsst", "4.4.0.1+1",
                                                   category="external"))
        self.assertEquals(os.path.join(self.serverroot, "pseudo/lsst/4.4.0.1"),
                          self.repos.getProductDir("lsst", "4.4.0.1+1",
                                                   category="pseudo"))
        self.assertEquals(os.path.join(self.serverroot, "lsst/4.4.0.1"),
                          self.repos.getProductDir("lsst", "4.4.0.1+1"))

        self.assertEquals(os.path.join(self.serverroot, "external/python/2.7.2"),
                          self.repos.getProductDir("python", "2.7.2"))

    def testGetUndepMan4(self):
        files = self.repos.getUndeployedManifestsFor("python", "2.7.2")
        self.assertEquals(2, len(files))
        self.assert_("b1.manifest" in files)
        self.assert_("b2.manifest" in files)

    def testGetLatestUndepMan4(self):
        self.assertEquals("b2.manifest",
                          self.repos.getLatestUndeployedManifestFile("python", "2.7.2"))
        self.assertEquals("b1.manifest",
                          self.repos.getLatestUndeployedManifestFile("numpy", "1.6.1"))

    def testGetLatestBuildN(self):
        self.assertEquals(2,
                          self.repos.getLatestUndeployedBuildNumber("python", "2.7.2+1"))
        self.assertEquals(1,
                          self.repos.getLatestUndeployedBuildNumber("numpy", "1.6.1+1"))

    def testNextBuildN(self):
        self.assertEquals("b3.manifest",
                          self.repos.getNextUndeployedBuildFilename("python", "2.7.2"))
        self.assertEquals("b2.manifest",
                          self.repos.getNextUndeployedBuildFilename("numpy", "1.6.1+1"))

if __name__ == "__main__":
    unittest.main()
