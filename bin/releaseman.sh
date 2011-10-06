#! /bin/bash
#
prog=`basename $0`
dest=/lsst_ibrix/lsst/softstack/pkgs/test/dc4
path=$1

[ -n "$path" ] || {
    echo ${prog}: input manifest not provided
    exit 1
}
[ -e "$path" ] || {
    echo ${prog}: input manifest not found
    exit 1
}
[ -e "manifests" ] || {
    echo ${prog}: manifests directory not found
    exit 1
}

bmanifest=`basename $path`
fromdir=`dirname $path`
release=`basename $fromdir`
fromdir=`dirname $fromdir`
product=`basename $fromdir`
fromdir=`dirname $fromdir`
pdir=$product/$release
external=`basename $fromdir`
[ $external == '.' -o $external != 'external' ] && external=
if [ $product == '.' -o $release == '.' ]; then
    echo "${prog}: unable to identify product from: $path" 1>&2
    exit 2
fi
todir=$dest
[ -n $external ] && todir=$todir/$external

build=`echo $bmanifest | sed -e 's/^b//' -e 's/\.manifest$//'` 

echo Writing manifests/${product}-${release}+${build}.manifest...
exec cp -i $path manifests/${product}-${release}+${build}.manifest
