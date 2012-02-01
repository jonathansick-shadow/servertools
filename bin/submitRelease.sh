#! /bin/bash -
#
# submitRelease.sh -- request the release of a tagged version of a product
# 
# This script is intended to run as a user who has permission to write to 
# the distribution server and to the reference software stack.  Non-privileged
# users would invoke this via a wrapper script (submitrelease)
#
SHELL=/bin/bash
refstack=/lsst/DC3/stacks/default
workdir=/lsst/DC3/distrib/default/submitRelease
stagesrvr=/lsst/DC3/distrib/w12/www
startdir=$PWD
prog=`basename $0 | sed -e 's/\..*$//'`
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
reposExtractLib="$libdir/gitReposExtract.sh"  # default; override in conf
copyPackageLib="$libdir/rsyncCopyPackage.sh"  # default; override in conf
releaseFunctionLib="$libdir/releaseFunction.sh"

function usage {
    echo Usage: `basename $0` "[-c FILE -r DIR -j NUM -t TAGS -iCnVh] product version [manifest]"
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
    echo "Admin/Debug Options:"
    echo "  -T          deploy to test server only"
    echo "  -c FILE     the configuration file to use"
    echo "  -w DIR      a 'work' directory to use for private scratch"
    echo "  -r DIR      the reference stack directory"
    echo "  -U USER     identify the user running this command"
    echo "  -L          log the progress in the configured area"
}

usebuildthreads=4
ignorefailedtests=
testsHaveFailed=
checkTests=
reftags=
testserver=
asuser=
allowRerelease=
nocommit=
nodepuprev=
isrerelease=

while getopts "c:j:r:w:t:U:iDRVCTLnh" opt; do
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
      workdir=$OPTARG ;;
    j)
      usebuildthreads=$OPTARG ;;
    i)
      ignorefailedtests=1 ;;
    V)
      checkTests=1 ;;
    C)
      nocommit=1 ;;
    D)
      nodepuprev=1 ;;
    R)
      allowRerelease=1;;
    n)
      noclean=1 ;;
    t)
      reftags=$OPTARG ;;
    T)
      testserver=1 ;;
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

[ -e "$configfile" ] && \
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
[ -e "$copyPackageLib" ] || {
    echo "${prog}:  copyPackage plugin does not exist: $copyPackageLib"
    exit 1
}
DEVENV_SERVERTOOLS_DIR=$prodhome . $copyPackageLib

{ echo $refstack | grep -qsE '^/'; } || refstack=$PWD/$refstack
{ echo $workdir  | grep -qsE '^/'; } || workdir=$PWD/$workdir

[ -d "$refstack" ] || {
    echo "Reference stack directory not found: $refstack"
    exit 2
}
[ -d "$workdir" ] || {
    echo "Reference stack directory not found: $workdir"
    exit 2
}



##
# setup the working directory for the current session
#
function setupSessionDir {
    [ -d "$sessiondir" ] || mkdir $sessiondir
    local host=`hostname | sed -e 's/\..*//'`
    echo $$ ${asuser}@$host > $sessiondir/$prog.pid
    mksandbox $sandbox || return 3
    makeStageServer $createpkgs || return 3
}

## 
# check to see if a session directory is in use
#
function checkForSession {
    [ -e "$sessiondir" ] && { 
        echo -n "Release of $prodname $version is already in progress "
        if [ -e "$sessiondir/$prog.pid" ]; then
            who=`cat $sessiondir/$prog.pid`
            pid=`echo $who | awk '{print $1}'`
            user=`echo $who | awk '{print $2}'`
            [ -z "$user" ] && user="unknown"
            echo -n "by user $user (pid=$pid) "
            ls -gG --time-style=long-iso "$sessiondir/$prog.pid" | awk '{print $4,$5}'
        fi
        echo "Aborting."
        [ -n "$dolog" ] && {
            echo "Already in progress by user $user (pid=$pid)" >> $log
        }
        sessiondir=
        return 1
    }
    return 0
}

