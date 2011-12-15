#! /bin/bash
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
startdir=$PWD
prog=`basename $0`

[ -n "$DEVENV_SERVERTOOLS_DIR" ] || {
    echo "${prog}: devenv_servertools not setup"
    exit 1
}
libdir="$DEVENV_SERVERTOOLS_DIR/lib"
reposExtractLib="$libdir/gitReposExtract.sh"  # default; override in conf
copyPackageLib="$libdir/rsyncCopyPackage.sh"  # default; override in conf
releaseFunctionsLib="$libdir/releaseFunctions.sh"

function usage {
    echo Usage: `basename $0` "[-c FILE -r DIR -j NUM -t TAGS -ih]" product version "[manifest]"
}

function help {
    usage
    echo 
    echo "Releases a tagged version of a product after confirming a successful"
    echo "build.  If manifest file is not provided, one is generated assuming"
    echo "current versions of product's dependencies."
    echo 
    echo "Options:"
    echo "  -c FILE     the configuration file to use"
    echo "  -r DIR      the reference stack directory"
    echo "  -w DIR      a 'work' directory to use for private scratch"
    echo "  -j NUM      use NUM threads when building"
    echo "  -t TAGS     when deploying, tag the release with the given tags name."
    echo "                tag names current and stable are disallowed."
    echo "  -i          ignore failed tests: don't let failed tests prevent release"
    echo "  -h          print this help and exit"
}

configfile=$DEVENV_SERVERTOOLS_DIR/conf/submitRelease_conf.sh
usebuildthreads=4
ignorefailedtests=
testsHaveFailed=

while getopts "c:j:r:w:t:ih" opt; do
  case $opt in 
    c)
      configfile=$OPTARG 
      [ -f "$configfile" ] || {
          echo "${prog}: config file not found:" $configfile
          exit 1
      }
      ;;
    r)
      refstack=$OPTARG
    w)
      workdir=$OPTARG
    j)
      usebuildthreads=$OPTARG ;;
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
    echo "${prog}: Missing arguments: product version"
    usage
    exit 1
}
[ $# -lt 2 ] && {
    echo "${prog}: Missing argument: version"
    usage
    exit 1
}

[ -n "$manifest" -a ! -d "$manifest" ] && {
    echo "${prog}: Manifest file not found: $manifest"
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
    mksandbox $sandbox || return 3
    makeStageServer $createpkgs || return 3
}

##
# deploy the product artifacts to the staging server.  If a manifest 
# was not provided, one will be generated.
function deployToStageServer {
    # assume we are in $sessiondir
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
        createManifest || exit $?
    else
        cp "${tarrootdir}.tar.gz" $product/$version || return 6
        cp $manifest $product/$version/
    fi

    # buildProduct "$tarrootdir" || return $?
    
}

##
# create a manifest file for the product.  This requires building and 
# installing the product.
#
function createManifest {
    # PUT THIS INTO SEPARATE SCRIPT
    local opts
    opts=
    [ -n "$ignorefailedtests" ] && opts="-i"
    echo buildManifest.sh -r $refstack -w "$sessiondir" -s "$sessiondir/$tarrootdir" -d "$sandbox" -c "$createpkgs" $opts $product $version "$sessiondir/${tarrootdir}.manifest"
    buildManifest.sh -r $refstack -w "$sessiondir" -s "$sessiondir/$tarrootdir" -d "$sandbox" -c "$createpkgs" $opts $product $version "$sessiondir/${tarrootdir}.manifest" || return `expr $? + 10`
    manifest="$sessiondir/${tarrootdir}.manifest"
    #

}

function onexit {
    cd $startdir
    [ -n "$sessiondir" -a -d "$sessiondir" ] && {
        rm -rf $sessiondir
    }
}

function interrupted {
    onexit
}

trap "onexit" 0
trap "interrupted" 1 2 3 13 15

prodname=$1
version=$2
manifest=$3
if { echo $version | grep -qsE '[\+][0-9]+'; }; then
    ext=`echo $version | sed -e 's/.*+/+/'`
    echo "Note: ignoring build number extension as one will be assigned"
    version=`taggedVersion $version`
fi
tarrootdir=`productDirName $prodname $version`

sessiondir="$workdir/$product-$version"
sandbox="$sessiondir/test"
createpkgs="$sessiondir/pkgs"

# lock this session: prevent multiple simultaneous releases of the same version
[ -e "$sessiondir" ] && { 
    echo "Release of $prodname $version is already in progress; aborting"
    sessiondir=
    exit 3
}
mkdir $sessiondir

# setup up our work area
setupSessionDir || exit $?
cd "$sessiondir"

# extract the source
extractProductSource || exit $?

# create the artifacts for the distribution server
deployToStageServer || exit $?

# 



# 






