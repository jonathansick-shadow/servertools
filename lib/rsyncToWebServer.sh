#! /bin/bash
#
# copy all recent changes from the local server staging area to the actual
# web server (on a remote machine)
#
function rsyncToWebServer {

    echo rsync -avz --exclude=.git\* --exclude=\*~ $localServerMirror/ ${packageServerName}:$testPackageServerDir
    rsync -avz --exclude=.git\* --exclude=\*~ $localServerMirror/ ${packageServerName}:$testPackageServerDir || return 1

    return 0
}

packageServerName=dev.lsstcorp.org
testPackageServerPath=pkgs/test/w12
testPackageServerDir=softstack/$testPackageServerPath
localServerMirror=$stackbase/www
