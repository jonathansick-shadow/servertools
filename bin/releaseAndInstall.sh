#! /bin/bash
#
#  This script is intended for use within releaseProducts.py
#
SHELL=/bin/bash
stackbase=/lsst/DC3/distrib/w12
prog=`basename $0`

[ -n "$DEVENV_SERVERTOOLS_DIR" ] || {
    echo "${prog}: devenv_servertools not setup"
    exit 1
}
libdir="$DEVENV_SERVERTOOLS_DIR/lib"
. $DEVENV_SERVERTOOLS_DIR/lib/rsyncToWebServer.sh
rsyncCopyCmd=rsyncToWebServer

function usage {
    echo Usage: `basename $0` "[-d DIR -j NUM -t TAG -h] manifestpath [...]"
}

function help {
    usage
    echo "Options:"
    echo "  -b DIR      the base directory for the release-related directories"
    echo "  -r DIR      the reference stack directory"
    echo "  -d DIR      the root directory for the distribution server"
    echo "  -j NUM      use NUM threads when building"
    echo "  -t TAG      when deploying, tag the release with the given tag name"
    echo "  -h          print this help and exit"
}

eupstag=
overwrite=

while getopts "j:b:r:d:t:oh" opt; do
  case $opt in 
    b)
      stackbase=$OPTARG ;;
    r)
      refstack=$OPTARG
      { echo $refstack | grep -qsE '^/'; } || refstack=$PWD/$refstack ;;
    d)
      serverdir=$OPTARG
      { echo $serverdir | grep -qsE '^/'; } || serverdir=$PWD/serverdir ;;
    j)
      usebuildthreads=$OPTARG ;;
    t)
      eupstag=$OPTARG ;;
    o)
      overwrite=1 ;;
    h)
      help
      exit 0 ;;
  esac
done
shift $(($OPTIND - 1))

[ $# -lt 1 ] && {
    echo "${prog}: Missing manifest filepath"
    usage
    exit 1
}

{ echo $stackbase | grep -qsE '^/'; } || stackbase=$PWD/$stackbase
[ -z "$refstack" -o -z "$serverdir" -a -d "$stackbase" ] || {
    echo "${prog}: base directory not found: $stackbase"
    exit 1
}
[ -z "$refstack" ]    && refstack=$stackbase/ref
[ -z "$serverdir" ] && serverdir=$stackbase/www
[ -d "$serverdir" ] || {
    echo "Product staging directory not found: $serverdir"
    exit 2
}
[ -d "$refstack" ] || {
    echo "Reference stack directory not found: $refstack"
    exit 2
}

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

# copy the manifests to the 
owarg=
[ -n "$overwrite" ] && owarg="-o"
echo releaseman.py -d $serverdir -a $owarg "$@" 
releaseman.py -d $serverdir -a $owarg "$@" || exit 3

$rsyncCopyCmd || exit 4

clearlsst
export LSST_DEVEL=
export LSST_HOME=$refstack
source $LSST_HOME/loadLSST.sh
[ -n "$usebuildthreads" ] && export SCONSFLAGS="-j $usebuildthreads"

for manifest in "$@"; do
    pv=`echo $manifest | sed -e 's/^external\///' -e 's/\// /' -e 's/\/b/+/' -e 's/\.manifest$//'`
    tagopt=
    [ -n "$eupstag" ] && tagopt="--tag=$eupstag"
    echo eups distrib install --nolocks $tagopt $pv
    eups distrib install --nolocks $tagopt $pv || exit 5
done


    
