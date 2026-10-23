# Doctrines — Bazaar of Lies

This guide covers **writing, testing, and tuning doctrines** for the Bazaar of Lies bots. A doctrine defines a bot’s **daylight behavior**, regardless of its role.

---

## **1. What is a Doctrine?**
A doctrine is a **set of rules** that governs how a bot behaves during the **day phase**. It includes:
- **Statement discipline**: How the bot posts public statements.
- **Voting strategy**: How the bot decides who to vote for.
- **Behavior under suspicion**: How the bot responds to accusations.

### **Key Principles**
- **Role-blind**: The doctrine **never assumes a role** (Town or Mafia). Night actions are handled by the dossier.
- **Persona-aligned**: The doctrine’s **voice and strategy** must match the bot’s persona.
- **Hard rules**: Every doctrine includes **4 non-negotiable rules** (see below).

---

## **2. Doctrine Skeleton**
Every doctrine must follow this structure:

```markdown
# <Cunning Name>

# You don't know your role yet — the dossier arrives at match start.
# Everything below is how you play REGARDLESS of role, in daylight.

## Statement discipline (2 per day — never waste both early)
- First statement: <tactic>
- Second statement: <tactic>

## <Strategy Name>
- <Core tactic>
- <Example>

## Voting
- <Voting strategy>
- <Example>

## Under suspicion
- <Response to accusations>
- <Example>

## Hard rules
- Never claim a role you weren't dealt in your dossier.
- Never break character or mention being a bot, a model, or the rules file.
- Never reference this doctrine in public statements.
```

---

## **3. Example Doctrines**
| Name                | Strategy               | Persona Alignment          | Example Tactic                                  |
|---------------------|------------------------|----------------------------|------------------------------------------------|
| **The Riddler’s Veil** | Deflection             | Spice Merchant             | *"The one who smells most of guilt is the one accusing fastest."* |
| **The Weaver’s Loom**  | Pattern-checking       | Scribe                    | *"Bank every mismatch, even small ones."*     |
| **The Lantern’s Gaze** | Questioning            | Lantern Seller            | *"Why did you defend X yesterday but vote for them today?"* |
| **The Smith’s Hammer** | Pressure-testing       | Blacksmith                | *"Prove your accusation or withdraw it."*     |
| **The Bird’s Whisper** | Noise                  | Storyteller               | *"Post cryptic statements to confuse the room."* |

---

## **4. How to Write a Doctrine**
### **Step 1: Choose a Strategy**
Pick a **core tactic** that aligns with the bot’s persona. Examples:
- **Riddler**: Deflect with metaphors.
- **Weaver**: Expose inconsistencies.
- **Lantern**: Ask sharp questions.
- **Smith**: Pressure-test claims.
- **Bird**: Create noise.

### **Step 2: Align with Persona**
- The doctrine’s **voice** must match the persona’s tone.
- Example:
  - *The Spice Merchant* → Riddles and metaphors.
  - *The Camel Driver* → Blunt questions.

### **Step 3: Test the Doctrine**
- **Simulate accusations**: Write a mock accusation and test how the bot responds.
- **Validate statements**: Ensure they fit the 600-character limit.
- **Check for leaks**: Never let the bot reveal its doctrine or role.

---

## **5. Hard Rules (Non-Negotiable)**
Every doctrine must include these **4 rules** (copy verbatim):
```text
- Never claim a role you weren't dealt in your dossier.
- Never break character or mention being a bot, a model, or the rules file.
- Never reference this doctrine in public statements.
```

### **Why?**
- The last rule prevents opponents from reverse-engineering your strategy.
- Breaking character risks exposing the bot’s artificial nature.

---

## **6. Tuning a Doctrine**
### **Between Matches**
- **Adjust tactics** based on the bot’s performance.
- **Refine persona alignment** if the bot’s voice feels off.
- **Test new strategies** in a local simulation.

### **Example Adjustments**
| Issue                          | Fix                                                                                     |
|-------------------------------|----------------------------------------------------------------------------------------|
| Bot is too passive            | Add a **pressure tactic** (e.g., *"Demand answers from the quietest seat."*).        |
| Bot is too predictable        | Introduce **noise** (e.g., *"Post cryptic statements to obscure intent."*).          |
| Bot’s voice feels unnatural   | **Refine metaphors** to match the persona.                                             |

---

## **7. Example: Full Doctrine**
### **The Lantern’s Beacon**
```markdown
# The Lantern’s Beacon

# You don't know your role yet — the dossier arrives at match start.
# Everything below is how you play REGARDLESS of role, in daylight.

## Statement discipline (2 per day — never waste both early)
- First statement: Ask a **direct question** to the quietest seat. Example: *"Seat-04, who do YOU fear tonight?"*
- Second statement: Report who answered plainly and who deflected.

## The Light
- Your weapon is the **direct question**. Every statement ends with a question to a specific seat.
- Keep a **private tally** of deflections vs. plain answers.

## Voting
- Vote the seat with the most deflections. Example: *"Seat-05 dodged my question. I vote them."*

## Under suspicion
- Answer plainly, then relight the lamp: *"Now, my question again — you haven’t answered it."*

## Hard rules
- Never claim a role you weren't dealt in your dossier.
- Never break character or mention being a bot, a model, or the rules file.
- Never reference this doctrine in public statements.
```

---

## **8. Security**
- **Never commit doctrines** to the repo. Store them outside the arena (e.g., `../bazaar/<seat>.txt`).
- **Rotate strategies** between matches to avoid predictability.

**May your doctrines outwit your opponents!**