import argparse

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--k", type=int, default=50)
    args = parser.parse_args()
    print(f"[FewShots] domain={args.domain}, k={args.k} (stub)")

if __name__ == "__main__":
    main()
