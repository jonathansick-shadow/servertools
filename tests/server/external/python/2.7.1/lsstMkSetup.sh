#! /bin/bash
#

# given an eups package name, print the name of the environment variable 
# that gives its location.  
function eupsPkgDirName {
    echo -n $1 | tr a-z A-Z
    echo _DIR
}

# return 0 if the given package is setup via EUPS or 1 otherwise.  This 
# checks to see if the appropriate package directory enviroment variable is 
# set.  
function eupsPkgDir {
    local prod_dir_var=`eupsPkgDirName $1`
    local prod_dir=`eval echo \\\$$prod_dir_var`
    [ -n "$prod_dir" ] && { echo "$prod_dir"; return 0; }
    return 1
}

# given an eups package name, print the expect path for libraries provided 
# by that package.  Nothing is printed if the package is not currently setup
function eupsPkgLibPath {
    local prod_dir=`eupsPkgDir $1`
    [ -n "$prod_dir" ] && echo $prod_dir/lib
}

# look for a library among a list of directories as a way to see if 
# it is available.  This will look for files call lib{libname}.a.  The path
# to the first directory where the library was found will be printed.
# @param libname    the name of library
# @return 0 if the library was found, 1 if not
function findLibLocation {
    local _paths=(`standardLibPaths`)
    local _path
    for _path in ${_paths[*]}; do
        [ -r "$_path/lib${1}.*" ] && { echo $_path; return 0; }
    done
    return 0
}

# print to standard out a -L argument for finding a particular library.
# Nothing is printed if a library location is not found or not needed 
# (because the libarary should be in a standard location like /usr/lib).
# @param libname    the library name whose filename is lib[libname].a
# @param pkgname    the name of an EUPS package expected to the library.  
#                     If given, this package will be search first for the 
#                     library.  
# @return  0 if the library was found, 1 if not.
function libLocation {
    [ -z "$1" ] && { echo libLocation: missing library name; return 1; }
    if [ -n "$2" ]; then
        local out=`eupsPkgLibPath $1`
        [ -n "$out" ] && { echo "$out"; return 0; }
    fi

    findLibLocation "$1"
}

# print to standard out a space-delimited list of the standard directory 
# paths where OS-installed static libraries can be found.  This list is 
# platform-dependent
#
function standardLibPaths {
    echo ${lib_dirs_common[*]} ${lib_dirs_platform[*]}
}

lib_dirs_common=( /usr/lib /lib /usr/local/lib )
lib_dirs_platform=( /usr/lib64 )
lib_dirs=`standardLibPaths`

##########################################################################

# customize the Setup file
grep -v '^#' Modules/Setup.dist | grep -v -E '^\s*$' > Modules/Setup.lsst

# configure Tcl/Tk support:
tk_base_version=`echo $SETUP_TCLTK | awk '{print $2}' | sed -e 's/[a-zA-Z_\-].*//' -e 's/\./ /g' | awk '{printf("%s %s\n", $1,$2)}' | sed -e 's/ /./g'` 
cat >> Modules/Setup.lsst <<EOF

# The _tkinter module

_tkinter _tkinter.c tkappinit.c -DWITH_APPINIT \
	-L$TCLTK_DIR/lib -I$TCLTK_DIR/include -I/usr/X11R6/include \
	-ltk$tk_base_version -ltcl$tk_base_version -lX11

EOF

# configure readline support 
if [ "$EUPS_FLAVOR" != Darwin* ]; then
    libloc=
    lib_path_opt=
    libloc=`libLocation readline` && {
        eupsPkgDir readline || lib_path_opt="$lib_path_opt -L$libloc"
    }
    libloc=`libLocation termcap` && {
        eupsPkgDir termcap || lib_path_opt="$lib_path_opt -L$libloc"
    }
    cat >> Modules/Setup.lsst <<EOF

# GNU readline

readline readline.c $lib_path_opt -lreadline -ltermcap
EOF
fi

# configure zlib support when it is available via EUPS.  It will get 
# compiled in automatically if zlib is installed as part of the OS.
# 
proddir=`eupsPkgDir zlib` && {
    cat >> Modules/Setup.lsst <<EOF

# The zlib module
# 
zlib zlibmodule.c -I${proddir}/include -L${proddir}/lib -lz
EOF
}

cp Modules/Setup.lsst Modules/Setup
