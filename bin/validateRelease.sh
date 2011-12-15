#! /bin/bash
#
SHELL=/bin/bash
stackbase=/lsst/DC3/stacks/rc
prog=`basename $0`

[ -n "$DEVENV_SERVERTOOLS_DIR" ] || {
    echo "${prog}: devenv_servertools not setup"
    exit 1
}
libdir="$DEVENV_SERVERTOOLS_DIR/lib"
reposExtractLib="$libdir/gitReposExtract.sh"  # default; override in conf
copyPackageLib="$libdir/rsyncCopyPackage.sh"  # default; override in conf

function usage {
    echo Usage: `basename $0` "[-b DIR -r DIR -j NUM -hpi]" product version command
}

function help {
    usage
    echo "Options:"
    echo "  -c FILE     the configuration file to use"
    echo "  -b DIR      the base directory for the release-related directories"
    echo "  -r DIR      the reference stack directory"
    echo "  -j NUM      use NUM threads when building"
    echo "  -t TAG      when deploying, tag the release with the given tag name"
    echo "  -p          purge previous attempts to validate before executing command"
    echo "  -i          ignore failed tests: don't let failed tests halt validation"
    echo "  -h          print this help and exit"
    commands
}

function commands {
    echo "Commands:"
    echo "  extract     extract the product source code from the repository"
    echo "  test        build the product and run the tests"
    echo "  install     install the product manually into test stack"
    echo "  package     create distribution package in server staging area"
    echo "  deploy      copy the distribution package to the server"
    echo "  download    install the product from the distribution server"
    echo "  complete    do a complete validation and update reference stack"
    echo "  clean       clean product from build directory and test stack"
    echo "                 This forces validation to start from beginnning."
    echo "  purge       run clean and also remove product from reference stack"
    echo "                 This forces validation to start from beginnning."
}

configfile=$DEVENV_SERVERTOOLS_DIR/conf/validateRelease_conf.sh
prepurge=
ignorefailedtests=
usebuildthreads=4
testsHaveFailed=
eupstag=

while getopts "c:j:b:r:t:pih" opt; do
  case $opt in 
    c)
      configfile=$OPTARG 
      [ -f "$configfile" ] || {
          echo "${prog}: config file not found:" $configfile
          exit 1
      }
      ;;
    b)
      stackbase=$OPTARG ;;
    r)
      refstack=$OPTARG
      { echo $refstack | grep -qsE '^/'; } || refstack=$PWD/$refstack ;;
    j)
      usebuildthreads=$OPTARG ;;
    p) 
      prepurge=1 ;;
    i)
      ignorefailedtests=1 ;;
    t)
      eupstag=$OPTARG ;;
    h)
      help
      exit 0 ;;
  esac
done
shift $(($OPTIND - 1))

[ $# -lt 1 ] && {
    echo "${prog}: Missing arguments: product version command"
    usage
    exit 1
}
[ $# -lt 2 ] && {
    echo "${prog}: Missing arguments: version command"
    usage
    exit 1
}
[ $# -lt 3 ] && {
    echo "${prog}: Missing command argument"
    usage
    commands
    exit 1
}

[ -e "$conffile" ] && \
    . $configfile
[ -e "$reposExtractLib" ] || {
    echo "${prog}:  reposExtract plugin does not exist: $reposExtractLib"
    exit 1
}
[ -e "$copyPackageLib" ] || {
    echo "${prog}:  copyPackage plugin does not exist: $copyPackageLib"
    exit 1
}

{ echo $stackbase | grep -qsE '^/'; } || stackbase=$PWD/$stackbase

[ -z "$refstack" ]    && refstack=$stackbase/ref
[ -z "$teststack" ]   && teststack=$stackbase/test
[ -z "$serverstage" ] && serverstage=$stackbase/pkgs
[ -z "$builddir" ]    && builddir=$stackbase/build
[ -d "$refstack" ] || {
    echo "Reference stack directory not found: $refstack"
    exit 2
}
[ -d "$teststack" ] || {
    echo "Reference stack directory not found: $teststack"
    exit 2
}
[ -d "$serverstage" ] || {
    echo "Product staging directory not found: $serverstage"
    exit 2
}
[ -d "$builddir" ] || {
    echo "Build directory not found: $builddir"
    exit 2
}

# load the plugins
. $reposExtractLib
. $copyPackageLib

function clearlsst {
    [ -n "$SETUP_EUPS" ] && {
        eval `$EUPS_DIR/bin/eups_setup --unsetup lsst`
    }
    setuppkgs=(`printenv | grep '^SETUP_' | sed -e 's/=.*$//'`)
    for var in ${setuppkgs[@]}; do
        pkghome=`echo $var | sed -e 's/SETUP_//' -e 's/$/_DIR/'`
        eval $var=
        eval $pkghome=
    done
    EUPS_PATH=
    LD_LIBRARY_PATH=
    PYTHONPATH=
}

function taggedVersion {
    echo $1 | sed -e 's/[\+\-].*$//'
}

