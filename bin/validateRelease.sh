#! /bin/bash
#
SHELL=/bin/bash
stackbase=/lsst/DC3/stacks/rc

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

while getopts "b:r:h"; do
    b)
      stackbase=$OPTARG ;;
    r)
      refstack=$OPTARG ;;
    h)
      help
      exit 0 ;;
    \?)
      echo "Invalid option: -$OPTARG"
      exit 1 ;;
    :)
      echo "Option -$OPTARG requires an argument"
      exit 1 ;;
done

[ -z "$refstack" ]    && refstack=$stackbase/ref
[ -z "$teststack" ]   && teststack=$stackbase/test
[ -z "$serverstage" ] && serverstage=$stackbase/pkgs
[ -d "$refstack" ] && {
    echo "Reference stack directory not found: $refstack"
    exit 2
}
[ -d "$teststack" ] && {
    echo "Reference stack directory not found: $teststack"
    exit 2
}
[ -d "$serverstage" ] && {
    echo "Product staging directory not found: $serverstage"
    exit 2
}

