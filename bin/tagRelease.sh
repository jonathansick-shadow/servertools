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

libdir="$prodhome/lib"
configfile="$prodhome/conf/submitRelease_conf.sh"
releaseFunctionLib="$libdir/releaseFunction.sh"

function usage {
    echo Usage: ${prog}: "-t TAG[,TAG] [-U USER -Ln] product version ..."
}

function help {
    usage
    echo <<EOF
Assign one or more server tags to one or more distributions.  The -D option 
(identifying the server directory) and at least one -t occurance (to name
the tag to assign is required.  The stable tag is not assignable with this 
command. 

Options:
  -t TAG[,TAG...]   server tag to assign to the given list of products

  -D                do not tag the products' dependents"
  -c FILE           the configuration file to use
  -w DIR            a 'work' directory to use for private scratch (def: /tmp)
  -T                deploy to test server only"
  -U USER           identify the user running this command
  -L                log the tagging in the configured area
EOF
}

tags=()
noclean=
dolog=
testserver=
nodepuprev=

origargs=($*)

while getopts ":t:w:c:U:LTDnh" opt; do
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
    D)
      nodepuprev=1 ;;
    L)
      dolog=1 ;;
    T)
      testserver=1 ;;
    U)
      asuser=$OPTARG ;;
    h)
      help
      exit 0 ;;
    '?')
      echo ${prog}: illegal option -- $OPTARG
      exit 1 ;;
  esac
done
shift $(($OPTIND - 1))

[ -e "$configfile" ] && \
    . $configfile
[ -e "$releaseFunctionLib" ] || {
    echo "${prog}:  releaseFunction library does not exist: $releaseFunctionLib"
    exit 1
}
. $releaseFunctionLib
[ ${#tags[@]} -eq 0 ] && {
    echo ${prog}: No tags specified
    exit 1
}
[ $# -eq 0 ] && {
    echo ${prog}: No products listed
    exit 1
}
products=()
prodname=
for prod in $*; do 
    if [ -n "$prodname" ]; then
        echo $prod | egrep -sq '^[0-9]' || {
            echo ${prog}: product syntax error: $prod does not look like a version for product $prodname
            exit 1
        }
        products=(${products[*]} ${prodname}-$prod)
        prodname=
    else
        if { echo $prod | grep -qse -; }; then
            products=(${products[*]} $prod)
        else
            prodname=$prod
        fi
    fi
done
[ -n "$prodname" ] && {
    echo ${prog}: Missing product version for $prodname
    exit 1
}

sessiondir="$workdir/$prog.$$"
mkdir $sessiondir

function onexit {
    [ -z "$noclean" -a -n "$sessiondir" -a -d "$sessiondir" ] && {
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
for tag in ${tags[*]}; do
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
for prod in ${products[*]}; do
    [ -e "$stagesrvr/manifests/$prod.manifest" ] || bad=(${bad[*]} $prod)
done
[ ${#bad[*]} -gt 0 ] && {
    echo "${prog}: Unreleased products:" ${bad[*]} | tee -a $log
    exit 4
}
for prod in ${products[*]}; do
    name=`echo $prod | sed -e 's/-.*$//'`
    [ -d "$stagesrvr/name" -o -d "$stagesrvr/pseudo/$name" ] && {
        bad=(${bad[*]} $name)
    }
done
[ ${#bad[*]} -gt 0 ] && {
    echo "${prog}: Non-lsst products:" ${bad[*]} | tee -a $log
    exit 4
}

# add in dependents
[ -z "$nodepuprev" ] && {
    specified=(${products[*]})
    for prod in ${specified[*]}; do
        pv=(`echo $prod | sed -e 's/-/ /'`)
        deps=(`grep "^${pv[0]}" $stagesrvr/manifests/*.manifest | grep ${pv[1]} | sed -e 's/:.*//' -e 's/.manifest$//' -e 's/^.*\///' | grep '+'`)
        for dep in ${deps[*]}; do
            echo ${products[*]} | grep -sq $dep || {
                products=(${products[*]} $dep)
            }
        done
    done
}
[ -n "$dolog" ] && {
    echo -n Tagging these products >> $log
    [ -z "$nodepuprev" ] && echo -n " (with dependencies)" >> $log
    echo ":" >> $log
    echo -n "  " >> $log
    echo ${products[*]} | sed -e 's/ /\n  /g' >> $log
}

# now update the tags
for tag in ${tags[*]}; do
    # to make this command atomic (and rollback-able) copy the tag file to 
    # a work area and operate on it there.
    tagfile=$stagesrvr/$tag.list
    cp $tagfile $sessiondir || {
        echo ${prog}: Failed to write to $sessiondir | tee -a $log
        exit 5
    }
    tagfile=$sessiondir/$tag.list

    for prod in ${products[*]}; do
        pv=(`echo $prod | sed -e 's/-/ /'`)
        echo tagRelease.py -d $sessiondir ${pv[*]} $tag >> $log
        tmplog=$sessiondir/tagRelease-py.log
        tagRelease.py -d $sessiondir ${pv[*]} $tag > $tmplog 2>&1 || {
            cat $tmplog
            [ -n "$dolog" ] && cat $tmplog >> $log 
            exit 1
        }
    done

    # copy them back to the server
    cp $tagfile $stagesrvr || { 
        echo Failed to commit $tag.list
        exit 5
    }
done

syncerr=
[ -n "$testserver" ] || synctostd || syncerr=6
synctoweb || syncerr=6
[ -n "$syncerr" ] && {
    echo ${prog}: Sync with server failed | tee -a $log
    exit $syncerr
}
echo Server tags assigned.

# update the tags in the reference stack
echo Updating tags in reference stack | tee -a $log
for prod in ${products[*]}; do
    tagarg=
    for tag in ${tags[*]}; do
        tagarg="$tagarg -t $tag"
    echo eups declare $tagarg `echo $prod | sed -e 's/-/ /'` | tee -a $log
    eups declare $tagarg `echo $prod | sed -e 's/-/ /'` 
done