function productDirName {
    echo "$1-$2"
}
function productDir {
    echo $builddir/`productDirName $1 $2`
}
function manifestForVersion {
    local version=$1
    [ -z "$version" ] && version=b
    local pre=$2
    [ -z "$pre" ] && pre=b
    local ext=`echo $version | sed -e 's/^.*\([+-]\)/\1/'`
    local bn=`echo $ext | sed -e 's/^.//'`
    echo "$pre$bn.manifest"
} 

function extractProductSource {
    cd $builddir
    pdname=`productDirName $prodname $taggedas`
    reposExtract $prodname $taggedas $pdname || {
        echo "$prog: failed to extract source code"
        return 2
    }
    tar czf ${pdname}.tar.gz $pdname || { 
        echo "$prog: Problem creating tar-ball"
        return 3
    }
}

function buildProduct {
    # make sure that our stack had current tags up to date
    ensureCurrent.py

    cd $pdir
    EUPS_PATH=${teststack}:$refstack

    # get the dependency products tagged current whenever possible
    setup --tag=current -r .

    threadarg=
    [ -n "$1" ] && threadarg="-j $1"

    buildok=
    echo scons opt=3 $threadarg
    scons opt=3 $threadarg && buildok=1
    if [ -n "$buildok" ]; then
        mkdir -p "tests/.tests"
    else
        echo "$prog: Product build failed"
        return 4
    fi
}

