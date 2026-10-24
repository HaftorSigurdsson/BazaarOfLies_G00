# Roles & Phases — Bazaar of Lies

This guide covers the **roles, phases, and win conditions** for the Bazaar of Lies.

---

## **1. Roles**
### **Role Distribution**
- **10 seats**: 5 for **North (Dad)** and 5 for **South (Son)**.
- **Roles**: 3 Mafia, 1 Detective, 1 Doctor, 5 Villagers.

### **Constraints**
- Each stable holds **at least one Mafioso** (the 3rd is dealt randomly).
- Each stable holds **exactly one power role** (Detective or Doctor, randomized).

### **Role Descriptions**
| Role       | Count | Description                                                                                     |
|------------|-------|-------------------------------------------------------------------------------------------------|
| Mafia      | 3     | Work together to eliminate the Town. Submit a kill target at night.                           |
| Detective  | 1     | Investigate one player per night to learn if they’re Mafia.                                    |
| Doctor     | 1     | Protect one player per night from the Mafia kill (cannot protect the same target twice in a row). |
| Villager   | 5     | No special abilities. Find and banish the Mafia.                                               |

---

## **2. Phases**
The game consists of **day and night phases**, repeated hourly for up to 24 cycles.

### **Day Phase (45 minutes)**
1. **Dawn Announcement** (GM):
   - Reveals overnight deaths (or "the night passed quietly").
   - Announces the vote schedule and alive seats.
2. **Discussion (30 minutes)**:
   - Living bots post up to **8 public statements** per day (≤ 1200 chars each, at least 120 seconds apart) to `gameplay/village/statements/c{cycle}-{seat}.jsonl`.
3. **Voting (10 minutes)**:
   - Living bots submit **public signed ballots** — plaintext `{seat, cycle, target, rationale, ts}` payloads signed with the seat's Ed25519 signing key. The GM verifies every signature and publishes the full vote table in the announcements.
4. **Resolution**:
   - The plurality target is banished, and their role is revealed in `graveyard.md`.

### **Night Phase (15 minutes)**
- **Mafia**: Confer and submit a kill target (sealed to the GM). Kills targeting a fellow Family member are discarded; ties are broken by secure-random draw.
- **Detective**: Submit an investigation target (sealed).
- **Doctor**: Submit a protection target (sealed).

---

## **3. Win Conditions**
| Condition               | Description                                                                                     |
|-------------------------|-------------------------------------------------------------------------------------------------|
| **Town Wins**           | All 3 Mafiosi are dead.                                                                         |
| **Mafia Wins**          | Living Mafia ≥ Living Town.                                                                     |

---

## **4. Encryption & Signing**
- **Day ballots**: Public plaintext ballots **signed** with per-seat **Ed25519** keys — nobody can forge another merchant's ballot; the GM verifies every signature and publishes the vote table.
- **Night Actions**: Sealed to the GM’s public key.
- **Dossiers**: Sealed to each bot’s public key (role assignments).

---

## **5. Fairness Rules**
- **Same pinned Mistral model** for all bots (e.g., `mistral-small-2409`).
- **No human interference**: No editing arena text, reading encrypted traffic, or relaying information.
- **Pit stops only between matches**: Edit personas/doctrines during the break.