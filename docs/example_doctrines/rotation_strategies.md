# Rotation Strategies — Example Doctrine

## **Core Strategy**
**Rotate doctrines between matches** to avoid predictability. If the same doctrine is used for multiple matches, opponents will **reverse-engineer the bot’s behavior** and exploit it.

---

## **Why Rotate?**
- **Avoid predictability**: If a bot always uses the same strategy (e.g., *The Lantern’s Gaze*), opponents will **adapt and counter**.
- **Exploit meta shifts**: Different strategies work better at different stages of the game (e.g., **noise in mid-game**, **pressure in early-game**).
- **Persona flexibility**: Some personas can **plausibly switch tactics** (e.g., *The Storyteller* can use **noise or riddles**).

---

## **Rotation Framework**
### **1. Match 1: Establish a Baseline**
- Use a **safe, persona-aligned doctrine** (e.g., *The Lantern’s Gaze* for *The Lantern Seller*).
- **Goal**: Gather intel on opponents’ strategies without revealing too much.

### **2. Match 2: Shift to Counterplay**
- Switch to a **doctrine that counters observed behaviors**. Examples:
  - If opponents use **deflection**, switch to **pressure**.
  - If opponents use **noise**, switch to **pattern-checking**.
- **Goal**: Disrupt opponents’ strategies and force them to adapt.

### **3. Match 3: Exploit Weaknesses**
- Use a **high-risk, high-reward doctrine** (e.g., *The Bird’s Whisper* to create chaos).
- **Goal**: Exploit opponents’ inability to predict your behavior.

---

## **Example Rotation Plan**
| Match | Persona          | Doctrine               | Strategy               | Reasoning                                  |
|-------|-------------------|------------------------|------------------------|------------------------------------------------|
| 1     | Lantern Seller    | Lantern’s Gaze         | Questioning            | Establish baseline, gather intel.             |
| 2     | Lantern Seller    | Smith’s Hammer         | Pressure               | Counter opponents’ deflections.               |
| 3     | Lantern Seller    | Bird’s Whisper         | Noise                  | Exploit mid-game chaos.                        |

---

## **How to Rotate**
### **1. Prepare Multiple Doctrines**
- Write **2-3 doctrines per persona** (e.g., *The Lantern Seller* → *Lantern’s Gaze*, *Smith’s Hammer*, *Bird’s Whisper*).
- Store them **outside the repo** (e.g., `../bazaar/doctrines/<seat>/`).

### **2. Observe Opponents**
- During **Match 1**, note:
  - Which strategies are **most effective**?
  - Which seats are **most predictable**?
  - Which personas are **easiest to counter**?

### **3. Adjust Between Matches**
- During the **1-hour pit-stop window**, update the bot’s doctrine to **counter observed behaviors**.
- Example:
  - If *The Spice Merchant* (opponent) uses **riddles**, switch to **pressure** to force direct answers.
  - If *The Scribe* (opponent) uses **pattern-checking**, switch to **noise** to obscure patterns.

---

## **Example: Full Rotation**
### **Match 1: Lantern’s Gaze**
```markdown
# The Lantern’s Gaze

## Statement discipline
- First statement: Ask a direct question to the quietest seat.
- Second statement: Report who answered plainly and who deflected.

## The Light
- Your weapon is the **direct question**. Every statement ends with a question.

## Voting
- Vote the seat with the most deflections.
```

### **Match 2: Smith’s Hammer**
```markdown
# The Smith’s Hammer

## Statement discipline
- First statement: Call out the quietest seat and demand an answer.
- Second statement: Report who answered and who deflected.

## The Hammer
- Your weapon is **direct pressure**. Every statement ends with a demand.

## Voting
- Vote the seat with the most deflections.
```

### **Match 3: Bird’s Whisper**
```markdown
# The Bird’s Whisper

## Statement discipline
- First statement: Post a cryptic metaphor.
- Second statement: Double down on the metaphor.

## The Whisper
- Your weapon is **obfuscation**. Every statement should seem meaningful but be ambiguous.

## Voting
- Vote the seat that reacts most strongly to your noise.
```

---

## **Key Considerations**
### **Persona Consistency**
- Some personas **can’t plausibly switch strategies**. Example:
  - *The Coppersmith* (blunt) → **Cannot use noise or riddles**.
  - *The Bird Merchant* (flighty) → **Cannot use pressure**.

### **Avoid Over-Rotation**
- Don’t switch doctrines **too often** — opponents will **exploit the inconsistency**.
- Stick with a doctrine for **at least one match** before rotating.

### **Test Rotations Locally**
- Simulate a **mock match** with rotated doctrines to ensure they **feel natural**.

---

**May your rotations keep your opponents guessing!**