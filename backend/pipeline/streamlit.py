"""Minimal headless `streamlit` shim for the FastAPI backend.

A few pipeline modules (caption_styler, gemini_image_generator, music_provider)
were written for the Streamlit UI and call a handful of `st.*` helpers for
progress/feedback. When running under FastAPI (no Streamlit installed), this
shim supplies no-op equivalents so those modules import and run headless.

Placed at the pipeline root (which is on sys.path), it only takes effect when
the real `streamlit` package is absent from the environment.
"""

import contextlib
import sys


class _Progress:
    def progress(self, *a, **k):
        return self

    def empty(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@contextlib.contextmanager
def _spinner(text=""):
    yield


def _log(level, msg):
    try:
        print(f"[prostudio:{level}] {msg}", file=sys.stderr)
    except Exception:
        pass


def warning(msg, *a, **k):
    _log("warning", msg)


def error(msg, *a, **k):
    _log("error", msg)


def success(msg, *a, **k):
    _log("success", msg)


def info(msg, *a, **k):
    _log("info", msg)


def progress(value=0, *a, **k):
    return _Progress()


def spinner(text="", *a, **k):
    return _spinner(text)


def markdown(*a, **k):
    return None


def write(*a, **k):
    return None


def caption(*a, **k):
    return None


def set_page_config(*a, **k):
    return None


def cache_data(*a, **k):
    if a and callable(a[0]):
        return a[0]
    return lambda fn: fn


def cache_resource(*a, **k):
    return cache_data(*a, **k)


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


session_state = _SessionState()
