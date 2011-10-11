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
        shutil.copyfile(os.path.join(self.serverroot,
                                     "external/numpy/1.6.1/b1.manifest"),
                        os.path.join(self.serverroot,
                                     "external/numpy/1.6.1/b2.manifest"))

        self.dest = os.path.join(self.serverroot,
                                 "manifests/numpy-1.6.1+2.manifest")
                        
    def tearDown(self):
        if os.path.exists(self.serverroot):
            shutil.rmtree(self.serverroot)

    def testScript(self):
        exe = "bin/releaseman.py"
        cmd = [exe, "-d", self.serverroot]
        cmd.append("external/numpy/1.6.1/b2.manifest")

        self.assert_(not os.path.exists(self.dest))

        do = Popen(cmd, executable=exe, stdout=PIPE, stderr=PIPE)
        (cmdout, cmderr) = do.communicate()
        self.assert_(not do.returncode)

        updatedFiles = cmdout.strip().split("\n")
        self.assert_(os.path.exists(self.dest))



if __name__ == "__main__":
    unittest.main()

