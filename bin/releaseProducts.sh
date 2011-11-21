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

while getopts "j:b:r:t:h" opt; do
  case $opt in 
    b)
      valRelOpts="$valRelOpts -b $OPTARG" ;;
    r)
      valRelOpts="$valRelOpts -r $OPTARG" ;;
    j)
      valRelOpts="$valRelOpts -j $OPTARG" ;;
    t)
      valRelOpts="$valRelOpts -t $OPTARG" ;;
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

    prodver=`echo $1 | sed -e 's/\// /g'`
    buildlog=`echo $1 | sed -e 's/\//-/g'`.log
    echo validateRelease.sh -p $valRelOpts $prodver complete
    validateRelease.sh -p $valRelOpts $prodver complete > $buildlog 2>&1 || {
        echo "Problem validating $prodver"
        exit $?
    }
    shift

done

echo Done.


