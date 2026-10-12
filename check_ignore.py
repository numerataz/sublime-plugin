import os
import queue
import subprocess
import threading
import time

# On Windows, do not flash a console window for every git process
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _is_inside(cwd, path):
    try:
        base = os.path.normcase(os.path.abspath(cwd))
        target = os.path.normcase(os.path.abspath(path))
        return os.path.commonpath([base, target]) == base
    except ValueError:  # different drives on Windows
        return False


class _Worker:
    """One `git check-ignore --stdin` process and the thread that reads its answers."""

    def __init__(self, cwd, popen):
        self.started = time.monotonic()
        self.process = popen(
            ["git", "check-ignore", "--stdin", "-z", "-v", "-n"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )
        self.answers = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        # With -z -v -n git answers every path with four NUL-terminated fields:
        # source, line number, pattern, path. The pattern is empty when no rule matches.
        stdout = self.process.stdout
        fields = []
        field = bytearray()
        while True:
            byte = stdout.read(1)
            if not byte:
                break
            if byte == b"\0":
                fields.append(bytes(field))
                field = bytearray()
                if len(fields) == 4:
                    self.answers.put(tuple(fields))
                    fields = []
            else:
                field += byte
        self.answers.put(None)  # git exited

    def alive(self):
        return self.process.poll() is None

    def ask(self, path, timeout):
        """Returns True (ignored), False (not ignored) or None (no usable answer)."""
        data = os.fsencode(path)
        try:
            self.process.stdin.write(data + b"\0")
            self.process.stdin.flush()
            answer = self.answers.get(timeout=timeout)
        except (OSError, ValueError, queue.Empty):
            return None
        if answer is None or answer[3] != data:
            return None
        pattern = answer[2]
        # A pattern that starts with "!" is an exception: the file is NOT ignored
        return bool(pattern) and not pattern.startswith(b"!")

    def close(self):
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.kill()
        except OSError:
            pass


class IgnoreChecker:
    """Asks git whether a file is ignored, without starting git for every question.

    One long-running `git check-ignore --stdin` process is kept per folder, so a question
    takes well under a millisecond instead of tens of milliseconds. Git reads its ignore
    rules when it starts, so the process is restarted when `invalidate` is called (for
    example after a .gitignore is saved) and after `max_age` seconds, which also picks up
    changes to nested .gitignore files and to .git/info/exclude.

    `is_ignored` returns True or False, or None when git could not answer (not a
    repository, a path outside the folder, git missing, ...); the caller decides what to
    do then."""

    def __init__(self, max_age=60.0, retry_after=5.0, timeout=2.0, popen=subprocess.Popen):
        self._max_age = max_age
        self._retry_after = retry_after
        self._timeout = timeout
        self._popen = popen
        self._lock = threading.Lock()
        self._workers = {}
        self._failed_at = {}

    def is_ignored(self, cwd, path):
        if not cwd or not path or not _is_inside(cwd, path):
            return None
        with self._lock:
            now = time.monotonic()
            if now - self._failed_at.get(cwd, -1e9) < self._retry_after:
                return None
            worker = self._workers.get(cwd)
            if worker and (not worker.alive() or now - worker.started > self._max_age):
                worker.close()
                worker = None
            if worker is None:
                try:
                    worker = _Worker(cwd, self._popen)
                except OSError:
                    self._failed_at[cwd] = now
                    return None
                self._workers[cwd] = worker
            result = worker.ask(path, self._timeout)
            if result is None:
                # Not a repository, git exited or stopped answering: start over next time,
                # but not on every keystroke
                worker.close()
                self._workers.pop(cwd, None)
                self._failed_at[cwd] = now
            return result

    def invalidate(self, cwd=None):
        """Forget the running process(es), so the next question re-reads the ignore rules."""
        with self._lock:
            for key in [cwd] if cwd is not None else list(self._workers):
                worker = self._workers.pop(key, None)
                if worker:
                    worker.close()

    def close(self):
        self.invalidate()
