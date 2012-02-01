#! /bin/bash
#
# use Git to extract a product
# @param prodname   name of product to extract
# @param version    version of the product as tagged in the repository
# @param dirname    the root directory for the output tarball
function reposExtract {
    local prodname=$1 taggedas=$2 proddir=$3
    local reposname=$prodname
    local reposroot=git://git.lsstcorp.org/LSST/DMS
    if [ "$1" = "lssteups" ]; then
        reposname=devenv/lssteups
    elif [ "$1" = "lsst" ]; then
        reposname=devenv/lsst
    elif [ "$prodname" = "sconsUtils" ]; then
        reposname=devenv/sconsUtils
    elif [ "$prodname" = "devenv_servertools" ]; then
        reposname=devenv/servertools
    else
        reposname=$prodname
    fi

    echo git archive --format=tar --prefix=$proddir/                \
                     --remote=$reposroot/$reposname.git $taggedas \| \
             gzip -c \>  $prodname-$taggedas.tar.gz
    { git archive --format=tar --prefix=$proddir/   \
                --remote=$reposroot/$reposname.git $taggedas || return $?; } | \
        gzip -c >  $prodname-$taggedas.tar.gz

    tar xzf $prodname-$taggedas.tar.gz
}
