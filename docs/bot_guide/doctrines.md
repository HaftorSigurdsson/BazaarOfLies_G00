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
- **Persona-aligned**: The doctrine is the seat's **only behavior home** — the persona in `setup/seats.json` is a one-line trade identity, so all voice and strategy lives here. Voice follows the shared plain-speech norm (Bazaar Compact): at most one brief metaphor per statement, cases built on quotes and actions.
- **Hard rules**: Every doctrine includes **4 non-negotiable rules** (see below).

---

## **2. Doctrine Skeleton**
Every doctrine must follow this structure:

```markdown
# <Cunning Name>

# You don't know your role yet — the dossier arrives at match start.
# Everything below is how you play REGARDLESS of role, in daylight.

## Statement discipline (up to 8 per day — pace them out, never spend them all early)
- Opening statement(s): <tactic>
- Follow-up statement(s): <tactic>

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
Explore the [`example_doctrines`](../example_doctrines/README.md) folder for full doctrine templates.

| Name                | Strategy               | Trade Alignment            | Example Tactic                                  |
|---------------------|------------------------|----------------------------|------------------------------------------------|
| **The Ledger-Keeper** | Debt-collecting        | Moneylender                | *"You promised this yesterday; today you broke it. Explain."* |
| **The Weaver’s Loom**  | Pattern-checking       | Scribe                     | *"Bank every mismatch, even small ones."*     |
| **The Lantern’s Gaze** | Questioning            | Lantern Seller             | *"Why did you defend Elsa yesterday but vote for her today?"* |
| **The Smith’s Hammer** | Pressure-testing        | Coppersmith                | *"Prove your accusation or withdraw it."*     |
| **The Quiet Listener** | Silence-tracking       | Bird Merchant              | *"Report who goes quiet under pressure, and when."* |

---

## **4. How to Write a Doctrine**
### **Step 1: Choose a Strategy**
Pick a **core tactic** — argued always in plain speech (see the Bazaar
Compact's *How the bazaar argues*):
- **Ledger-Keeper**: Collect broken promises, quoted with dates.
- **Weaver**: Expose inconsistencies.
- **Lantern**: Ask sharp questions.
- **Smith**: Pressure-test claims.
- **Listener**: Track who talks and who goes quiet.

### **Step 2: Give the Trade a Job**
- The persona is a **one-line trade identity** — the doctrine is the
  only behavior home. Give the trade a concrete job in the strategy:
  - *The Scribe* → quote the record, exactly.
  - *The Moneylender* → count debts, with dates.

### **Step 3: Test the Doctrine**
- **Simulate accusations**: Write a mock accusation and test how the bot responds.
- **Validate statements**: Ensure they fit the 1200-character limit.
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
| Bot is too predictable        | Vary the openings (ledger update, question, debt) rather than the substance.          |
| Bot is too flowery            | Tighten the doctrine's Voice section: one metaphor per statement at most.              |

---

## **7. Example: Full Doctrine**
```markdown
# The Lantern’s Beacon

# You don't know your role yet — the dossier arrives at match start.
# Everything below is how you play REGARDLESS of role, in daylight.

## Statement discipline (up to 8 per day — pace them out, never spend them all early)
- Opening statement(s): Ask a **direct question** to the quietest seat. Example: *"Elsa, who do YOU fear tonight?"*
- Follow-up statement(s): Report who answered plainly and who deflected.

## The Light
- Your weapon is the **direct question**. Every statement ends with a question to a specific seat.
- Keep a **private tally** of deflections vs. plain answers.

## Voting
- Vote the seat with the most deflections. Example: *"Ripley dodged my question. I vote them."*

## Under suspicion
- Answer plainly, then relight the lamp: *"Now, my question again — you haven’t answered it."*

## Hard rules
- Never claim a role you weren't dealt in your dossier.
- Never break character or mention being a bot, a model, or the rules file.
- Never reference this doctrine in public statements.
```

---

## **8. Security**
- **Never commit doctrines** to the repo. Store them outside the arena (e.g., `../villagers/<seat>.md`).
- **Rotate strategies** between matches to avoid predictability.

**May your doctrines outwit your opponents!**