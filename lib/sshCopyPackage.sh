#! /bin/bash
#
# use SVN to extract a product
# @param directory  path to directory containing package file.  The whole 
#                     path and the contains of the directory will be 
#                     replicated.
function copyPackage {
    echo tar cf - $1 \| ssh $packageServerName "\"cd $testPackageServerDir; tar xf -\""
    tar cf - $1 | ssh $packageServerName "cd $testPackageServerDir; tar xf -"
    manfile=`manifestForVersion $version`
    ssh $packageServerName $releaseCmd $prodname $version $manfile
    
    return $?
}

packageServerName=dev.lsstcorp.org
testPackageServerPath=pkgs/test/w12a
testPackageServerDir=softstack/$testPackageServerPath
testPackageServerURL=http://$packageServerName/$testPackageServerPath
releaseCmd="/home/rplante/svn/servertools-trunk/bin/remoteRelease.sh -d $testPackageServerDir"
# canonicalTag=current