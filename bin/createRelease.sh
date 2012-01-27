#! /bin/bash
#
# createRelease.sh -- create the artifacts required for a release of an 
#                     LSST software product.
# 
# This script can be used to generate the manifest required to request a 
# release of a product.  To accomplish the creation of the manifest, this 
# script will:
#  1.  extract the source for the requested tag from the source repository,
#  2.  build the product,
#  3.  run and check its tests,
#  4.  install the product into a sandbox,
#  5.  generate the artifacts for the release, including the manifest.
# Unless the -n is used, all generated files except the manifest will be 
# deleted except for the manifest.  
#
prog=`basename $0 | sed -e 's/\..*$//'`
SHELL=/bin/bash
refstack=/lsst/DC3/stacks/default
workdir=$PWD/${prog}-work.$$
startdir=$PWD

[ -n "$DEVENV_SERVERTOOLS_DIR" ] || {
    echo "${prog}: devenv_servertools not setup"
    exit 1
}
prodhome=$DEVENV_SERVERTOOLS_DIR
libdir="$prodhome/lib"
reposExtractLib="$libdir/gitReposExtract.sh"     # default; override in conf
releaseFunctionLib="$libdir/releaseFunction.sh"  # default; override in conf

function usage {
    echo  Usage: `basename $0` "[-c FILE -w DIR -r DIR -s DIR -c DIR -d DIR]" 
    echo "           [-j NUM -b NUM -o PATH -inh] [-M|-S]" PRODUCT VERSION 
}

function help {
    usage
    cat <<EOF

Creates the artifacts that go into a tagged release of an LSST product.  When
the manifest argument is provided (and -n is not used), all artifacts except
the manifest will be cleaned up (deleted) and the manifest will be saved to
filename given by the argument. 

Options:
  -M       create only the manifest file
  -t TAG[,TAG...] a list of tags to build against.  If not provided, the 
             current dependencies will be used.  
  -o PATH  the output location: if -M is used, this is the file to write 
             the manifest to; if -S is used instead, this the root directory 
             of an existing server directory; otherwise, it is a name of simple 
             directory to create and place all release artifacts into.  If not 
             given, the file will be ./PRODUCT-VERSION+BNUM.manifest with -M, or 
             ./PRODUCT-VERSION+BNUM, otherwise.  
  -i       ignore failed tests: don't let failed tests prevent release
  -n       preserve all generated release artifacts
  -j NUM   use NUM threads when building
  -c FILE  the configuration file to use 
  -w DIR   a writable 'work' directory where temporary files can be written;
             if not given
  -r DIR   the reference stack directory
  -s DIR   the source directory to use to build the code 
  -d DIR   a development sandbox for installing a test installation
  -S DIR   staging package server to write release artifacts into
  -b BNUM  take BNUM as the build number for the new release
  -h       print this help and exit

EOF
}

configfile=$prodhome/conf/createRelease_conf.sh
usebuildthreads=4
ignorefailedtests=
testsHaveFailed=
noclean=
userworkdir=
tmpsrcdir=
buildNum=
output=
manifestOnly=
taglist=

while getopts "r:t:w:s:d:o:c:j:b:inMSh" opt; do
  case $opt in 
    c)
      configfile=$OPTARG 
      [ -f "$configfile" ] || {
          echo "${prog}: config file not found:" $configfile
          exit 1
      }
      ;;
    r)
      refstack=$OPTARG ;;
    w)
      userworkdir=$OPTARG 
      workdir=$userworkdir ;;
    s)
      srcdir=$OPTARG ;;
    d)
      sandbox=$OPTARG ;;
    o)
      output=$OPTARG ;;
    t)
      taglist=$OPTARG ;;
    j)
      usebuildthreads=$OPTARG ;;
    b)
      buildNum=$OPTARG ;;
    S)
      srvroutdir=1 ;;
    M)
      manifestOnly=1 ;;
    i)
      ignorefailedtests=1 ;;
    n)
      noclean=1 ;;
    h)
      help
      exit 0 ;;
  esac
done
shift $(($OPTIND - 1))

[ -n "$manifestOnly" -a -n "$srvroutdir" ] && {
    echo "${prog}: use only -S or -M or neither"
    usage
    exit 1
}

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
[ -e "$releaseFunctionLib" ] || {
    echo "${prog}:  releaseFunction library does not exist: $releaseFunctionLib"
    exit 1
}
. $releaseFunctionLib
[ -e "$reposExtractLib" ] || {
    echo "${prog}:  reposExtract plugin does not exist: $reposExtractLib"
    exit 1
}
. $reposExtractLib

{ echo $refstack | grep -qsE '^/'; } || refstack=$PWD/$refstack
{ echo $workdir  | grep -qsE '^/'; } || workdir=$PWD/$workdir

[ -d "$refstack" ] || {
    echo "Reference stack directory not found: $refstack"
    exit 2
}
[ -d "$workdir" ] || {
    mkdir -p $workdir || {
        echo "Unable to create scratch directory: $workdir"
        exit 2
    }
    { touch "$workdir/$prog.junk.$$" && rm "$workdir/$prog.junk.$$"; } || {
        echo "Scratch directory not writable: $workdir"
        exit 2
    }
}

prodname=$1; shift
version=$1;  
log=$workdir/$prog.log

