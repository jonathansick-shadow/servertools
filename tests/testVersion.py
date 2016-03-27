"""
test the version module
"""
import os
import sys
import re
import unittest
import pdb

from lsstdistrib.version import VersionCompare, incrementBuild, substituteBuild, \
    splitToReleaseBuild, baseVersion


class FunctionsTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testSplit(self):
        invers = "4.5.1.1+23"
        out = splitToReleaseBuild(invers)
        self.assertEquals(len(out), 3)
        self.assertEquals(out[0], "4.5.1.1")
        self.assertEquals(out[1], "+")
        self.assertEquals(out[2], "23")

        invers = "1.2.44"
        out = splitToReleaseBuild(invers)
        self.assertEquals(len(out), 3)
        self.assertEquals(out[0], "1.2.44")
        self.assert_(out[1] is None)
        self.assert_(out[2] is None)

        invers = "4.5.1.1svn23b3"
        out = splitToReleaseBuild(invers)
        self.assertEquals(len(out), 3)
        self.assertEquals(out[0], "4.5.1.1")
        self.assertEquals(out[1], "svn")
        self.assertEquals(out[2], "23b3")

        invers = "4.5.1.1-"
        out = splitToReleaseBuild(invers)
        self.assertEquals(len(out), 3)
        self.assertEquals(out[0], "4.5.1.1")
        self.assertEquals(out[1], "-")
        self.assertEquals(out[2], "")

    def testBaseVersion(self):
        self.assertEquals("4.5.1.1", baseVersion("4.5.1.1+23"))
        self.assertEquals("1.2.44", baseVersion("1.2.44"))
        self.assertEquals("4.5.1.1", baseVersion("4.5.1.1svn23b3"))
        self.assertEquals("4.5.1.1", baseVersion("4.5.1.1-"))

    def testSubstituteBuild(self):
        self.assertEquals("4.5.1.1+34", substituteBuild("4.5.1.1+23", 34))
        self.assertEquals("4.5.1.1-34", substituteBuild("4.5.1.1-23", 34))
        self.assertEquals("1.2.44+2", substituteBuild("1.2.44", 2))
        self.assertEquals("4.5.1.1svn23b4", substituteBuild("4.5.1.1svn23b3", 4))
        self.assertEquals("4.5.1.1svn4", substituteBuild("4.5.1.1svn23", 4))
        self.assertEquals("4.5.1.1+4", substituteBuild("4.5.1.1svn23", 4, True))
        self.assertEquals("4.5.1.1svn23+4", substituteBuild("4.5.1.1svn23b3", 4, True))
        self.assertEquals("4.5.1.1-2", substituteBuild("4.5.1.1-", 2))
        self.assertEquals("4.5.1.1+2", substituteBuild("4.5.1.1-", 2, True))

    def testIncrementBuild(self):
        self.assertEquals("4.5.1.1+24", incrementBuild("4.5.1.1+23"))
        self.assertEquals("4.5.1.1-24", incrementBuild("4.5.1.1-23"))
        self.assertEquals("1.2.44+1", incrementBuild("1.2.44"))
        self.assertEquals("4.5.1.1svn23b4", incrementBuild("4.5.1.1svn23b3"))
        self.assertEquals("4.5.1.1svn24", incrementBuild("4.5.1.1svn23"))
        self.assertEquals("4.5.1.1+1", incrementBuild("4.5.1.1svn23", True))
        self.assertEquals("4.5.1.1svn23+1", incrementBuild("4.5.1.1svn23b3", True))
        self.assertEquals("4.5.1.1-1", incrementBuild("4.5.1.1-"))
        self.assertEquals("4.5.1.1+1", incrementBuild("4.5.1.1-", True))


