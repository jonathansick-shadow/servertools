#! /bin/bash -
#
usehome=`dirname $0`
usehome=`dirname $usehome`
prog=`basename $0 | sed -e 's/-.*//'`
user=UNSPECIFIED

function usage {
    echo Usage: ${prog}: "-t TAG[,TAG] [-nh] product version ..."
}

function help {
    usage
    echo <<EOF
Assign one or more server tags to one or more distributions.  The -D option 
(identifying the server directory) and at least one -t occurance (to name
the tag to assign is required.  Note that products are identified with a 
name-version format.  The stable tag is not assignable with this command.

Options:
  -t TAG[,TAG...]   server tag to assign to the given list of products
  -D                do not tag the products' dependents
  -n                do not clean up the work area before exiting
EOF
}

args=()
tags=()
while getopts ":t:U:Dnh" opt; do
  case $opt in 
    t)
      args=(${args[*]} -t "$OPTARG") ;;
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
      args=(${args[*]} -$opt) ;;
  esac
done
origarg=($*)
shift $(($OPTIND - 1))

# echo $usehome/bin/tagRelease.sh -L -U $user ${args[*]} $*
exec $usehome/bin/tagRelease.sh -L -U $user ${args[*]} $*
