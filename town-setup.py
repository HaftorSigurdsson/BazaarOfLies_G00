#!/usr/bin/env python3
import argparse
import base64
import json
import os
from nacl.public import PrivateKey


def generate_keypair() -> tuple[str, str]:
    """Generate a keypair for a bot."""
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return (
        base64.b64encode(bytes(private_key)).decode(),
        base64.b64encode(bytes(public_key)).decode()
    )


def populate_seats_json(seats: int, output_file: str) -> None:
    """Populate seats.json with keypairs and placeholders."""
    seats_data = {"seats": {}}
    for i in range(1, seats + 1):
        private_key, public_key = generate_keypair()
        seat_id = f"seat-{i:02d}"
        seats_data["seats"][seat_id] = {
            "persona": "",
            "public_key": public_key,
            "git_identity": ""
        }
        # Save private key to a file (outside the repo)
        with open(f"{seat_id}.key", "w") as f:
            f.write(private_key)
    
    with open(output_file, "w") as f:
        json.dump(seats_data, f, indent=2)
    
    print(f"Generated {seats} keypairs and saved to {output_file}")
    print("Private keys saved to seat-XX.key files (keep these secure!)")


def main():
    parser = argparse.ArgumentParser(
        description="Bazaar of Lies — seat keypair generation "
                    "and setup/seats.json population.")
    parser.add_argument("--seats", type=int, default=10, help="Number of seats (default: 10)")
    parser.add_argument("--output", type=str, default="setup/seats.json", help="Output file for seats.json")
    args = parser.parse_args()
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    populate_seats_json(args.seats, args.output)


if __name__ == "__main__":
    main()