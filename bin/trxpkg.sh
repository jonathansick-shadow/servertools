#! /bin/bash
#
prog=`basename $0`
dest=/lsst_ibrix/lsst/softstack/pkgs/test/dc4
path=$1

release=`basename $path`
fromdir=`dirname $path`
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

if [ ! -e "$path" ]; then
    echo ${prog}: product $path not found 1>&2
    exit 2
fi

build=1
version=$release
if { echo $release | grep -sq '+'; }; then 
    build=`echo $release | sed -e 's/^.*+//'`
    version=`echo $release | sed -e 's/+.*//'`
fi

if [ -e "$todir/$pdir" -o -e "$todir/$product/$version" ]; then
    echo ${prog}: Destination $product/$version already exists
    exit 3
fi

# transfer the files
pushd $fromdir > /dev/null 2>&1 || { 
    echo ${prog}: missing dir, $fromdir 1>&2
    exit 2; 
}
tar chf - $pdir | (cd $todir; tar xf -) || { 
    echo ${prog}: tar failure 1>&2
    exit 4
}
cd $todir

# drop +N from version dir
if [ "$version" != "$release" ]; then
    mv $pdir $product/$version
    pdir=$product/$version
fi

cd $pdir || { echo missing dir, $pdir; exit 2; }

# check for a build script
themanifest=the.manifest
if [ -e "$themanifest" ]; then
    bldfile=`grep '^>self' $themanifest | grep installFile= | sed -e 's/^.* installFile=//' -e 's/ .*$//'`
    [ -n "$bldfile" ] && echo "$product $version uses build script: $bldfile"
else
    themanifest=
fi

# build a manifest
pre=
[ -n "$external" ] && pre="$external/"
$dest/makemanifest.py -T -b $build -m $themanifest $pre$product/$version > b${build}.manifest

# print a current entry
printf "%-15s  %-9s  %-13s  %-12s\n" $product generic $version+$build $external
