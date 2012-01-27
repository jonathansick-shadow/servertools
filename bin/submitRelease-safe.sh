#! /bin/bash -
#
usehome=`dirname $0`
prog=`basename $0 | sed -e 's/-.*//'`
user=UNSPECIFIED

function usage {
    echo Usage: $prog "[-j NUM -t TAGS -iCnVh]" product version "[manifest]"
}

function help {
    usage
    echo 
    echo "Releases a tagged version of a product after confirming a successful"
    echo "build.  If manifest file is not provided, one is generated assuming"
    echo "current versions of product's dependencies."
    echo 
    echo "Options:"
    echo "  -t TAG[,TAG]  when creating a manifest on the fly (i.e. manifest is not"
    echo "                provided) prefer dependencies with these (server-assign) tags."
    echo "  -R          re-release already released version: without this, the release"
    echo "                will not be proceed if the version has already been released."
    echo "  -i          ignore failed tests: don't let failed tests prevent release"
    echo "  -j NUM      use NUM threads when building (default is 4)"
    echo "  -D          do not uprev the product's dependents"
    echo "  -C          prep and test the release but do not commit it"
    echo "  -n          do not clean up the work area before exiting"
    echo "  -V          force validation: check that the tests pass even if the tests"
    echo "                were run implicitly when a default manifest was created."
    echo "  -h          print this help and exit"
}

args=()
while getopts ":j:t:U:iDVCTnh" opt; do
  case $opt in 
    j)
      args=($args -j "$OPTARG") ;;
    t)
      args=($args -t "$OPTARG") ;;
    U)
      user=$OPTARG ;;
    h)
      help
      exit 0 ;;
    '?')
      echo ${prog}: Unsupported option: -$OPTARG
      usage
      exit 1 ;;
    *) 
      args=($args -$opt) ;;
  esac
done
shift $(($OPTIND - 1))

echo $usehome/bin/submitRelease.sh -L -U $user ${args[*]} $*
exec $usehome/bin/submitRelease.sh -L -U $user ${args[*]} $*
