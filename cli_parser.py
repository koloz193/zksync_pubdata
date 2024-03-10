import argparse

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION]...",
        description="Parse zkSync Pubdata from L1"
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version = f"{parser.prog} version 1.0.0"
    )

    parser.add_argument("--l1rpc", type=str, required=True)
    parser.add_argument("--l2rpc", type=str, required=True)
    parser.add_argument("-b", "--batch", type=int, required=True)

    return parser