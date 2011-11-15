#! /bin/bash
#
prog=`basename $0`
adjustCmd=/home/rplante/svn/servertools-trunk/bin/adjustmanfortags.py
tag=current

function taggedVersion {
    echo $1 | sed -e 's/[\+\-].*$//'
}
function buildNumber {
    echo $1 | sed -e 's/^.*[\+\-]//'
}
function productDirName {
    echo "$1/$2"
}
function manifestForVersion {
    local version=$1
    [ -z "$version" ] && version=rc
    local pre=$2
    [ -z "$pre" ] && pre=rc
    local ext=`echo $version | sed -e 's/^.*\([+-]\)/\1/'`
    local bn=`echo $ext | sed -e 's/^.//'`
    echo "$pre$bn.manifest"
} 

function usage {
    echo "Usage: $prog -d DIR product version manifest"
}
function help {
    usage
}

serverdir=
while getopts "d:h" opt; do
  case $opt in 
    d)
      serverdir=$OPTARG ;;
    h)
      help
      exit 0 ;;
  esac
done
shift $(($OPTIND - 1))

[ -z "$serverdir" ] && serverdir=$HOME/softstack/pkgs/test/w12a
prodname=$1
version=$2
manifest=$3
if { echo $version | grep -qsE '[\+][0-9]+'; }; then
    taggedas=`taggedVersion $version`
    bn=`buildNumber $version`
else
    taggedas=$version
    version=${taggedas}+1
    bn=1
fi
pdir=$serverdir/$prodname/$taggedas

cd $serverdir
[ -d "$serverdir" ] || {
    echo "${prog}: server directory does not exist: $serverdir"
    exit 1
}
pushd $pdir
bmanifest=`echo $manifest | sed -e "s/^.*\($bn.manifest\)$/b\1/"`
$adjustCmd -d $serverdir -t $tag $manifest > $bmanifest || {
    echo "$prog: Failed to standardize manifest file"
    exit 2
}
grep -qs $prodname/$taggedas $bmanifest || {
    echo "$prog: Failed to standardize manifest file (missing data)"
    exit 2
}
popd
exit 0

# release the package via its manifest
ext=`echo $bmanifest | sed -e 's/^b/\+/'`
cp $pdir/$bmanifest $prodname-$version$ext || exit 3