[ -n "$srcdir" -a ! -d "$srcdir" ] && {
    echo "Product source code directory not found: $srcdir"
    exit 2
}


function onexit {
    echo "Cleaning up..."
    cd $startdir
    [ -z "$noclean" ] && {
        if [ -z "$userworkdir" ]; then
            rm -rf $workdir
        else
            [ -d "$srvrdir" ] && { echo $srrvdir | grep -v "^$userworkdir" | grep -sq '.'$$'$'; } && {
                rm -rf $srvrdir
            }
            [ -d "$sandbox" ] && { echo $sandbox | grep -sq '.'$$'$'; } && {
                rm -rf $sandbox
            }
            [ -n "$tmpsrcdir" -a -d "$tmpsrcdir" ] && { 
                echo $srcdir | grep -sq '.'$$'$'; } && {
                rm -rf $srcdir
            }
        fi
    } 
}

function interrupted {
    onexit
}

trap "onexit" 0
trap "interrupted" 1 2 3 13 15

clearlsst
source $refstack/loadLSST.sh
{ pushd $prodhome >/dev/null && setup -r . && popd >/dev/null; }
#pushd $HOME/git/lssteups >/dev/null && setup -r . && popd >/dev/null
#set -x

# make sure we have version without a build number and a build numer to use
{ echo $version | grep -sq +; } && {
    # strip off any build number but use it in lieu of -b
    [ -z "$buildNum" ] && {
        buildNum=`echo $version | sed -e 's/^.*+//'`
        { echo $buildNum | grep -sqP '\d+'; } || buildNum=
    }
    version=`taggedVersion $version`
}
[ -z "$buildNum" ] && {
    buildNum=`recommendBuildNumber $prodname $vers`
}

if [ -n "$manifestOnly" ]; then
    [ -z "$output" ] && output=$prodname-$version+$buildNum.manifest
else
    [ -z "$output" ] && output=$prodname-$version+$buildNum 
    [ -n "$srvroutdir" ] && srvrdir=$output
fi
if [ -z "$srvrdir" ]; then
    srvrdir="$workdir/pkgs.$$"
elif [ -z "$srvoutdir" -a ! -d "$srvrdir" ]; then
    echo "Server staging directory not found: $srvrdir"
    exit 2
fi
[ ! -e "$srvrdir/config.txt" ] && {
    makeStageServer $srvrdir || exit 2
}

[ -n "$output" -a -z "$srvroutdir" -a -e "$output" ] && {
    echo "${prog}: output file/dir exists: $output"
    exit 2
}


if [ -z "$sandbox" ]; then
    sandbox="$workdir/test.$$"
    mksandbox $sandbox || exit 2
elif [ ! -d "$sandbox" ]; then
    echo "Sandbox stack not found: $sandbox"
    exit 2
elif [ ! -d "$sandbox/ups_db" ]; then
    echo "Provided sandbox is not configured (no ups_db, use \"mksandbox\")"
    exit 2
fi

cd $workdir

# set the threads
oldSCONSFLAGS=$SCONSFLAGS
[ -n "$usebuildthreads" ] && {
    export SCONSFLAGS="-j $usebuildthreads"
    [ -n "$oldSCONSFLAGS" ] && SCONSFLAGS="$SCONSFLAGS $oldSCONSFLAGS"
}

# extract (and bundle) the source
[ -z "$srcdir" ] && {
    pdname=`productDirName $prodname $version`
    tmpsrcdir=$workdir/$pdname
    extractProductSource $prodname $version $pdname || exit $?
    srcdir=$tmpsrcdir
}

# build the product
EUPS_PATH=$refstack
setupopts=
[ -n "$taglist" ] && {
    tagarg=
    [ -n "$taglist" ] && {
        for tag in `echo $taglist|sed -e 's/,/ /g'`; do
           tagarg="$tagarg --tag=$tag" 
        done
    }
    tagarg="$tagarg --tag=current"
    setupopts=$tagarg
}
sconsopts=
[ -n "$usebuildthreads" ] && sconsopts="-j $usebuildthreads"
buildProduct $prodname $version+$buildNum $srcdir "$setupopts" "$sconsopts" \
  || exit $?

# check the tests
checkTests $srcdir || {
    err=$?
    if [ -n "$ignorefailedtests" ]; then
        echo "Ignoring failed tests results"
    else
        exit $err
    fi
}

EUPS_PATH=$refstack
installProduct $prodname $version+$buildNum $srcdir $sandbox "$setupopts" "$sconsopts" || exit $?

EUPS_PATH=$refstack
distribcreate $prodname $version+$buildNum $srvrdir $workdir $sandbox || exit $?

[ -d "$srvrdir/$prodname/$version" ] || {
    echo "${prog}: Failed to create artifacts in $prodname/$version"
    echo "    under $srvrdir"
    exit 9
}

cd $startdir

# save the results
if [ -n "$manifestOnly" ]; then
    echo Moving manifest to $output...
    mv $srvrdir/$prodname/$version/b$buildNum.manifest $output || exit 10
elif [ -z "$srvroutdir" ]; then 
    echo Moving release artifacts to $output...
    mv $srvrdir/$prodname/$version $output || exit 10
else 
    echo Release artifacts in $srvrdir/$prodname/$version
fi

exit 0
        