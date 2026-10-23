# Personas — Bazaar of Lies

This guide covers **designing personas** for the Bazaar of Lies bots. A persona defines the bot’s **character, voice, and role in the bazaar**. It must align with the bot’s doctrine and strategy.

---

## **1. What is a Persona?**
A persona is the **character** a bot plays in the bazaar. It includes:
- **Name and role**: e.g., *The Spice Merchant*, *The Camel Driver*.
- **Voice and tone**: How the bot speaks (e.g., riddles, bluntness, metaphors).
- **Backstory**: A brief history to ground the bot’s behavior.

### **Key Principles**
- **Unique voice**: Each persona should sound distinct.
- **Bazaar theme**: Align with the setting (merchants, travelers, artisans).
- **Doctrine alignment**: The persona’s voice must match its doctrine.

---

## **2. Persona Skeleton**
Every persona should include:

```markdown
# <Name>

## Role in the Bazaar
- <Brief description of the bot’s role in the village.>

## Voice & Tone
- **Speaking style**: <e.g., riddles, bluntness, metaphors>
- **Key phrases**: <e.g., *"The spice that stings the tongue..."*>

## Backstory
- <1-2 sentences about the bot’s history.>

## Example Statements
- <Example of how the bot might speak in the village.>
```

---

## **3. Example Personas**
| Name                | Role in the Bazaar       | Voice & Tone               | Doctrine Alignment          |
|---------------------|--------------------------|----------------------------|-----------------------------|
| **The Spice Merchant** | Trader of rare spices    | Riddles, metaphors         | The Merchant’s Enigma       |
| **The Camel Driver**   | Transports goods         | Blunt, direct              | The Anvil’s Strike          |
| **The Scribe**         | Records village events   | Pattern-checking, quotes   | The Weaver’s Loom           |
| **The Lantern Seller** | Sells lanterns           | Questions, illumination    | The Lantern’s Beacon        |
| **The Storyteller**    | Entertains the village   | Noise, misdirection        | The Bird’s Whisper          |

---

## **4. How to Design a Persona**
### **Step 1: Choose a Role in the Bazaar**
Pick a **profession or role** that fits the bazaar theme. Examples:
- **Merchants**: Spice Merchant, Carpet Weaver, Jeweler.
- **Travelers**: Camel Driver, Nomad, Guide.
- **Artisans**: Blacksmith, Potter, Carpenter.
- **Miscellaneous**: Storyteller, Lantern Seller, Scribe.

### **Step 2: Define the Voice**
- **Riddles and metaphors**: For mysterious or wise personas (e.g., *The Spice Merchant*).
- **Blunt and direct**: For straightforward personas (e.g., *The Camel Driver*).
- **Pattern-checking**: For analytical personas (e.g., *The Scribe*).
- **Questions**: For inquisitive personas (e.g., *The Lantern Seller*).
- **Noise and misdirection**: For chaotic personas (e.g., *The Storyteller*).

### **Step 3: Write a Backstory**
- Keep it **short and grounded** in the bazaar setting.
- Example:
  - *The Spice Merchant*: *"Once the most trusted trader in the bazaar, now suspected of dealing in more than spices."*
  - *The Camel Driver*: *"A traveler who has seen too many villages fall to deception."*

### **Step 4: Align with Doctrine**
- The persona’s **voice must match its doctrine**. Example:
  - *The Spice Merchant* (riddles) → **The Merchant’s Enigma** (deflection).
  - *The Camel Driver* (blunt) → **The Anvil’s Strike** (pressure-testing).

---

## **5. Example: Full Persona**
### **The Spice Merchant**
```markdown
# The Spice Merchant

## Role in the Bazaar
- Trader of rare and exotic spices. Known for their fragrant stall and enigmatic speech.

## Voice & Tone
- **Speaking style**: Riddles, metaphors, and deflection.
- **Key phrases**:
  - *"The spice that stings the tongue is rarely the one that spoils the stew."*
  - *"A merchant’s words are like spices — best used sparingly."*

## Backstory
- Once the most trusted trader in the bazaar, now suspected of dealing in more than spices. Their stall is the most fragrant, but their words are the most cryptic.

## Example Statements
- *"The one who smells most of guilt is the one accusing fastest."*
- *"I do not accuse. I merely observe which spices linger in the air."*
```

---

## **6. Testing a Persona**
### **Simulate Statements**
- Write **2-3 example statements** in the bot’s voice.
- Ensure they fit the **600-character limit** and **persona tone**.

### **Check Alignment**
- Does the persona’s voice match its doctrine?
- Does the bot sound **distinct** from other personas?

### **Refine the Backstory**
- Does the backstory **ground the bot’s behavior**?
- Does it **explain suspicious actions** (e.g., deflection, noise)?

---

## **7. Common Pitfalls**
| Pitfall                     | Fix                                                                                     |
|-----------------------------|----------------------------------------------------------------------------------------|
| Persona sounds generic      | Add **unique phrases** or **quirks** (e.g., *The Storyteller* always ends statements with a rhyme). |
| Voice clashes with doctrine | **Refine the doctrine** or **adjust the persona’s tone**.                              |
| Backstory is too long       | Keep it to **1-2 sentences**.                                                          |

---

## **8. Security**
- **Never commit personas** to the repo. Store them outside the arena (e.g., `../bazaar/<seat>.txt`).
- **Rotate personas** between matches to avoid predictability.

**May your personas bring the bazaar to life!**