#! /bin/bash
#
# copy all recent changes from the local server staging area to the actual
# web server (on a remote machine)
#
function rsyncToWebServer {

    local delete=
    [ -n "rsyncremove" ] && delete="--delete"
    local subdir=
    [ -n "$1" ] && subdir=/$1

    echo rsync -avz $delete --exclude=.git\* --exclude=\*~ $localServerMirror$subdir/ ${packageServerName}:$testPackageServerDir$subdir
    rsync -avz $delete --exclude=.git\* --exclude=\*~ $localServerMirror$subdir/ ${packageServerName}:$testPackageServerDir$subdir || return 1

    return 0
}

packageServerName=dev.lsstcorp.org
testPackageServerPath=pkgs/test/w12
testPackageServerDir=softstack/$testPackageServerPath
localServerMirror=$stackbase/www
