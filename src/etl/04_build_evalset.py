import argparse

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--n", type=int, default=300)
    args = parser.parse_args()
    print(f"[EvalSet] domain={args.domain}, n={args.n} (stub)")

if __name__ == "__main__":
    main()
