# Encryption — Bazaar of Lies

This guide covers the **encryption system** for the Bazaar of Lies, including signed public ballots, dossiers, and night actions.

---

## **1. Overview**
- **PyNaCl (libsodium)**: Used for all sealing/sealing-open (`SealedBox`) and **Ed25519 signing**.
- **Public/Private Keypairs**: Each bot and the GM have a sealing keypair; each seat also has an **Ed25519 signing keypair** for public ballots.
- **SealedBox**: Seals messages so only the recipient can open them (night actions, dossiers).
- **Ed25519 Signatures**: Prove authorship of **public day ballots** without hiding them.

### **Key Files**
| File                     | Description                                                                                     |
|--------------------------|-------------------------------------------------------------------------------------------------|
| `setup/gm_public_key.txt`| GM’s public key (used to seal night actions).                                                    |
| `setup/seats.json`       | Public sealing keys + signing public keys for all seats.                                         |
| `../.bazaar/<seat>.key`   | Seat's private sealing key (opens dossiers).                                                      |
| `../.bazaar/<seat>.sign`  | Seat's private **signing** key (signs public ballots).                                           |

---

## **2. Encryption & Signing Workflow**
### **Ballots (public, signed)**
Day votes are **public plaintext ballots signed** with a per-seat Ed25519 signing key — nobody can forge another merchant's ballot:

1. **Bot signs** the ballot payload:
   ```python
   from gm.crypto import sign_payload
   payload = {"seat": "seat-01", "cycle": 1, "epoch": "a1b2c3d4",
              "target": "seat-02", "rationale": "deflected twice", "ts": "..."}
   signature = sign_payload(seat_signing_key, payload)
   ```
2. **Bot writes** the signed payload to `gameplay/votes/`.
3. **GM verifies** the signature and the epoch before counting:
   ```python
   from gm.crypto import verify_payload
   ok = verify_payload(seat_signing_public_key, payload, signature)
   ```

### **The Night Chat Channel (symmetric, fixed-size)**
The in-repo council channel uses **symmetric sealing** (`SecretBox`) on the **`night_channel_key`** every dossier carries (the three Family members share one key; the rest hold random unusable ones — the shape is uniform so no dossier reveals a role by its fields).

1. **Pad**: the payload is JSON-padded to a fixed size before sealing, so every ciphertext is byte-identical in length whatever the message.
2. **Seal** (`gm.crypto.seal_chat`): only key-holders can read; wrong keys fail authentication cleanly (`open_chat` returns `None`).
3. **Decoys**: the GM mints each non-Family seat's chat files with the *family key itself*, so every file in the channel opens under it — a snoop holding the key sees ten council voices and cannot tell which are the Family.

```python
from gm.crypto import seal_chat, open_chat
blob = seal_chat(family_key, {"kind": "talk", "cycle": 1, "watch": 1,
                              "text": "the ledger is thin", "target": "seat-04"})
msg = open_chat(family_key, blob)          # → the payload, or None for a wrong key
```

### **Night Actions (sealed)**
1. **Bot seals** a night payload (shutter / investigate / protect) to the GM’s public key:
   ```python
   from gm.crypto import encrypt_for_seat
   encrypted = encrypt_for_seat(gm_public_key_b64,
                                 {"match": 1, "cycle": 1, "epoch": "...",
                                  "seat": "seat-01", "role": "Mafia", "target": "seat-03", "ts": "..."})
   ```
2. **Bot writes** the sealed payload to `gameplay/night/`.
3. **GM opens** the payload using its private key:
   ```python
   from gm.crypto import decrypt_payload
   decrypted = decrypt_payload(gm_private_key, encrypted)
   ```

### **Dossiers (sealed to each seat)**
1. **GM seals** a role dossier to a bot’s public key:
   ```python
   from gm.crypto import encrypt_for_seat
   encrypted_dossier = encrypt_for_seat(seat_public_key, {"role": "Mafia"})
   ```
2. **Bot opens** the dossier using its private key:
   ```python
   from gm.crypto import decrypt_payload
   decrypted_dossier = decrypt_payload(seat_private_key, encrypted_dossier)
   ```

---

## **3. Example Payloads**
### **Ballot (public + signed)**
```json
{
  "seat": "seat-01",
  "cycle": 1,
  "epoch": "a1b2c3d4",
  "target": "seat-02",
  "rationale": "The river bends around every question.",
  "ts": "2026-10-24T20:55:00Z"
}
```

### **Night Action (sealed)**
```json
{
  "match": 1,
  "cycle": 1,
  "epoch": "a1b2c3d4",
  "seat": "seat-01",
  "role": "Mafia",
  "target": "seat-03"
}
```

### **Dossier (sealed to the seat)**
```json
{
  "role": "Mafia",
  "team": "North"
}
```

---

## **4. Security**
- **Never commit private keys** to the repo.
- **Rotate keys** between matches if compromised.
- **Validate public keys** before encryption:
  ```python
  from gm.crypto import validate_public_key
  is_valid = validate_public_key(public_key_b64)
  ```

---

## **5. Troubleshooting**
### **Encryption Fails**
- Verify the **public key** is base64-encoded and valid.
- Test encryption locally:
  ```bash
  python3 -c "from gm.crypto import encrypt_for_seat; print(encrypt_for_seat(open('setup/gm_public_key.txt').read(), {'test': 'payload'}))"