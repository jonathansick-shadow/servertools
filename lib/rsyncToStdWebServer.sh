#! /bin/bash
#
# copy all recent changes from the local server staging area to the actual
# web server (on a remote machine)
#
function rsyncToStdWebServer {

    echo rsync -avz --exclude=.git\* --exclude=/newinstall.sh --exclude=\*~ $localServerMirror/ ${packageServerName}:$testPackageServerDir
    rsync -avz --exclude=.git\* --exclude=/newinstall.sh --exclude=\*~ $localServerMirror/ ${packageServerName}:$testPackageServerDir || return 1

    echo ssh $packageServerName \"cd $testPackageServerDir\; sed -e \'/EUPS distribution/ s/current/stable/\' current.list \> stable.list\"
    ssh $packageServerName "cd $testPackageServerDir; sed -e '/EUPS distribution/ s/current/stable/' current.list > stable.list" || return 2

    return 0
}

packageServerName=dev.lsstcorp.org
testPackageServerPath=pkgs/std/w12
testPackageServerDir=softstack/$testPackageServerPath
localServerMirror=$stackbase/www
