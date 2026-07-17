"""Console encoding setup - import and call before anything prints."""

import sys


def configure_utf8_console():
    """Force UTF-8 on stdout/stderr.

    Windows consoles default to a legacy codepage (e.g. cp1252) that cannot
    encode the checkmarks and emoji used throughout the status output. Without
    this, a routine progress print raises UnicodeEncodeError and takes the
    whole analysis down with it.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
