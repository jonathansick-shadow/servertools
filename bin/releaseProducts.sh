#! /bin/bash
#
SHELL=/bin/bash
prog=`basename $0`

[ -n "$DEVENV_SERVERTOOLS_DIR" ] || {
    echo "${prog}: devenv_servertools not setup"
    exit 1
}
libdir="$DEVENV_SERVERTOOLS_DIR/lib"

function usage {
    echo Usage: "$prog [-b DIR -r DIR -j NUM -hpi] product/version [ product/version ... ]"
}

function help {
    usage
    echo "Options:"
    echo "  -b DIR      the base directory for the release-related directories"
    echo "  -r DIR      the reference stack directory"
    echo "  -j NUM      use NUM threads when building"
    echo "  -t TAG      when deploying, tag the release with the given tag name"
    echo "  -h          print this help and exit"
}
valRelOpts=""
stackbase=
douprev=1

while getopts "j:b:r:t:Uh" opt; do
  case $opt in 
    b)
      stackbase="$OPTARG"
      valRelOpts="$valRelOpts -b $stackbase" ;;
    r)
      valRelOpts="$valRelOpts -r $OPTARG" ;;
    j)
      valRelOpts="$valRelOpts -j $OPTARG" ;;
    t)
      valRelOpts="$valRelOpts -t $OPTARG" ;;
    U)
      douprev= ;;
    h)
      help
      exit 0 ;;
  esac
done
shift $(($OPTIND - 1))

[ $# -lt 1 ] && {
    echo "${prog}: Missing arguments: product/version"
    usage
    exit 1
}

while [ $# -gt 0 ]; do

    prodversargs=`echo $1 | sed -e 's/\// /g'`
    prodver=`echo $1 | sed -e 's/\//-/g'`
    buildlog=${prodver}.log
    echo validateRelease.sh -p $valRelOpts $prodversargs complete
    validateRelease.sh -p $valRelOpts $prodversargs complete > $buildlog 2>&1\
    || {
        ok=$?
        echo "Problem validating $prodversargs"
        exit $ok
    }

    # uprev its dependents
    uprevlist=$stackbase/build/${prodver}-uprev.lis
    echo autouprev.py -d $stackbase/www -o $uprevlist $1
    autouprev.py -d $stackbase/www -o $uprevlist $1 || {
        ok=$?
        echo "Problem processing dependents via autouprev"
        exit $ok
    }

    # release those dependents to the test server
    

    shift

done

echo Done.


