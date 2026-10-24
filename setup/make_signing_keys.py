#!/usr/bin/env python3
"""One-time setup: generate Ed25519 signing keys for every seat.

Day votes are public plaintext ballots SIGNED with a per-seat signing key —
nobody can forge another merchant's ballot. This script:

  1. generates a signing keypair for each seat in setup/seats.json;
  2. writes the PRIVATE key to <vault>/<seat>.sign (outside the repo —
     git must never see it; the vault is the operator's secrets folder);
  3. records the PUBLIC key in setup/seats.json as "signing_public_key"
     (commit that change).

Refuses to overwrite existing keys. Safe to re-run.

Usage (from the arena repo root):
    python3 setup/make_signing_keys.py --vault ../.bazaar
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gm.crypto import generate_signing_keypair  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seats", default="setup/seats.json",
                    help="Path to seats.json (default setup/seats.json)")
    ap.add_argument("--vault", required=True,
                    help="Secrets folder for private keys (e.g. ../.bazaar)")
    args = ap.parse_args()

    with open(args.seats) as f:
        data = json.load(f)
    seats = data["seats"]

    os.makedirs(args.vault, exist_ok=True)
    made = 0
    for seat in sorted(seats):
        if seats[seat].get("signing_public_key"):
            print(f"{seat}: signing key already registered — skipping")
            continue
        priv_path = os.path.join(args.vault, f"{seat}.sign")
        if os.path.exists(priv_path):
            print(f"{seat}: {priv_path} exists but seats.json has no "
                  "signing_public_key — add it manually or remove the file")
            continue
        sk_b64, pk_b64 = generate_signing_keypair()
        with open(priv_path, "w") as f:
            f.write(sk_b64)
        os.chmod(priv_path, 0o600)
        seats[seat]["signing_public_key"] = pk_b64
        made += 1
        print(f"{seat}: signing keypair generated (private → {priv_path})")

    with open(args.seats, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    if made:
        print(f"\n{made} keypair(s) generated. Commit the updated {args.seats}.")
        print("NEVER commit the vault — private .sign keys must stay out of git.")
    else:
        print("\nNothing to do.")


if __name__ == "__main__":
    main()
