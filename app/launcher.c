/*
 * etime.app launcher: runs `.venv/bin/python main.py` from the repo.
 *
 * Why a compiled launcher rather than a shell script: macOS grants Accessibility
 * (needed for the global hotkeys) to the *responsible* app, and a child process
 * stays attributed to the app that spawned it. Spawning Python as a child (not
 * exec-ing into it) makes that app etime.app, so the permission is listed as
 * "etime" instead of Terminal or Python.
 *
 * The repo path is baked in at build time (-DETIME_REPO=...), so code changes
 * take effect on the next launch with no rebuild. Output goes to
 * ~/.etime/etime.log since there's no terminal to print to.
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef ETIME_REPO
#error "build with -DETIME_REPO=\"/path/to/etime\""
#endif

#define LOG_ROTATE_BYTES (5 * 1024 * 1024)

extern char **environ;
static pid_t child = 0;

static void forward_signal(int sig) {
    if (child > 0) kill(child, sig);
}

int main(void) {
    const char *home = getenv("HOME");
    if (!home) return 1;

    char log_dir[4096], log_path[4096], old_log[4096];
    snprintf(log_dir, sizeof log_dir, "%s/.etime", home);
    snprintf(log_path, sizeof log_path, "%s/etime.log", log_dir);
    snprintf(old_log, sizeof old_log, "%s/etime.log.1", log_dir);
    mkdir(log_dir, 0755);

    struct stat st;
    if (stat(log_path, &st) == 0 && st.st_size > LOG_ROTATE_BYTES) rename(log_path, old_log);

    int log_fd = open(log_path, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (log_fd >= 0) {
        dup2(log_fd, STDOUT_FILENO);
        dup2(log_fd, STDERR_FILENO);
        close(log_fd);
    }

    if (chdir(ETIME_REPO) != 0) {
        fprintf(stderr, "etime launcher: cannot cd to %s: %s\n", ETIME_REPO, strerror(errno));
        return 1;
    }

    setenv("PYTHONUNBUFFERED", "1", 1);  // so prints reach the log as they happen

    char *argv[] = {"python", "main.py", NULL};
    int err = posix_spawn(&child, ETIME_REPO "/.venv/bin/python", NULL, NULL, argv, environ);
    if (err != 0) {
        fprintf(stderr, "etime launcher: cannot start %s/.venv/bin/python: %s\n",
                ETIME_REPO, strerror(err));
        return 1;
    }

    signal(SIGTERM, forward_signal);
    signal(SIGINT, forward_signal);
    signal(SIGHUP, forward_signal);

    int status = 0;
    while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
