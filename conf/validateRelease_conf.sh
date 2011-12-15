#! /bin/bash
#
eval `loadConfigfileIntoShell.py $DEVENV_SERVERTOOLS/conf/common_conf.py`

[ -z "$stackbase"   ] && stackbase=$conf_stackbase
[ -z "$refstack"    ] && stackbase=$conf_refstack
[ -z "$teststack"   ] && teststack=$conf_teststack
[ -z "$serverstage" ] && serverstage=$conf_serverstage
[ -z "$builddir" ]    && builddir=$conf_builddir
[ -z "$usebuildthreads" ] && usebuildthreads=$conf_usebuildthreads

reposExtractLib="$libdir/gitReposExtract.sh" 
copyPackageLib="$libdir/rsyncCopyPackage.sh"

