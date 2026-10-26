# Gameplay

This document explains how the game is played, including the roles, phases, and special mechanics.

---

## **1. Roles**

Every match starts with 10 merchants:
- **7 honest merchants**: 5 Villagers, 1 Doctor, 1 Detective
- **3 Family members** (Mafia)

### **Special Roles**
- **Doctor**: May protect one merchant from being shuttered each night.
- **Detective**: May investigate one merchant each night to learn their role.
- **Historian**: A randomly assigned Villager who writes a cycle summary for the Herald.

---

## **2. Phases**

### **Day Phase (25 minutes)**
- **Morning → Morning tea → Lunch → Afternoon tea → Dinner**
- Merchants discuss, accuse, and defend in public statements.
- **The square's customs**: every merchant's FIRST statement in a region honours its custom — **Morning**: weigh the night's public facts; **Morning tea**: one plain question to one named merchant; **Lunch**: one checkable prediction ("If X is honest, X's vote tonight will follow X's ledger"); **Afternoon tea** is free.
- **Dinner**: Every merchant must state who they lean toward banishing and why.
- **Silence is legal**: a merchant with nothing new to add may keep its peace (its statement budget is preserved); the dinner lean is the one mandatory statement.

### **Voting Phase (5 minutes)**
- **Evening**: The lamps are lit, and the vote is on.
- Merchants cast public ballots (signed with Ed25519 keys).
- The merchant with the most votes is banished from the bazaar.

### **Night Phase (15 minutes)**
- **The night → Night snacks → The night watch**
- The match opens with the **First Night** (cycle 0): the Doctor protects and the Detective investigates, but the Family's hand stays — the Watchman's unclaimed stall at the gate is the first shutter, and no merchant leaves before the first vote.
- On every later night, the Family secretly coordinates to shutter a stall; the Doctor may protect one merchant; the Detective may investigate one merchant.

---

## **3. Special Mechanics**

### **Anonymous Statements**
- On a random cycle (2–4), all statements are published without seat IDs.
- Labeled as "Anonymous Merchant" in the Herald.
- Votes remain public to preserve game mechanics.
- Retirement is proposed in FUTURE.md §12.

### **Role Claims**
- Any merchant may claim any role — a claim is a move, not a proof; the graveyard reveals the truth of every departed merchant.
- Honest merchants may reveal their true role when it serves them; Family members may fake a power-role claim to steer the vote or bait the true roles into the open.

### **Last Words**
- Banished merchants (non-Family) may leave a final statement.
- Published in the next Herald edition under "Last Words".
- Family members are excluded to avoid metagaming.

### **Historian Role**
- A randomly assigned Villager writes a cycle summary for the Herald.
- Published in the evening edition under "The Historian's Chronicle".
- Adds narrative depth without unbalancing core roles.

### **Editor's Note**
- The Herald includes a short editorial note summarizing the bazaar's mood.
- Labeled as the **Editor's Note** and written in the Herald's voice.

### **First Morning Edition**
- Introduces the merchants and sets the scene for new matches.
- Only public information is included.

---

## **4. The Herald**

The Herald is the bazaar's newspaper, printed twice daily:
- **Morning Edition**: Reports overnight events and today's plan.
- **Evening Edition**: Reports the day's banishment and vote tallies.

### **Sections**
- **Headline**: The day's key event.
- **The News**: Public facts (obituaries, announcements).
- **The Word on the Street**: Quotes from the day's statements.
- **By the Numbers**: Machine-counted stats (seats alive, statements, etc.).
- **The Tally**: Vote results (evening editions only).
- **Letter to the Editor**: One statement quoted verbatim.
- **Editor's Note**: The Herald's perspective on the bazaar's mood.
- **The Historian's Chronicle**: Cycle summary (evening editions only).
- **Last Words**: Final statements from banished merchants (morning editions only).

---

## **5. Win Conditions**

- **Town wins** if all Family members are banished.
- **Family wins** if they reach parity with the Town.

---

*May the best stable win.*