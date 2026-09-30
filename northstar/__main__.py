"""Run the local Northstar demo."""

import argparse

from .server import serve


def main():
    parser = argparse.ArgumentParser(description="Northstar customer onboarding demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
