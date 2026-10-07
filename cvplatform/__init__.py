"""cvplatform — command line interface for the CV platform data engine."""

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    from cvplatform.cli import main as cli_main

    return cli_main(argv)
