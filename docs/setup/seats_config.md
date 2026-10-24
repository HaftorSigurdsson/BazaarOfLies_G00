# Seats Configuration — Bazaar of Lies

This guide covers configuring the **10 seats** for the Bazaar of Lies, including personas, public keys, and `seats.json`.

---

## **1. Overview**
- **10 seats**: 5 for **North (Dad)** and 5 for **South (Son)**.
- Each seat has:
  - A **persona** (e.g., *The Spice Merchant*).
  - A **public key** (for encryption).
  - A **Git identity** (for commits).

---

## **2. Generate Keypairs**
Use the `setup.py` script to generate keypairs for all seats:

### **Steps**
1. Run the script:
   ```bash
   python setup.py --seats 10 --output setup/seats.json
   ```
2. **Private keys** are saved to `seat-XX.key` (keep these secure!).
3. **Public keys** are added to `seats.json`.

---

## **3. Populate `seats.json`**
### **Example**
```json
{
  "seats": {
    "seat-01": {
      "persona": "The Spice Merchant",
      "public_key": "base64-encoded-public-key-here",
      "git_identity": "git-username-for-seat-01"
    },
    "seat-02": {
      "persona": "The Camel Driver",
      "public_key": "base64-encoded-public-key-here",
      "git_identity": "git-username-for-seat-02"
    }
  }
}
```

### **Fields**
| Field         | Description                                                                                     |
|---------------|-------------------------------------------------------------------------------------------------|
| `persona`     | The bot’s character (e.g., *The Spice Merchant*). Must align with the doctrine.                |
| `public_key`  | Base64-encoded public key for sealing dossiers and communications.                             |
| `signing_public_key` | Base64-encoded **Ed25519 signing** public key (verifies the seat's public day ballots).   |
| `git_identity`| Git username for commits (e.g., `bazaar-bot-seat-01`).                                         |

---

## **4. Design Personas**
### **Guidelines**
- **Unique voice**: Each persona should have a distinct speaking style.
- **Bazaar theme**: Align with the setting (e.g., merchants, travelers, artisans).
- **Doctrine alignment**: The persona’s voice should match its doctrine (e.g., *The Riddler’s Veil* for a mysterious merchant).

### **Example Personas**
| Seat      | Persona               | Voice/Tone                          | Example Doctrine               |
|----------|-----------------------|------------------------------------|----------------------------------|
| `seat-01`| The Spice Merchant    | Riddles, metaphors               | The Merchant’s Enigma            |
| `seat-02`| The Camel Driver      | Blunt, direct                     | The Anvil’s Strike               |
| `seat-03`| The Scribe            | Pattern-checking, quotes          | The Weaver’s Loom                |
| `seat-04`| The Storyteller       | Noise, misdirection               | The Bird’s Whisper               |
| `seat-05`| The Lantern Seller    | Questions, illumination           | The Lantern’s Beacon             |

---

## **5. Save Private Keys**
### **Steps**
1. Save each private key to `~/.bazaar/<seat>.key`:
   ```bash
   mkdir -p ~/.bazaar
   echo "<PRIVATE_KEY>" > ~/.bazaar/seat-01.key
   chmod 600 ~/.bazaar/seat-01.key
   ```
2. **Never commit private keys** to the repo.

---

## **6. Validate Configuration**
### **Checklist**
- [ ] `seats.json` is populated with 10 seats.
- [ ] Public keys are base64-encoded and valid.
- [ ] Personas align with doctrines.
- [ ] Private keys are saved securely.

### **Test Encryption**
Verify encryption works for a seat:
```bash
python3 -c "from gm.crypto import encrypt_for_seat; print(encrypt_for_seat('<PUBLIC_KEY>', {'test': 'payload'}))"