##
# deploy the product artifacts to the staging server.  
function deployToStageServer {
    echo Deploying to server... | tee -a $log
    [ -d $createpkgs/$prodname/$version ] || {
        echo Failed to find server artifacts: $createpkgs/$prodname/$version | tee -a $log
        return 3
    }
    [ -d $stagesrvr ] || { 
        echo Missing stage server directory: $stagesrvr | tee -a $log
        return 3
    }
    pushd $createpkgs > /dev/null

    # update the header of the manifest to identify who submitted it
    local manifest=$prodname/$version/b1.manifest
    local now=`date`
    local ins=`printf "# Submitter:    %s\n# Date:         %s\n#" $asuser "$now"`
    echo sed -e "/^# pkg/ i\\$ins" $manifest \> $manifest.upd >> $log
    sed -e "/^# pkg/ i\\$ins" $manifest > $manifest.upd || return 3
    [ -f "$manifest.upd" ] || return 3
    echo mv $manifest.upd $manifest >> $log
    mv $manifest.upd $manifest

    if [ -d "$stagesrvr/$prodname/$version" ]; then
        local rversion=`grep "^$prodname " $manifest | awk '{print $3}'`
        local oldbn=`echo $rversion | sed -e 's/^.*+//'`
        local oldmf=$manifest
        
        manifest=$prodname/$version/b${bn}.manifest
        while [ -e "$stagesrvr/$manifest" ]; do
            bn=`expr $bn +  1`
            manifest=$prodname/$version/b${bn}.manifest
        done
        [ "$bn" -ne "$oldbn" ] && {
            sed -e "/$prodname / s/+[0-9][0-9]*/+$bn/g" \
                $oldmf > $manifest || return 3
            rm $oldmf || return 3
        }
    fi

    if [ -n "$isrerelease" ]; then
        # do not write over tar-ball etc.; only copy new manifest
        cp $manifest $stagesrvr/$manifest || {
            echo ${prog}: Failed to copy over $manifest for re-release | tee -a $log
            return 9
        }
    else
        # new release; copy all artifacts
        { tar cf - $prodname/$version | (cd $stagesrvr; tar xf -); } || {
            echo ${prog}: Failed to copy "(via tar)" artifacts for new release | tee -a $log
            return 9
        }
    fi
    # install manifest into manifests directory
    echo cp $manifest $stagesrvr/manifests/$prodname-${version}+${bn}.manifest >> $log
    cp $manifest $stagesrvr/manifests/$prodname-${version}+${bn}.manifest || {
        echo ${prog}: Failed to complete installation of manifest | tee -a $log
        return 9
    }

    synctoweb || return 10
    [ -n "$testserver" ] || synctostd || return 10
}

function uprevDependents {
    echo "Up-reving dependents for $prodname $version" | tee -a $log

    outfile=
    [ -n "$1" ] && outfile="-o $1"

    tagarg=
    [ -n "$reftags" ] && tagarg="-T $reftags"

    echo autouprev.py -d $stagesrvr $outfile $tagarg --submitter=$asuser -r $prodname/${version}+${bn} | tee -a $log
    autouprev.py -d $stagesrvr $outfile $tagarg --submitter=$asuser -r $prodname/${version}+${bn} ||  return 9

    synctoweb || return 10
    [ -n "$testserver" ] || synctostd || return 10
}

##
# validate the requested release via a test deployment and install.  If a 
# manifest was not provided, one will be generated.
#
function validateVersion {
    # assume we are in $sessiondir
    # package up the source
    [ -d "$tarrootdir" ] || {
        if [ -f "${tarrootdir}.tar.gz" ]; then
            tar xzf "${tarrootdir}.tar.gz" || return 6
        else
            echo "${prog}: Missing source code: $tarrootdir"
            return 6
        fi
    }
    local buildnum=$bn
    local dmanifest=$createpkgs/$prodname/$version/b$bn.manifest
    if [ -z "$manifest" ]; then
        # create a manifest if one was not provided
        createManifest || return $?
    else
        # 
        mkdir -p $createpkgs/$prodname/$version

        # convert the build number if need be
        local rversion=`grep "^$prodname " $manifest | awk '{print $3}'`
        buildnum=`echo $rversion | sed -e 's/^.*+//'`
        if [ $bn -eq $buildnum ]; then
            cp $manifest $dmanifest || return 6
        else
            sed -e "/$prodname / s/+[0-9][0-9]*/+$bn/g" \
                $manifest > $dmanifest || return 6
        fi
        cp "${tarrootdir}.tar.gz" $createpkgs/$prodname/$version || return 6
        cp "${tarrootdir}/ups/$prodname.table" $createpkgs/$prodname/$version || return 6
        checkTests=1
    fi
    echo cp $dmanifest $createpkgs/manifests/${tarrootdir}+$buildnum.manifest | tee -a $log
    cp $dmanifest $createpkgs/manifests/${tarrootdir}+$buildnum.manifest

    # install from test server
    echo Testing install from server... | tee -a $log
    EUPS_PATH=${sandbox}:$EUPS_PATH
    echo EUPS_PATH=$EUPS_PATH >> $log
    [ -n "$usebuildthreads" ] && { 
        export SCONSFLAGS="-j $usebuildthreads"
        echo SCONSFLAGS=$SCONSFLAGS | tee -a $log
    }
    echo eups distrib install --nolocks --noclean -r $createpkgs $prodname ${version}+$buildnum | tee -a $log
    eups distrib install --nolocks --noclean -r $createpkgs $prodname ${version}+$buildnum || {
        echo ${prog}: test-install failed | tee -a $log
        return 7
    }

    local flavor=`eups flavor`
    pushd $sandbox/EupsBuildDir/$flavor/${tarrootdir}+$buildnum > /dev/null || return 2
    [ -n "$checkTests" ] && {
        # check the tests
        echo Checking tests...
        [ -d "${tarrootdir}/tests/.tests" ] || {
            # the tests need to be run
            [ -e "eupssetup.sh" ] && source eupssetup.sh
            cd ${tarrootdir} >/dev/null
            opts=
            [ -n "$usebuildthreads" ] && opts="-j $usebuildthreads"
            echo scons opt=3 version=${version}+$buildnum $opts tests | tee -a $log
            scons opt=3 version=${version}+$buildnum $opts tests || return 8
            mkdir -p tests/.tests
            { checkTests $PWD && checkTests=; } || {
                echo "rechecking..."
                scons opt=3 tests || return 8
            }
            cd $sandbox/EupsBuildDir/$flavor/${tarrootdir}+$buildnum >/dev/null
        }
    }
    [ -n "$checkTests" ] && {
        checkTests $tarrootdir || {
            err=$?
            if [ -n "$ignorefailedtests" ]; then
                echo "Ignoring failed tests results" | tee -a $log
            else
                return $9
            fi
        }
    }
    EUPS_PATH=$refstack
    popd >/dev/null
}

