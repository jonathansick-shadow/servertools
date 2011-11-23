#! /bin/bash
#
# use Git to extract a product
# @param prodname   name of product to extract
# @param version    version of the product as tagged in SVN
# @param dirname    the name of the directory to call the export.
function reposExtract {
    local prodname
    if { echo $1 | grep -s '_'; }; then
        prodname=`echo $1 | sed -e 's/_/\//g'`
    elif [ "$1" = "lssteups" ]; then
        prodname=devenv/lssteups
    elif [ "$1" = "lsst" ]; then
        prodname=devenv/lsst
    elif [ "$1" = "sconsUtils" ]; then
        prodname=devenv/sconsUtils
    else
        prodname=$1
    fi

    echo git archive --format=tar --prefix=$1-$taggedas/    \
                     --remote=$LSST_DMS/$prodname.git $taggedas \| \
             gzip -c \>  $1-$taggedas.tar.gz
    { git archive --format=tar --prefix=$1-$taggedas/   \
                --remote=$LSST_DMS/$prodname.git $taggedas || return $?; } | \
        gzip -c >  $1-$taggedas.tar.gz

    tar xzf $1-$taggedas.tar.gz
}
