#!/usr/bin/env python

import argparse
import os
import sys
from typing import Optional

try:
    from airium import __version__, from_html_to_airium
except ImportError:
    this_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(this_dir))
    from airium import __version__, from_html_to_airium


def entry_main(*args: str) -> None:
    opts = parse_options(args or sys.argv[1:])

    try:
        code = make_airium_code(opts.input_html)
        if code is not None:
            print(code)

    except Exception as e:
        msg = f" Translation failed.\n {type(e).__name__}: {e}"
        sys.stderr.write(msg + '\n')
        sys.exit(msg)


def make_airium_code(input_arg: str) -> Optional[str]:
    html = get_html_as_strnig(input_arg)
    if html is None:
        sys.stderr.write(f"\nUnable to get HTML from: {input_arg}\n\n")
        sys.exit(31)

    return from_html_to_airium(html)


def get_html_as_strnig(input_arg: str) -> Optional[str]:
    def from_local_file(file_path: str) -> Optional[str]:
        if os.path.isfile(file_path):
            with open(file_path, 'rt') as f:
                return f.read()

    def from_uri(uri: str) -> Optional[str]:
        try:
            import requests

        except ImportError as e:
            sys.stderr.write("\nPlease install `requests` package in order to fetch html files from web.\n")
            sys.stderr.write(f"{type(e).__name__}: {e}\n")
            return

        try:
            response = requests.get(uri, auth=('user', 'pass'))
        except IOError as e:
            sys.stderr.write(f"{type(e).__name__}: {e}\n")
            return

        if response.status_code == 200:
            ct = response.headers['content-type']
            if 'text/html' in ct:
                return response.text
            else:
                sys.stderr.write(f"Bad content type returned from {input_arg}: {ct}.")
                return

    ret = None
    for method_ in [from_local_file, from_uri]:
        try:
            ret = method_(input_arg)
        except (ValueError, TypeError, KeyError, IOError, AttributeError, TimeoutError, AssertionError):
            pass
        if ret is not None:
            return ret


def parse_options(args) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        'airium', description='Parse input files and generate output based on options given.')

    parser.add_argument(
        'input_html', metavar='URI_PATH', nargs='?',
        help='Local HTML file path or an URI')

    parser.add_argument('-v', '--version', action='version', version=f"airium {__version__}")

    return parser.parse_args(args)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(entry_main())