##
# create a manifest file for the product.  This requires building and 
# installing the product.
#
function createManifest {
    local opts
    opts=
    [ -n "$usebuildthreads" ] && opts="$opts -j $usebuildthreads"
    [ -n "$ignorefailedtests" ] && opts="$opts -i"
    [ -n "$reftags" ] && opts="$opts -t $reftags"
    [ -n "$noclean" ] && opts="$opts -n"

    echo createRelease.sh -S -b $bn -r $refstack -w "$sessiondir" -s "$sessiondir/$tarrootdir" -o "$createpkgs" $opts $prodname $version | tee -a $log
    createRelease.sh -S -b $bn -r $refstack -w "$sessiondir" -s "$sessiondir/$tarrootdir" -o "$createpkgs" $opts $prodname $version || {
        echo ${prog}: Failed to create manifest | tee -a $log
        return `expr $? + 10`
    }
    manifest="$createpkgs/$product/$version/b1.manifest"
}

##
# install all the new releases into the reference stack.
# 
function updateRefStack {
    updatelist=$1
    EUPS_PATH=$refstack
    [ -n "$usebuildthreads" ] && { 
        export SCONSFLAGS="-j $usebuildthreads"
        echo SCONSFLAGS=$SCONSFLAGS
    }

    bad=()
    [ -n "$nodepuprev" -a -f "$updatelist" ] && {
        bad=(`cat "$updatelist" | sed 's/ */-/'`)
    }

    tmplog=$sessiondir/install_${prodname}-${version}+${bn}.log
    echo EUPS_PKGROOT=$EUPS_PKGROOT
    echo eups distrib install --nolocks $prodname ${version}+${bn} | tee -a $log
    eups distrib install --nolocks $prodname ${version}+${bn} > $tmplog 2>&1 || {
        [ -n "$dolog" ] && cat $tmplog >> $log
        echo "${prog}: Trouble installing $prodname ${version}+${bn}" | tee -a $log
        echo "Disabling release..." | tee -a $log
        bad=($prodname/$version+$bn ${bad[@]})
        [ -n "$bad" ] && unreleaseDependents "${bad[@]}"
        return 1
    }

    [ -n "$nodepuprev" ] && return 0

    [ -f "$updatelist" ] || {
        echo "${prog}: Failed to find up-rev list file: $updatelist" | tee -a $log
        return 1
    }
    bad=()
    for manfile in `cat "$updatelist"`; do
        info=(`basename $manfile | sed -e 's/\.manifest$//' -e 's/-/ /'`)
        pname=${info[0]}
        vers=${info[1]}
        echo eups distrib install --nolocks $pname ${vers} | tee -a $log
        eups distrib install --nolocks $pname ${vers} || {
            echo "${prog}: Dependent $prodname ${version}+1 failed to install" | tee -a $log
            echo "Unreleasing $prodname ${version}+1..." 
            bad=(${bad[*]} $pname/$vers)
            unreleaseDependents $pname/$vers
        }
    done

    [ ${#bad[*]} -gt 0 ] && {
        echo "The following dependent products did build successfully:" | tee -a $log
        {
            echo -n "  " | tee -a $log
            echo ${bad[*]} | sed -e 's/ /\n  /g' -e 's/\// /g'
        } | tee -a $log
        echo Their release have been cancelled. | tee -a $log
    }

    return 0
}

function unreleaseDependents {
    for prod in $*; do 
        local mfile=`echo $prod | sed -e 's/\//-/'`.manifest

        rm -f $stagesrvr/manifests/$mfile
    done
    [ -n "$testserver" ] || synctostd -r manifests
    synctoweb -r manifests
}

function onexit {
    if [ -z "$noclean" ]; then
        cd $startdir
        [ -n "$sessiondir" -a -d "$sessiondir" ] && {
            rm -rf $sessiondir
        }
    elif [ -n "$sessiondir" ]; then 
        echo "Work space (test builds, etc.) not removed:"
        echo "  $sessiondir"
        echo "run clearSubmitRelease to clean it up"
    fi
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

prodname=$1
version=$2
manifest=$3
if { echo $version | grep -qsE '[\+][0-9]+'; }; then
    ext=`echo $version | sed -e 's/.*+/+/'`
    echo "Note: ignoring build number extension as one will be assigned"
    version=`taggedVersion $version`
fi
tarrootdir=`productDirName $prodname $version`

[ -n "$dolog" ] && {
    [ -n "$logdir" ] || logdir=$workdir/logs
    log=$logdir/`date '+%Y-%m-%dT%H:%M:%S'`_$prodname-$version.log

    echo $prog ${origargs[*]} > $log
    echo LSST_HOME=$LSST_HOME >> $log
    echo EUPS_PATH=$EUPS_PATH >> $log
    echo EUPS_PKGROOT=$EUPS_PKGROOT >> $log
}

[ -n "$manifest" ] && {
    [ ! -f "$manifest" ] && {
        echo "${prog}: Manifest file not found: $manifest"
        exit 1
    }
    checkTests=1
    { echo $manifest | grep -qsE '^/'; } || manifest=$PWD/$manifest
}

sessiondir="$workdir/$prodname-$version"
sandbox="$sessiondir/test"
createpkgs="$sessiondir/pkgs"


# lock this session: prevent multiple simultaneous releases of the same version
checkForSession || exit 3
mkdir $sessiondir

# check to see if the product has already been released.
bn=1
eups distrib list $prodname | grep $prodname | grep $version > $sessiondir/previousreleases.txt
if [ -z "$allowRerelease" ]; then
    grep -qs $version $sessiondir/previousreleases.txt && {
        echo ${prog}: $prodname $version already release as... | tee -a $log
        cat $sessiondir/previousreleases.txt | tee -a $log
        echo "Consider using -R to re-release; aborting." | tee -a $log
        exit 1
    }
elif [ -s "$sessiondir/previousreleases.txt" ]; then
    isrerelease=1
    lastver=`sort $sessiondir/previousreleases.txt | tail -n -1 | awk '{print $3}'`
    lastbn=0
    { echo $lastver | egrep -qs '+[0-9]*$'; } && {
        lastbn=`echo $lastver | sed -e 's/.*+//'`
    }
    { expr $lastbn + 1 > /dev/null 2>&1; } && bn=`expr $lastbn + 1`
fi
[ -n "$dolog" ] && {
    [ -n "$isrerelease" ] && echo This is a re-release request >> $log
    echo Initializing build number to $bn >> $log
    echo >> $log
}
        
# setup up our work area
setupSessionDir || exit $?
cd "$sessiondir"

# extract the source and create tarball
extractProductSource $prodname $version $tarrootdir || exit $?

# do a test deployment and install using the given manifest.  If one was 
# not provided, create one.
validateVersion || exit $?
echo "Product has passed all tests; ready to deploy to server"

# send validated artifacts to the actual server.
if [ -z "$nocommit" ]; then
    deployToStageServer || exit $?

    # uprev the dependents
    status=
    updatelist=$sessiondir/updated.lis
    [ -n "$nodepuprev" ] || {
        uprevDependents $updatelist || status=$?
        echo "The dependents that need to be upreved:" >> $log
        cat $updatelist >> $log
    }

    # updating reference stack
    updateRefStack $updatelist || status=$?

    [ -z "$status" ] || {
        echo "${prog}: Problem upreving or updating stack; if necessary," | tee -a $log
        echo "    consult with software manager to fix."  | tee -a $log
        exit 10
    }

else
    echo "Release not committed to server (as per request)" | tee -a $log
fi






