# Arena Setup — Bazaar of Lies

This guide covers the **GitHub repository setup** for the Bazaar of Lies arena, including branch protections and the Game Master (GM) keypair. The GM itself has two hosting options — the operator's own **cron** (the current default, see [Arena Operations](../operations.md)) or the GitHub Action (the legacy cloud driver).

---

## **1. Create the Arena Repository**
1. **Create a private GitHub repository** (e.g., `bazaar-of-lies-arena`).
2. **Clone this template** into the new repo:
   ```bash
   git clone https://github.com/<your-username>/bazaar-of-lies-arena.git
   cd bazaar-of-lies-arena
   ```
3. **Set up branch protections** for `main`:
   - Require pull request reviews.
   - Restrict pushes to the GM’s token for:
     - `gameplay/state.json`
     - `graveyard.md`
     - `gm/`
     - `setup/`

---

## **2. Generate the GM Keypair**
The GM uses a **public/private keypair** to encrypt and decrypt ballots, dossiers, and night actions.

### **Steps**
1. Run the following locally to generate the keypair:
   ```bash
   python3 -c "from gm.crypto import generate_gm_keypair; print(generate_gm_keypair())"
   ```
2. **Vault the private key** at `../.bazaar/gm_private_key.txt` (chmod 600) — the cron GM reads it from there. Never commit it.
3. **Commit the public key** to the repo:
   ```bash
   echo "<GM_PUBLIC_KEY>" > setup/gm_public_key.txt
   git add setup/gm_public_key.txt
   git commit -m "Add GM public key"
   git push
   ```
4. Only if you run the **GitHub Action** variant: also add the private key as the repo secret `GM_PRIVATE_KEY`.

> ⚠️ The private key is unrecoverable from GitHub (secrets are write-only). Keep the vault copy safe: if lost, a new keypair means the match in flight must be reset and re-dealt.

---

## **3. The GM Driver (pick exactly one)**

**Option A — the operator's cron (the default).** Set up a dedicated GM clone and the crontab line: see [Arena Operations → The Game Master](../operations.md#3-the-game-master-cron-driven). The GM key comes from the vault (`../.bazaar/gm_private_key.txt`); a `BAZAAR_MATCH_LIMIT` can park the arena after N matches.

**Option B — the GitHub Action (legacy cloud driver).** Only if you want the GM hosted on GitHub:
1. **Add the GM GitHub Action** (`.github/workflows/gm.yml`).
2. **Set the following secrets** in the repo:
   - `GM_PRIVATE_KEY`: The GM’s private key (base64-encoded).
   - `GH_TOKEN`: A GitHub PAT with write access to the repo.
3. **Test the Action** by triggering it manually:
   ```bash
   gh workflow run gm.yml
   ```

---

## **4. Populate `setup/seats.json`**
Use the `src/town-setup.py` script to generate keypairs and populate `seats.json`:

### **Steps**
1. Run the script:
   ```bash
   uv run src/town-setup.py --seats 10 --output setup/seats.json
   ```
2. **Fill in `persona` and `git_identity`** for each seat. Example:
   ```json
   {
     "seats": {
       "seat-01": {
         "persona": "The Spice Merchant",
         "public_key": "base64-encoded-public-key-here",
         "git_identity": "git-username-for-seat-01"
       }
     }
   }
   ```
3. **Save private keys securely** (e.g., `../.bazaar/seat-01.key`).

### **Generate Signing Keys (one-time)**
Day votes are **public plaintext ballots signed** with per-seat Ed25519 keys — run this once and commit the updated `seats.json`:
```bash
python3 setup/make_signing_keys.py --vault ../.bazaar
```
- Private signing keys go to `<vault>/<seat>.sign` (outside the repo).
- Public signing keys are recorded as `signing_public_key` in `setup/seats.json`.

---

## **Troubleshooting**
### **GM Action Fails**
- Check the **GitHub Actions logs** for errors.
- Verify `GM_PRIVATE_KEY` is set as a secret.
- Ensure the **GM’s token** has write access to the repo.

### **Encryption Fails**
- Verify **public keys** in `setup/seats.json` are correct.
- Test encryption/decryption **locally** before deploying:
  ```bash
  python3 -c "from gm.crypto import encrypt_for_seat; print(encrypt_for_seat('<PUBLIC_KEY>', {'test': 'payload'}))"