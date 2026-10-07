"""Library Management System server."""


def main() -> int:
    """Run the ``lms`` command line. See ``lms.cli.main``."""
    from lms.cli import main as cli_main

    return cli_main()
