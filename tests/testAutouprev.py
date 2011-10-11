"""
test the autouprev script
"""

import os, sys, re, unittest, pdb, shutil
from subprocess import Popen, PIPE

testdir = os.path.join(os.getcwd(), "tests")

class AutouprevTestCase(unittest.TestCase):

    def setUp(self):
        origroot = os.path.join(testdir, "server")
        self.serverroot = os.path.join(testdir, "server-tmp")

        self.tearDown()
        shutil.copytree(origroot, self.serverroot, True)

    def tearDown(self):
        if os.path.exists(self.serverroot):
            shutil.rmtree(self.serverroot)

    def testScript(self):
        exe = "bin/autouprev.py"
        cmd = [exe, "-d", self.serverroot]
        cmd.append("external/numpy/1.6.1+1")

        do = Popen(cmd, executable=exe, stdout=PIPE, stderr=PIPE)
        (cmdout, cmderr) = do.communicate()
        self.assert_(not do.returncode)

        updatedFiles = cmdout.strip().split("\n")
        self.assertEquals(2, len(updatedFiles))
        self.assert_("external/pyfits/2.4.0/b2.manifest" in updatedFiles)
        self.assert_("external/matplotlib/1.0.1/b2.manifest" in updatedFiles)



if __name__ == "__main__":
    unittest.main()

