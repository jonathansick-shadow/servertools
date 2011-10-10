"""
test the release module
"""

import os, sys, re, unittest, pdb
from cStringIO import StringIO

from lsstdistrib.release import UpdateDependents

testdir = os.path.join(os.getcwd(), "tests")

class UpdateDependentsCheckTestCase(unittest.TestCase):

    def setUp(self):
        self.serverroot = os.path.join(testdir, "server")

    def tearDown(self):
        pass

    def testDependencies(self):
        rel = UpdateDependents([("numpy", "1.6.1+1")], self.serverroot)
        deps = rel.getDependents();
        self.assertEquals(2, len(deps.keys()))






if __name__ == "__main__":
    unittest.main()

