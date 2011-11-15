#! /bin/bash
#
# use SVN to extract a product
# @param directory  path to directory containing package file.  The whole 
#                     path and the contains of the directory will be 
#                     replicated.
function copyPackage {
    tar cf - $1 | ssh $packageServerName 'cd $testPackageServerDir; tar xf -'
    return $?
}

packageServerName=dev.lsstcorp.org
testPackageServerPath=pkgs/test/w12a
testPackageServerDir=softstack/$testPackageServerPath
testPackageServerURL=http://$packageServerName/$testPackageServerPath

