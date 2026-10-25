# Seats Configuration — Bazaar of Lies

This guide covers configuring the **10 seats** for the Bazaar of Lies, including personas, public keys, and `seats.json`.

---

## **1. Overview**
- **10 seats**: 5 for **North** and 5 for **South**.
- Each seat has:
  - A **persona** (e.g., *The Spice Merchant*).
  - A **name** (e.g., *Gandalf*) — the public display name, shown everywhere as `Gandalf`. The name is an **arbitrary label**: no matter which film character it evokes, that character never enters the game; merchants are called by name in all prose while machine files (ballots, dossiers, state, transcripts) keep the bare seat ID as the one true identity.
  - A **public key** (for encryption).
  - A **Git identity** (for commits).

---

## **2. Generate Keypairs**
Use the `src/town-setup.py` script to generate keypairs for all seats:

### **Steps**
1. Run the script:
   ```bash
   uv run src/town-setup.py --seats 10 --output setup/seats.json
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
      "name": "Gandalf",
      "persona": "You are The Spice Merchant. You trade in scent and season.",
      "public_key": "base64-encoded-public-key-here",
      "signing_public_key": "base64-encoded-signing-public-key-here",
      "git_identity": "git-username-for-seat-01"
    },
    "seat-02": {
      "name": "Hermione",
      "persona": "You are The Carpet Weaver. You know every thread by heart.",
      "public_key": "base64-encoded-public-key-here",
      "signing_public_key": "base64-encoded-signing-public-key-here",
      "git_identity": "git-username-for-seat-02"
    }
  }
}
```

### **Fields**
| Field         | Description                                                                                     |
|---------------|-------------------------------------------------------------------------------------------------|
| `name`        | The public display name (`Gandalf`) — how the merchant is called in all prose.                   |
| `persona`     | The seat's **one-line trade identity**: "You are The <Trade>. <grounding sentence>" (parsed by `persona_name()` for announcements and the graveyard). |
| `public_key`  | Base64-encoded public key for sealing dossiers and communications.                             |
| `signing_public_key` | Base64-encoded **Ed25519 signing** public key (verifies the seat's public day ballots).   |
| `git_identity`| Git username for commits (e.g., `bazaar-bot-seat-01`).                                         |

---

## **4. Design Personas**
### **Guidelines**
- **Identity, not behavior**: one line per seat — the trade and a
  grounding sentence. No speaking styles, no metaphor vocabulary; all
  behavior lives in the doctrine (`../villagers/<seat>.md`).
- **Bazaar theme**: a trade of the marketplace (merchant, artisan,
  keeper of records).
- **Parser note**: the first sentence must be "You are The <Trade>." —
  `gm.utils.persona_name()` greps it for announcements and the graveyard.

### **Current Personas**
| Seat | Name | Persona |
|---|---|---|
| `seat-01` | Gandalf | The Spice Merchant — trades in scent and season |
| `seat-02` | Hermione | The Carpet Weaver — knows every thread by heart |
| `seat-03` | Yoda | The Lantern Seller — knows light and shadow |
| `seat-04` | Batman | The Coppersmith — works with what is real |
| `seat-05` | Ripley | The Moneylender — keeps the bazaar's ledger |
| `seat-06` | Neo | The Perfumer — notices what others overlook |
| `seat-07` | Elsa | The Scribe — keeps the bazaar's record true |
| `seat-08` | Morpheus | The Potter — knows how vessels are tested |
| `seat-09` | Inigo | The Tea Seller — everyone has sat at their stove |
| `seat-10` | Sherlock | The Bird Merchant — their ear catches every chirp |

---

## **5. Save Private Keys**
### **Steps**
1. Save each private key to `../.bazaar/<seat>.key`:
   ```bash
   mkdir -p ../.bazaar
   echo "<PRIVATE_KEY>" > ../.bazaar/seat-01.key
   chmod 600 ../.bazaar/seat-01.key
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
