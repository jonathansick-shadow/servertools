#! /bin/bash -
#
usehome=`dirname $0`
usehome=`dirname $usehome`
prog=`basename $0 | sed -e 's/-.*//'`
function usage {
    echo Usage: $prog "[-vh]" product version
}

function help {
    usage
    cat <<EOF

Clear the session lock for a particular product release.

Options:
  -v       show extra messages
  -h       print this help and exit
EOF
}

args=()
while getopts "vh" opt; do
  case $opt in 
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

# echo $usehome/bin/clearSubmitRelease.sh ${args[*]} $*
exec $usehome/bin/clearSubmitRelease.sh ${args[*]} $*