class VersionCompareTestCase(unittest.TestCase):

    def setUp(self):
        self.vcmp = VersionCompare()

    def tearDown(self):
        pass

    def testCompareBase(self):
        self.assertEquals(-1, self.vcmp("1", "2"))
        self.assertEquals(-1, self.vcmp("1.0", "2.3.1"))
        self.assertEquals(-1, self.vcmp("1.0.2", "2.3.1"))
        self.assertEquals(-1, self.vcmp("1.0.2.7", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.2.2.7", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.3.0", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.3.0.7", "2.3.1"))

        self.assertEquals(-1, self.vcmp("1.0+1", "2.3.1"))
        self.assertEquals(-1, self.vcmp("1.0.2+1", "2.3.1"))
        self.assertEquals(-1, self.vcmp("1.0.2.7+1", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.2.2.7+1", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.3.0+1", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.3.0.7+1", "2.3.1"))

        self.assertEquals(-1, self.vcmp("1.0svn4355", "2.3.1"))
        self.assertEquals(-1, self.vcmp("1.0.2svn4355", "2.3.1"))
        self.assertEquals(-1, self.vcmp("1.0.2.7svn4355", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.2.2.7svn4355", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.3.0svn4355", "2.3.1"))
        self.assertEquals(-1, self.vcmp("2.3.0.7svn4355", "2.3.1"))

        self.assertEquals(0, self.vcmp("2.2.2.7", "2.2.2.7"))

        self.assertEquals(+1, self.vcmp("2", "1"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0.2"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0.2.7"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.2.2.7"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.3.0"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.3.0.7"))

        self.assertEquals(+1, self.vcmp("2.3.1", "1.0+1"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0.2+1"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0.2.7+1"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.2.2.7+1"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.3.0+1"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.3.0.7+1"))

        self.assertEquals(+1, self.vcmp("2.3.1", "1.0svn4355"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0.2svn4355"))
        self.assertEquals(+1, self.vcmp("2.3.1", "1.0.2.7svn4355"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.2.2.7svn4355"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.3.0svn4355"))
        self.assertEquals(+1, self.vcmp("2.3.1", "2.3.0.7svn4355"))

    def testCompareQual(self):
        self.assertEquals(+1, self.vcmp("1.0+3", "1.0-5"))
        self.assertEquals(+1, self.vcmp("1.0+", "1.0-"))
        self.assertEquals(+1, self.vcmp("1.0.2+3", "1.0.2-5"))
        self.assertEquals(+1, self.vcmp("1.0.2+3", "1.0.2svn5"))
        self.assertEquals(+1, self.vcmp("1.0.2-3", "1.0.2svn5"))

        self.assertEquals(0, self.vcmp("1.0+", "1.0+"))
        self.assertEquals(0, self.vcmp("1.0-", "1.0-"))
        self.assertEquals(0, self.vcmp("1.0svn", "1.0svn"))

        self.assertEquals(-1, self.vcmp("1.0-5", "1.0+3"))
        self.assertEquals(-1, self.vcmp("1.0-", "1.0+"))
        self.assertEquals(-1, self.vcmp("1.0.2-5", "1.0.2+3"))
        self.assertEquals(-1, self.vcmp("1.0.2svn5", "1.0.2+3"))
        self.assertEquals(-1, self.vcmp("1.0.2svn5", "1.0.2-3"))

    def testCompareBuild(self):
        self.assertEquals(-1, self.vcmp("1.0+3", "1.0+6"))
        self.assertEquals(-1, self.vcmp("1.0+23", "1.0+36"))
        self.assertEquals(-1, self.vcmp("1.0-23", "1.0-36"))
        self.assertEquals(-1, self.vcmp("1.0-23b1", "1.0-23b3"))

        self.assertEquals(0, self.vcmp("1.0+6", "1.0+6"))
        self.assertEquals(0, self.vcmp("1.0-6", "1.0-6"))
        self.assertEquals(0, self.vcmp("1.0svn6", "1.0svn6"))

        self.assertEquals(+1, self.vcmp("1.0+6", "1.0+3"))
        self.assertEquals(+1, self.vcmp("1.0+36", "1.0+23"))
        self.assertEquals(+1, self.vcmp("1.0-36", "1.0-23"))
        self.assertEquals(+1, self.vcmp("1.0-23b3", "1.0-23b1"))


if __name__ == "__main__":
    unittest.main()
