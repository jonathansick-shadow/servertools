#! /bin/bash
#
SHELL=/bin/bash
stackbase=/lsst/DC3/stacks/rc

[ -n "$DEVENV_SERVERTOOLS_DIR" -a -e "$DEVENV_SERVERTOOLS_DIR/conf/validateRelease_conf.sh" ] && . $DEVENV_SERVERTOOLS_DIR/conf/validateRelease_conf.sh"

function usage() {
    echo Usage: `basename $0` "[-b DIR -r DIR -h]" product version
}

function help() {
    usage
    echo "Options:"
    echo "  -b DIR      the base directory for the release-related directories"
    echo "  -r DIR      the reference stack directory"
    echo "  -h          print this help and exit"
}

while getopts "b:r:h" opt; do
  case $opt in 
    b)
      stackbase=$OPTARG ;;
    r)
      refstack=$OPTARG ;;
    h)
      help
      exit 0 ;;
  esac
done

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

function clearlsst {
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

function prodductDir {
    echo "$builddir/$1-$2
}

function reposExtract {
    cd $builddir
    
}

clearlsst
export LSST_DEVEL=$teststack
export LSST_HOME=$refstack
source $LSST_HOME/loadLSST.sh

prodname=$1 ; shift
version=$1 ; shift
command=$1 ; shift
taggedas=`taggedVersion $version`
pdir=`productDir $prodname $taggedas`

function do_extract {
    if [ -d "$pdir" ]; then
        echo "Product is already checked out"
    else
        reposExtract
    fi
}


case $command in
    extract)
      do_extract ;;
    *)
      echo "Unknown command: $command" ;;
esac

