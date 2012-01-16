#! /bin/bash
#
# submitRelease.sh -- request the release of a tagged version of a product
# 
# This script is intended to run as a user who has permission to write to 
# the distribution server and to the reference software stack.  Non-privileged
# users would invoke this via a wrapper script (submitrelease)
#
workdir=/lsst/DC3/distrib/default/submitRelease
prog=`basename $0 | sed -e 's/\..*$//'`
pidfile="submitRelease.pid"

function usage {
    echo Usage: `basename $0` "[-c FILE -w DIR -h]" product version
}

function help {
    usage
    cat <<EOF

Clear the session lock for a particular product release.

Options:
  -w       the parent work directory containing the session area
  -c FILE  the configuration file to use 
  -h       print this help and exit
EOF
}

configfile=$DEVENV_SERVERTOOLS_DIR/conf/createRelease_conf.sh
while getopts "w:c:h" opt; do
  case $opt in 
    c)
      configfile=$OPTARG 
      [ -f "$configfile" ] || {
          echo "${prog}: config file not found:" $configfile
          exit 1
      }
      ;;
    w)
      workdir=$OPTARG ;;
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

[ -e "$conffile" ] && \
    . $configfile
{ echo $workdir  | grep -qsE '^/'; } || workdir=$PWD/$workdir

prodname=$1; shift
version=$1;  
sessiondir="$workdir/$prodname-$version"

[ -e "$sessiondir" ] || {
    echo "${prog}: Session for $prodname $version done"
    exit 0
}

[ -f "$sessiondir/$pidfile" ] && {
    who=`cat $sessiondir/$pidfile`
    pid=`echo $who | awk '{print $1}'`

    { ps -a -p $pid | grep -sq $pid; } && {
        echo "${prog}: Sorry, session process $$ is still running; not cleared"
        exit 1
    }
}

[ -e "$sessiondir" ] && {
    rm -rf $sessiondir || {
        echo "${prog}: Failed to remove session dir: $sessiondir"
        exit 2
    }
}
echo "Session cleared for $prodname $version"



