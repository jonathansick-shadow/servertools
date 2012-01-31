#! /bin/bash
#
# tagRelease.sh -- assign server tags to products
#
# This is thin wrapper around tagReelase.py which adapts the commandline 
# interface.
#
SHELL=/bin/bash
prog=`basename $0 | sed -e 's/\..*$//'`
workdir=/tmp
stagesrvr=/lsst/DC3/distrib/w12/www
log=/dev/null

prodhome=$DEVENV_SERVERTOOLS_DIR
[ -n "$prodhome" ] || {
    # reconstruct the LSST environment
    function failrecon {
        echo "Failed to determine DEVENV_SERVERTOOLS_DIR"
        exit 1
    }
    prodhome=`dirname $0`; [ -z "$prodhome" ] && failrecon
    prodhome=`dirname $prodhome`; [ -z "$prodhome" ] && failrecon
}

configfile="$prodhome/conf/submitRelease_conf.sh"

function usage {
    echo Usage: ${prog}: "-t TAG[,TAG] [-U USER -Ln] product-version ..."
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
  -c FILE           the configuration file to use
  -w DIR            a 'work' directory to use for private scratch (def: /tmp)
  -U USER           identify the user running this command
  -L                log the tagging in the configured area
EOF
}

tags=()
noclean=
dolog=

while getopts "t:w:c:nh" opt; do
  case $opt in 
    c)
      configfile=$OPTARG 
      [ -f "$configfile" ] || {
          echo "${prog}: config file not found:" $configfile
          exit 1
      }
      ;;
    t)
      tags=($tags `echo $OPTARG | sed -e 's/,/ /g'`)
      ;;
    w)
      workdir=$OPTARG ;;
    n)
      noclean=1 ;;
    L)
      dolog=1 ;;
    U)
      asuser=$OPTARG ;;
    h)
      help
      exit 0 ;;
  esac
done
origarg=($*)
shift $(($OPTIND - 1))

[ -e "$configfile" ] && \
    . $configfile
sessiondir="$workdir/$prog.$$"
mkdir $sessiondir

noclean=

function onexit {
    if [ -z "$noclean" -a -n "$sessiondir" -a -d "$sessiondir" ] && {
        rm -rf $sessiondir
    }
}

function interrupted {
    echo "Interrupted!" >> $log
    onexit
}

trap "onexit" 0
trap "interrupted" 1 2 3 13 15
clearlsst
source $refstack/loadLSST.sh
# setup devenv_servertools
{ pushd $prodhome >/dev/null && setup -r . && popd >/dev/null; }
# echo $DEVENV_SERVERTOOLS_DIR

[ -n "$dolog" ] && {
    [ -n "$logdir" ] || logdir=$workdir/logs
    log=$logdir/$prog-`date '+%Y-%m-%dT%H:%M:%S'`.log

    echo $prog ${origargs[*]} > $log
}

# check that all tags exist
bad=()
for tag in $tags; do
    [ "$tag" = "stable" ] && {
        echo "${prog}: $tag tag not assignable with this command." | tee -a $log
        exit 2
    }

    tagfile=$stagesrvr/$tag.list
    [ -f "$tagfile" ] || bad=(${bad[*]} $tag)
done
[ ${#bad[*]} -gt 0 ] && {
    echo "${prog}: unsupported tags: ${bad[*]}" | tee -a $log
    exit 3
}

# check that all of the products exist
bad=()
for prod in $*; do
    [ -e "$stagesrvr/manifests/$prod.manifest" ] && bad=(${bad[*]} $prod)
done
[ ${#bad[*]} -gt 0 ] && {
    echo "${prog}: Unreleased products:" ${bad[*]} | tee -a $log
    exit 4
}
for prod in $*; do
    name=`echo $prod | sed -e 's/-.*$//'`
    [ -d "$stagesrvr/name" -o -d "$stagesrvr/pseudo/$name" ] && {
        bad=(${bad[*]} $name)
    }
done
[ ${#bad[*]} -gt 0 ] && {
    echo "${prog}: Non-lsst products:" ${bad[*]} | tee -a $log
    exit 4
}


for tag in $tags; do
    # to make this command atomic (and rollback-able) copy the tag file to 
    # a work area and operate on it there.
    tagfile=$stagesrvr/$tag.list
    cp $tagfile $sessiondir || {
        echo ${prog}: Failed to write to $sessiondir | tee -a $log
        exit 5
    }
    tagfile=$sessiondir/$tag.list

    for prod in $*; do
        pv=(`echo $prod | sed -e 's/-/ /'`)
        echo tagRelease.py -d $sessiondir ${pv[*]} $tag | tee -a $log
        tmplog=$sessiondir/tagRelease-py.log
        tagRelease.py -d $sessiondir ${pv[*]} $tag > $tmplog 2>&1 || {
            cat $tmplog
            [ -n "$dolog" ] && cat $tmplog >> $log 
            exit 1
        }
    done

    # copy them back to the server
    cp $tagfile $serverdir || { 
        echo Failed to commit $tag.list
        exit 5
    }
done

echo products tagged.