function checkTests {
    cd $pdir/tests/.tests || return 5
    ran=(`ls`)
    [ ${#ran[@]} -eq 0 ] && {
        echo "Note: Apparently no tests were provided"
        return 0
    }
    failed=(`ls *.failed 2> /dev/null`)
    [ ${#failed[@]} -gt 0 ] && {
        howmany="${#failed[@]} test"
        [ ${#failed[@]} -gt 1 ] && howmany="${howmany}s"
        echo $howmany failed: ${failed[@]}
        return 5
    }
    echo "All tests passed"
}

function installProduct {
    EUPS_PATH=${teststack}:$refstack
    flavor=`eups flavor`
    cd $pdir
    setup -r .
    echo scons opt=3 version=$version install
    { scons opt=3 version=$version install && \
      [ -d "$teststack/$flavor/$prodname/$version" ]; } || {
        echo "${prog}: Product failed to install into test stack"
        return 6
    }
    echo scons -j 1 opt=3 version=$version declare
    scons -j 1 opt=3 version=$version declare
}

function eupscreate {
    EUPS_PATH=${teststack}:$refstack
    echo eups distrib create -j -f generic -d lsstbuild -s $serverstage \
                 -S srctardir=$builddir $prodname $version
    eups distrib create -j -f generic -d lsstbuild -s $serverstage      \
                 -S srctardir=$builddir $prodname $version           || \
    {
        echo "${prog}: Problem packaging product via eups distrib create"
        return 7
    }
    [ -f "$serverstage/$prodname/$taggedas/$prodname-${taggedas}.tar.gz" ] || {
        echo "${prog}: Failed to stage tarball"
        return 7
    }
}

function deployPackage {
    cd $serverstage
    [ -d "$prodname/$taggedas" ] || {
        echo "${prog}: Missing product export directory: $prodname/$taggedas"
        return 8
    }
    [ -f "$prodname/$taggedas/$prodname-${taggedas}.tar.gz" ] || {
        echo "${prog}: Missing product tarball: $prodname-$taggedas.tar.gz"
        return 8
    }
    manfile=`manifestForVersion $version`
    [ -f "$prodname/$taggedas/$manfile" ] || {
        echo "${prog}: Missing manifest file: $manfile"
        return 8
    }

    copyPackage $prodname/$taggedas $eupstag || return 8
}

function eupsinstall {
    EUPS_PATH=$LSST_HOME
    local oldSCONSFLAGS=$SCONSFLAGS
    [ -n "$usebuildthreads" ] && {
        export SCONSFLAGS="-j $usebuildthreads"
        [ -n "$oldSCONSFLAGS" ] && SCONSFLAGS="$SCONSFLAGS $oldSCONSFLAGS"
    }
    tagopt=
    [ -n "$eupstag" ] && tagopt="--tag=$eupstag"

    echo eups distrib install --nolocks $tagopt $prodname $version 
    eups distrib install --nolocks $tagopt $prodname $version || {
        echo "${prog}: Failed to install product"
        SCONSFLAGS=$oldSCONSFLAGS
        return 9
    }
    SCONSFLAGS=$oldSCONSFLAGS
    [ -d "$LSST_PKGS/$prodname/$version" ] || {
        echo "${prog}: Failed to install product; install directory not found"
        return 9
    }
    { eups list $prodname $version | grep -sq $version; } || {
        echo "${prog}: Failed to declare product"
        return 9
    }
}

function cleanInstall {
    local stack=$1
    if [ -z "$stack" -o -z "$prodname" -o -z "$version" ]; then
        echo "Programming error: unable to clean due to missing data:"
        echo "  stack=$stack"
        echo "  prodname=$prodname"
        echo "  verison=$version"
        return 10
    fi

    EUPS_PATH=${stack}
    flavor=`eups flavor`
    eups distrib clean $prodname $version
    if { eups list $prodname $version 2> /dev/null | grep -sq $version; }; then
        eups remove --force $prodname $version
    fi
    if { eups list $prodname $version 2> /dev/null | grep -sq $version; }; then
        echo "${prog}: Failed to remove product from test stack"
        return 10
    fi
    if [ -d "$teststack/$flavor/$prodname/$version" ]; then
        rm -rf $teststack/$flavor/$prodname/$version
    fi
    if [ -d "$teststack/$flavor/$prodname" ]; then
        local tmp=`ls $teststack/$flavor/$prodname | wc -l`
        [ $tmp = "0" ] && rmdir $teststack/$flavor/$prodname
    fi 
}

function cleanBuildDir {
    if [ -z "$builddir" -o -z "$prodname" -o -z "$taggedas" ]; then
        echo "Programming error: unable to clean due to missing data:"
        echo "  builddir=$builddir"
        echo "  prodname=$prodname"
        echo "  taggedas=$taggedas"
        return 100
    fi
    pdname=`productDirName $prodname $taggedas`
    [ -e "$builddir/${pdname}.tar.gz" ] && rm -rf $builddir/${pdname}.tar.gz
    [ -e "$builddir/$pdname" ] && rm -rf $builddir/$pdname
}

clearlsst
# export LSST_DEVEL=$teststack
export LSST_DEVEL=
export LSST_HOME=$refstack
source $LSST_HOME/loadLSST.sh

prodname=$1 ; shift
version=$1 ; shift
command=$1 ; shift

if { echo $version | grep -qsE '[\+][0-9]+'; }; then
    taggedas=`taggedVersion $version`
else
    taggedas=$version
    version=${taggedas}+1
fi
pdir=`productDir $prodname $taggedas`

function do_extract {
    if [ -d "$pdir" ]; then
        echo "Product is already checked out"
    else
        echo "Extractng source from repository"
        extractProductSource
    fi
}

function do_test {
    do_extract || return $?
    if [ -d "$pdir/tests/.tests" ]; then
        echo "Product is already built and tests have run"
    else
        echo "Building product and running tests"
        buildProduct $usebuildthreads || return $?
    fi

    echo "Confirming tests have passed"
    checkTests
    if [ "$?" != "0" ]; then
        echo "Failed tests detected; will try rebuilding"
        buildProduct 
        checkTests || {
            local status=$?
            testsHaveFailed=1
            [ -z "$ignorefailedtests" ] && return $status
            echo "WARNING: Going on despite failed tests!"
        }
    fi
}

function do_install {
    do_test || return $?
    flavor=`eups flavor`
    if [ -d "$teststack/$flavor/$prodname/$version" ]; then
        echo "Product is already installed in test stack"
    else
        installProduct || return $?
    fi
}

function do_package {
    do_install || return $?
    if [ -d "$serverstage/$prodname/$taggedas" ]; then
        echo "Product package has been staged already"
    else
        echo "Staging product package"
        eupscreate || return $?
    fi
}

function do_deploy {
    do_package || return $?
    echo "Deploying package to test server"
    deployPackage || return $?
}

function do_download {
    { EUPS_PATH=$refstack eups list $prodname $version 2> /dev/null | grep -sq $version; } && {
        echo "${prog}: $prodname $version is already installed into the reference stack."
        echo "    To override either remove the product or use the -p option"
        return 1
    }
    echo "Checking availability on test server"
    { eups distrib list $prodname $version 2> /dev/null | grep -sq $version; } || {
        do_deploy || return $?
    }
    echo "Installing product from test server"
    eupsinstall || return $?
}

function do_clean {
    echo "Cleaning test build and installation"
    cleanInstall $teststack
    local ok1=$?
    [ "$ok1" -eq 100 ] && return $ok1
    cleanBuildDir
    local ok2=$?
    [ -n "$ok2" -a "$ok2" -eq 100 ] && return $ok2
    [ -n "$ok2" -a "$ok1" -ne 0 ] && return $ok1
    return $ok2
}

function do_purge {
    do_clean
    echo "Removing product from reference stack"
    cleanInstall $refstack || return $?
}

function do_complete {
    do_download || return $?
    do_clean
    [ -n "$testsHaveFailed" ] && {
        echo "WARNING: Some TESTS HAVE FAILED"
    }
    echo "Product passes validation; it is ready for release."
}

[ -n "$prepurge" ] && {
    do_purge || exit $?
}

case $command in
    extract)
      do_extract || exit $? ;;
    test)
      do_test || exit $? ;;
    install)
      do_install || exit $? ;;
    package)
      do_package || exit $? ;;
    deploy)
      do_deploy || exit $? ;;
    download)
      do_download || exit $? ;;
    complete)
      do_complete || exit $? ;;
    clean)
      do_clean || exit $? ;;
    purge)
      do_purge || exit $? ;;
    *)
      echo "Unknown command: $command" ;;
esac

