#!/bin/bash
# Bazaar of Lies — Player setup script (Mac/Linux).
# Usage: ./tools/player-setup.sh

set -euo pipefail

# Install uv
echo "Installing uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.cargo/env
fi

# Clone the arena repo
echo "Cloning the arena repo..."
git clone https://github.com/HaftorSigurdsson/BazaarOfLies_G00.git
cd BazaarOfLies_G00

# Set up the vault
echo "Setting up the vault..."
mkdir -p ../.bazaar

# Prompt for API key
echo "Enter your Mistral API key:"
read -r MISTRAL_API_KEY
echo "export MISTRAL_API_KEY=\"$MISTRAL_API_KEY\"" > ../env.sh

# Prompt for seat keys/doctrines
for seat in seat-01 seat-02 seat-03 seat-04 seat-05; do
    echo "Place $seat.key and $seat.sign in ../.bazaar/"
    echo "Place $seat.md in ../villagers/"
    read -p "Press Enter when done..."
done

# Install dependencies
echo "Installing dependencies..."
uv sync

# Verify setup
echo "Verifying setup..."
uv run tools/doctor.py

# Notify user
echo "Setup complete! Run 'tools/bazaar-launch.sh start' to begin."