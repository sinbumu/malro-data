import argparse

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()
    print(f"[EDA] domain={args.domain} (stub)")

if __name__ == "__main__":
    main()
