#! /bin/bash -i
#
# submitRelease.sh -- request the release of a tagged version of a product
# 
# This script is intended to run as a user who has permission to write to 
# the distribution server and to the reference software stack.  Non-privileged
# users would invoke this via a wrapper script (submitrelease)
#
SHELL=/bin/bash
refstack=/lsst/DC3/stacks/default
workdir=/lsst/DC3/distrib/default/submitRelease
stagesrvr=/lsst/DC3/distrib/w12/www
startdir=$PWD
prog=`basename $0 | sed -e 's/\..*$//'`

[ -n "$DEVENV_SERVERTOOLS_DIR" ] || {
    echo "${prog}: devenv_servertools not setup"
    exit 1
}
libdir="$DEVENV_SERVERTOOLS_DIR/lib"
reposExtractLib="$libdir/gitReposExtract.sh"  # default; override in conf
copyPackageLib="$libdir/rsyncCopyPackage.sh"  # default; override in conf
releaseFunctionLib="$libdir/releaseFunction.sh"

function usage {
    echo Usage: `basename $0` "[-c FILE -r DIR -j NUM -t TAGS -iVCh]" product version "[manifest]"
}

function help {
    usage
    echo 
    echo "Releases a tagged version of a product after confirming a successful"
    echo "build.  If manifest file is not provided, one is generated assuming"
    echo "current versions of product's dependencies."
    echo 
    echo "Options:"
    echo "  -r DIR      the reference stack directory"
    echo "  -t TAG[,TAG]  when creating a manifest on the fly (i.e. manifest is not"
    echo "                provided) prefer dependencies with these (server-assign) tags."
    echo "  -i          ignore failed tests: don't let failed tests prevent release"
    echo "  -n          preserve all generated release artifacts"
    echo "  -j NUM      use NUM threads when building"
    echo "  -V          force validation: check that the tests pass even if the tests"
    echo "                were run implicitly when a default manifest was created."
    echo "  -C          prep but do not commit this release (used for testing purposes)"
    echo "  -T          deploy to test server only"
    echo "  -c FILE     the configuration file to use"
    echo "  -w DIR      a 'work' directory to use for private scratch"
    echo "  -U USER     identify the user running this command"
    echo "  -h          print this help and exit"
}

configfile=$DEVENV_SERVERTOOLS_DIR/conf/submitRelease_conf.sh
usebuildthreads=4
ignorefailedtests=
testsHaveFailed=
checkTests=
reftags=
testserver=
asuser=

while getopts "c:j:r:w:t:U:iVCTnh" opt; do
  case $opt in 
    c)
      configfile=$OPTARG 
      [ -f "$configfile" ] || {
          echo "${prog}: config file not found:" $configfile
          exit 1
      }
      ;;
    r)
      refstack=$OPTARG ;;
    w)
      workdir=$OPTARG ;;
    j)
      usebuildthreads=$OPTARG ;;
    i)
      ignorefailedtests=1 ;;
    V)
      checkTests=1 ;;
    C)
      nocommit=1 ;;
    n)
      noclean=1 ;;
    t)
      reftags=$OPTARG ;;
    T)
      testserver=1 ;;
    U)
      asuser=$OPTARG ;;
    h)
      help
      exit 0 ;;
  esac
done
shift $(($OPTIND - 1))

[ $# -lt 1 ] && {
    echo "${prog}: Missing arguments: product version"
    usage
    exit 1
}
[ $# -lt 2 ] && {
    echo "${prog}: Missing argument: version"
    usage
    exit 1
}

[ -e "$conffile" ] && \
    . $configfile
[ -e "$releaseFunctionLib" ] || {
    echo "${prog}:  releaseFunction library does not exist: $releaseFunctionLib"
    exit 1
}
. $releaseFunctionLib
[ -e "$reposExtractLib" ] || {
    echo "${prog}:  reposExtract plugin does not exist: $reposExtractLib"
    exit 1
}
. $reposExtractLib
[ -e "$copyPackageLib" ] || {
    echo "${prog}:  copyPackage plugin does not exist: $copyPackageLib"
    exit 1
}
. $copyPackageLib

{ echo $refstack | grep -qsE '^/'; } || refstack=$PWD/$refstack
{ echo $workdir  | grep -qsE '^/'; } || workdir=$PWD/$workdir

[ -d "$refstack" ] || {
    echo "Reference stack directory not found: $refstack"
    exit 2
}
[ -d "$workdir" ] || {
    echo "Reference stack directory not found: $workdir"
    exit 2
}

##
# setup the working directory for the current session
#
function setupSessionDir {
    [ -d "$sessiondir" ] || mkdir $sessiondir
    echo $$ $asuser > $sessiondir/$prog.pid
    mksandbox $sandbox || return 3
    makeStageServer $createpkgs || return 3
}

## 
# check to see if a session directory is in use
#
function checkForSession {
    [ -e "$sessiondir" ] && { 
        echo -n "Release of $prodname $version is already in progress"
        if [ -e "$sessiondir/$prog.pid" ]; then
            who=`cat $sessiondir/$prog.pid`
            pid=`echo $who | awk '{print $1}'`
            user=`echo $who | awk '{print $2}'`
            [ -z "$user" ] && user="unknown"
            echo -n " by user $user (pid=$pid)"
        fi
        echo "; aborting."
        return 1
    }
    return 0
}

##
# deploy the product artifacts to the staging server.  
function deployToStageServer {
    echo Deploying to server...
    [ -d $createpkgs/$prodname/$version ] || {
        echo Failed to find server artifacts: $createpkgs/$prodname/$version
        return 3
    }
    [ -d $stagesrvr ] || { 
        echo Missing stage server directory: $stagesrvr
        return 3
    }
    pushd $createpkgs > /dev/null
    { tar cf - $prodname/$version | (cd $stagesrvr; tar xf -); } || return 9
    cp $prodname/$version/b1.manifest $stagesrvr/manifests/$prodname-${version}+1.manifest || return 9

    synctoweb || return 10
    [ -n "$testserver" ] || synctostd || return 10
}

