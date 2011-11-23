#! /bin/bash
#
# deploy a package to a test server.  This implementation copies it to a 
# local directory which get rsynced to a remote server. 
# @param directory  path to directory containing package file.  The whole 
#                     path and the contents of the directory will be 
#                     replicated.
# @param tagname    if provided, assign the given server tag to the product
function copyPackage {
    [ -w "$localServerMirror" ] || {
        echo "${prog}: Configuration problem: localServerMirror not writable:"\
             $localServerMirror
        return 1
    }
    echo "tar cf - $1 | (cd $localServerMirror; tar xf -)"
    { tar cf - $1 | (cd $localServerMirror && tar xf -); } || return 2
    manfile=`manifestForVersion $version`

    # release the package
    echo cp $localServerMirror/$prodname/$taggedas/$manfile \
            $localServerMirror/manifests/$prodname-$version.manifest
    cp $localServerMirror/$prodname/$taggedas/$manfile \
       $localServerMirror/manifests/$prodname-$version.manifest || return 3

    # eups-tag it if desired
    [ -n "$2" ] && {
        echo $tagReleaseCmd -d $localServerMirror $prodname $version $2
        $tagReleaseCmd -d $localServerMirror $prodname $version $2 || return 4
    }

    echo rsync -avz --exclude=.git\* --exclude=\*~ $localServerMirror/ ${packageServerName}:$testPackageServerDir
    rsync -avz --exclude=.git\* --exclude=\*~ $localServerMirror/ ${packageServerName}:$testPackageServerDir || return 5

    return 0
}

packageServerName=dev.lsstcorp.org
testPackageServerPath=pkgs/test/w12
testPackageServerDir=softstack/$testPackageServerPath
testPackageServerURL=http://$packageServerName/$testPackageServerPath
localServerMirror=$stackbase/www
tagReleaseCmd=tagRelease.py
canonicalTag=current
