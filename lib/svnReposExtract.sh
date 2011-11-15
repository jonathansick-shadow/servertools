#! /bin/bash
#
# use SVN to extract a product
# @param prodname   name of product to extract
# @param version    version of the product as tagged in SVN
# @param dirname    the name of the directory to call the export.
function reposExtract {
    if { echo $1 | grep -s '_'; }; then
        prodname=`echo $1 | sed -e 's/_/\//g'`
    elif [ "$1" = "lssteups" ]; then
        prodname=devenv/lssteups
    elif [ "$1" = "sconsUtils" ]; then
        prodname=devenv/sconsUtils
    else
        prodname=$1
    fi

    svn export $LSST_DMS/$prodname/$2 $3 || return $?
}