##
# validate the requested release via a test deployment and install.  If a 
# manifest was not provided, one will be generated.
#
function validateVersion {
    # assume we are in $sessiondir
    # package up the source
    [ -d "$tarrootdir" ] || {
        if [ -f "${tarrootdir}.tar.gz" ]; then
            tar xzf "${tarrootdir}.tar.gz" || return 6
        else
            echo "${prog}: Missing source code: $tarrootdir"
            return 6
        fi
    }

    if [ -z "$manifest" ]; then
        # create a manifest if one was not provided
        createManifest || return $?
    else
        # 
        mkdir -p $createpkgs/$prodname/$version
        cp "${tarrootdir}.tar.gz" $createpkgs/$prodname/$version || return 6
        cp $manifest $createpkgs/$prodname/$version || return 6
        cp "${tarrootdir}/ups/$prodname.table" $createpkgs/$prodname/$version || return 6
        checkTests=1
    fi
    cp $createpkgs/$prodname/$version/b1.manifest $createpkgs/manifests/${tarrootdir}+1.manifest

    # install from test server
    echo Testing install from server...
    EUPS_PATH=${sandbox}:$EUPS_PATH
    [ -n "$usebuildthreads" ] && { 
        export SCONSFLAGS="-j $usebuildthreads"
        echo SCONSFLAGS=$SCONSFLAGS
    }
    echo eups distrib install --nolocks --noclean -r $createpkgs $prodname ${version}+1
    eups distrib install --nolocks --noclean -r $createpkgs $prodname ${version}+1 || return 7

    local flavor=`eups flavor`
    pushd $sandbox/EupsBuildDir/$flavor/${tarrootdir}+1 > /dev/null || return 2
    [ -n "$checkTests" ] && {
        # check the tests
        echo Checking tests...
        [ -d "${tarrootdir}/tests/.tests" ] || {
            # the tests need to be run
            [ -e "eupssetup.sh" ] && source eupssetup.sh
            cd ${tarrootdir} >/dev/null
            opts=
            [ -n "$usebuildthreads" ] && opts="-j $usebuildthreads"
            echo scons opt=3 version=${version}+1 $opts tests
            scons opt=3 version=${version}+1 $opts tests || return 8
            mkdir -p tests/.tests
            { checkTests $PWD && checkTests=; } || {
                echo "rechecking..."
                scons opt=3 tests || return 8
            }
            cd $sandbox/EupsBuildDir/$flavor/${tarrootdir}+1 >/dev/null
        }
    }
    [ -n "$checkTests" ] && {
        checkTests $tarrootdir || {
            err=$?
            if [ -n "$ignorefailedtests" ]; then
                echo "Ignoring failed tests results"
            else
                return $9
            fi
        }
    }
    popd >/dev/null
}

##
# create a manifest file for the product.  This requires building and 
# installing the product.
#
function createManifest {
    local opts
    opts=
    [ -n "$usebuildthreads" ] && opts="$opts -j $usebuildthreads"
    [ -n "$ignorefailedtests" ] && opts="$opts -i"
    [ -n "$reftags" ] && opts="$opts -t $reftags"
    [ -n "$noclean" ] && opts="$opts -n"

    echo createRelease.sh -S -r $refstack -w "$sessiondir" -s "$sessiondir/$tarrootdir" -o "$createpkgs" $opts $prodname $version
    createRelease.sh -S -r $refstack -w "$sessiondir" -s "$sessiondir/$tarrootdir" -o "$createpkgs" $opts $prodname $version || return `expr $? + 10`
    manifest="$createpkgs/$product/$version/b1.manifest"
}

function onexit {
    [ -z "$noclean" ] && {
        cd $startdir
        [ -n "$sessiondir" -a -d "$sessiondir" ] && {
            rm -rf $sessiondir
        }
    }
}

function interrupted {
    onexit
}

trap "onexit" 0
trap "interrupted" 1 2 3 13 15
dsthome=$DEVENV_SERVERTOOLS_DIR
clearlsst
source $refstack/loadLSST.sh
# setup devenv_servertools
{ pushd $dsthome >/dev/null && setup -r . && popd >/dev/null; }

prodname=$1
version=$2
manifest=$3
if { echo $version | grep -qsE '[\+][0-9]+'; }; then
    ext=`echo $version | sed -e 's/.*+/+/'`
    echo "Note: ignoring build number extension as one will be assigned"
    version=`taggedVersion $version`
fi
tarrootdir=`productDirName $prodname $version`

[ -n "$manifest" ] && {
    [ ! -f "$manifest" ] && {
        echo "${prog}: Manifest file not found: $manifest"
        exit 1
    }
    checkTests=1
    { echo $manifest | grep -qsE '^/'; } || manifest=$PWD/$manifest
}

sessiondir="$workdir/$prodname-$version"
sandbox="$sessiondir/test"
createpkgs="$sessiondir/pkgs"

# lock this session: prevent multiple simultaneous releases of the same version
checkForSession || exit 3
mkdir $sessiondir

# setup up our work area
setupSessionDir || exit $?
cd "$sessiondir"

# extract the source and create tarball
extractProductSource $prodname $version $tarrootdir || exit $?

# do a test deployment and install using the given manifest.  If one was 
# not provided, create one.
validateVersion || exit $?

# send validated artifacts to the actual server.
if [ -z "$nocommit" ]; then
    deployToStageServer || exit $?
else
    echo "Release not committed to server (as per request)"
fi

# 




# 






