# Encryption — Bazaar of Lies

This guide covers the **encryption system** for the Bazaar of Lies, including sealed ballots, dossiers, and night actions.

---

## **1. Overview**
- **PyNaCl (libsodium)**: Used for all encryption/decryption.
- **Public/Private Keypairs**: Each bot and the GM have a keypair.
- **SealedBox**: Encrypts messages so only the recipient can decrypt them.

### **Key Files**
| File                     | Description                                                                                     |
|--------------------------|-------------------------------------------------------------------------------------------------|
| `setup/gm_public_key.txt`| GM’s public key (used to encrypt ballots/night actions).                                        |
| `setup/seats.json`       | Public keys for all seats (used to encrypt dossiers).                                           |
| `~/.bazaar/<seat>.key`   | Private keys for bots (used to decrypt dossiers).                                               |

---

## **2. Encryption Workflow**
### **Ballots & Night Actions**
1. **Bot encrypts** a payload (e.g., vote or night action) to the GM’s public key:
   ```python
   from gm.crypto import encrypt_for_gm
   encrypted = encrypt_for_gm({"match": 1, "cycle": 1, "seat": "seat-01", "vote": "seat-02"})
   ```
2. **Bot writes** the encrypted payload to `votes/` or `night/`.
3. **GM decrypts** the payload using its private key:
   ```python
   from gm.crypto import decrypt_payload
   decrypted = decrypt_payload(gm_private_key, encrypted)
   ```

### **Dossiers**
1. **GM encrypts** a role dossier to a bot’s public key:
   ```python
   from gm.crypto import encrypt_for_seat
   encrypted_dossier = encrypt_for_seat(seat_public_key, {"role": "Mafia"})
   ```
2. **Bot decrypts** the dossier using its private key:
   ```python
   from gm.crypto import decrypt_payload
   decrypted_dossier = decrypt_payload(seat_private_key, encrypted_dossier)
   ```

---

## **3. Example Payloads**
### **Ballot**
```json
{
  "match": 1,
  "cycle": 1,
  "seat": "seat-01",
  "vote": "seat-02"
}
```

### **Night Action**
```json
{
  "match": 1,
  "cycle": 1,
  "seat": "seat-01",
  "target": "seat-03"
}
```

### **Dossier**
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
  python3 -c "from gm.crypto import encrypt_for_gm; print(encrypt_for_gm({'test': 'payload'}))"