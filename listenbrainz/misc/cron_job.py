#!/usr/bin/env python3

from collections import deque
import contextlib
import subprocess
import sys
import os

LINES_IN_LOG_SNIPPET = 500

newlines = ['\n', '\r\n', '\r']
def monitor(proc):
    stdout = getattr(proc, "stdout")
    os.set_blocking(stdout.fileno(), False)
    stderr = getattr(proc, "stderr")
    os.set_blocking(stderr.fileno(), False)

    log_stdout = deque(maxlen=LINES_IN_LOG_SNIPPET)
    log_stderr = deque(maxlen=LINES_IN_LOG_SNIPPET)

    with contextlib.closing(stdout):
        with contextlib.closing(stderr):
            stdout_line = ""
            stderr_line = ""
            while True:
                if proc.poll() is not None:
                    return list(log_stdout), list(log_stderr)
                
                # Process stdout
                ch = stdout.read(1)
                if ch == "":
                    continue

                if ch in newlines:
                    sys.stdout.write(stdout_line + ch)
                    log_stdout.append(stdout_line)
                    stdout_line = ""
                    continue

                stdout_line += ch

                # Process stderr
                ch = stderr.read(1)
                if ch == "":
                    continue

                if ch in newlines:
                    sys.stdout.write(stderr_line + ch)
                    log_stderr.append(stderr_line)
                    stderr_line = ""
                    continue

                stderr_line += ch

def monitor_process(cmd):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    stdout, stderr = monitor(proc)
    print("proc status %d" % proc.returncode)
    return proc.returncode, stdout, stderr


def main():
    args = sys.argv[1:]
    if not args:
        sys.stderr.write("Error: Must provide one program to execute.")
        sys.exit(-1)

    try:
        ret, stdout, stderr = monitor_process(args)
    except KeyboardInterrupt:
        print("Interrupted, exit with -1")
        sys.exit(-1)

    if ret == 0:
        print("Exit with success!")
        sys.exit(0)

    # We did not exit successfully, so report an error
    print("Script failed. stdout/stderr:")
    for line in stdout:
        print("[stdout]", line)

    for line in stderr:
        print("[stderr]", line)

    print("Exit with status %d" % ret)
    sys.exit(ret)




if __name__ == "__main__":
    main()
