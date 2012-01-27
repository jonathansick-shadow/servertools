#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef DST_INSTALL_DIR
#define DST_INSTALL_DIR /lsst/home/rplante/git/devenv_servertools
#endif
#define _QQ(x) #x
#define _QUOTED(x) _QQ(x)
#define DST_INSTALL_DIR_QUOTED _QUOTED(DST_INSTALL_DIR)

extern char **environ;
const char *pathenv = "PATH=/bin:/usr/bin";
const char *userenv = "USER=lsstsw";
const char *shenv   = "SHELL=bash";
const char *stvar   = "DEVENV_SERVERTOOLS_DIR";
const char *sthome  = DST_INSTALL_DIR_QUOTED;
const char *srscrp  = "bin/clearSubmitRelease.sh";

int main(int argc, char *argv[]) {
    int i=0;
    char **cmd;
    char *srpath;

    srpath = malloc( 2 + strlen(sthome) + strlen(srscrp) );
    strcpy(srpath, sthome);
    strcat(srpath, "/");
    strcat(srpath, srscrp);

    environ = malloc( 5 * sizeof(char*) );
    environ[0] = strdup(pathenv);
    environ[1] = strdup(userenv);
    environ[2] = strdup(shenv);
    environ[3] = malloc( 2 + strlen(stvar) + strlen(srpath) );
    strcpy(environ[3], stvar);
    strcat(environ[3], "=");
    strcat(environ[3], sthome);
    environ[4] = NULL;

    cmd = malloc( (argc+2) * sizeof(char*) );
    cmd[0] = argv[0];
    cmd[1] = strdup(srpath);
    for(i=1; i < argc; i++) 
        cmd[i+1] = argv[i];
    cmd[i+1] = NULL;

    execve("/bin/bash", cmd, environ);
    printf("%s: exec failed: %s\n", argv[0], strerror(errno));
}
