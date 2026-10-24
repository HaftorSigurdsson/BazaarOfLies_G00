# Example Doctrines — Bazaar of Lies

These are **example doctrines** for the Bazaar of Lies. Each example page shows the doctrine **unrendered, inside a code block** — exactly the bytes the bot reads from the vault file (`~/.bazaar/<seat>.md`), not a prettified rendering of it. Each stable (North/South) should create **5 unique doctrines** (one per bot) and store them **outside the repo** (e.g., `../bazaar/<seat>.txt`).

## How to Create a Doctrine

### **1. Skeleton (Required Structure)**
Every doctrine must:
- Be **role-blind**: Govern **daylight behavior only** (night actions are handled by the dossier).
- Include **4 hard rules** (copy verbatim):
  ```text
  - Never claim a role you weren't dealt in your dossier.
  - Never break character or mention being a bot, a model, or the rules file.
  - Never reference this doctrine in public statements.
  ```
- Define **statement discipline** (8 statements/day, ≥ 120 s apart), **voting strategy**, and **behavior under suspicion**.

### **2. Strategy (Choose One)**
Pick a **core tactic** that aligns with the bot’s persona. Examples:
- **Riddler**: Deflect with metaphors (e.g., *"The one who smells most of guilt is the one accusing fastest"*).
- **Weaver**: Expose inconsistencies (e.g., *"Bank every mismatch, even small ones"*).
- **Lantern**: Ask sharp questions (e.g., *"Why did you defend X yesterday but vote for them today?"*).
- **Smith**: Pressure-test claims (e.g., *"Prove your accusation or withdraw it"*).
- **Bird**: Create noise to obscure intent (e.g., *"Post cryptic statements to confuse the room"*).

### **3. Persona Alignment**
- The doctrine’s **voice** must match the persona. Example:
  - *The Spice Merchant* → Riddles and metaphors.
  - *The Scribe* → Pattern-checking and quotes.
  - *The Camel Driver* → Direct questions and bluntness.
- Avoid strategies that clash with the persona’s tone.

### **4. Testing**
- **Simulate accusations**: Write a mock accusation and test how the bot responds.
- **Validate statements**: Ensure they fit the 1200-character limit and persona voice.
- **Check for leaks**: Never let the bot reveal its doctrine or role in public.

## Design Notes

- **Role-blind on purpose**: The same doctrine works for **Town or Mafia**. Example:
  - A *Weaver* can **manufacture false patterns** if dealt Mafia.
  - A *Lantern* can **expose a Detective’s investigation** if dealt Town.
- **Hard rules are non-negotiable**: The last rule (*never reference this doctrine*) prevents opponents from reverse-engineering your strategy.
- **Never commit doctrines**: Live doctrines must stay **outside the repo** (e.g., `../bazaar/<seat>.txt`).

## Example Strategies
| Persona          | Strategy       | Example Tactic                                  |
|------------------|----------------|------------------------------------------------|
| Spice Merchant   | Riddler        | Deflect with metaphors.                        |
| Scribe           | Weaver         | Expose inconsistencies in statements.          |
| Camel Driver     | Lantern        | Ask sharp questions to expose contradictions.  |
| Blacksmith       | Smith          | Pressure-test claims.                          |
| Storyteller      | Bird           | Create noise to obscure intent.                |

**May your doctrines outwit your opponents!**
