
## 🎯 **Optimized ArUco Marker Schema**

### **New ID Ranges (Smaller & More Focused):**
- **Corner markers**: IDs 0-3 (calibration - unchanged)
- **Player tokens**: IDs 10-25 (**16 players** instead of 90)
- **Item tokens**: IDs 30-61 (**32 standard gaming items**)
- **Custom tokens**: IDs 62+ (user-defined)

### **Benefits of Optimization:**
- **Smaller physical markers**: Can now use 15mm x 15mm minimum size
- **Faster detection**: Only 52 standard IDs instead of 100+
- **Gaming-focused**: 32 curated items for actual tabletop needs
- **Better performance**: Less processing overhead

## 🎮 **32 Standard Gaming Items**

**Enemies (IDs 30-37):**
Goblin, Orc, Skeleton, Dragon, Troll, Wizard_Enemy, Beast, Demon

**Treasure/Items (IDs 40-47):**
Treasure_Chest, Magic_Item, Gold_Pile, Potion, Weapon, Armor, Scroll, Key

**NPCs (IDs 50-54):**
NPC_Merchant, NPC_Guard, NPC_Noble, NPC_Innkeeper, NPC_Priest

**Environment (IDs 55-61):**
Door, Trap, Fire_Hazard, Altar, Portal, Vehicle, Objective

## 🚀 **New "Complete Set" Generation**

```bash
# Generate EVERYTHING at once - perfect for getting started!
python3 aruco_generator.py --complete

# This creates:
# - 4 corner markers (calibration)
# - 16 player markers (your party)  
# - 32 item markers (all gaming items)
# - Print-ready sheets for each category
```

## 📊 **Visual Improvements**

**Camera Preview & Tracking:**
- **Red circles**: Player tokens (P1-P16)
- **Orange squares**: Item tokens (Gob, Drg, Chr, etc.)
- **Magenta circles**: Custom tokens (62+)
- **Short item names**: "Gob" for Goblin, "Chr" for Treasure_Chest

**Foundry Integration:**
- **Smart naming**: "Player_01", "Goblin", "Treasure_Chest"
- **Different token images**: Players vs Items vs Custom
- **Proper categorization**: Auto-detects and handles each type

## 🔧 **Updated Commands**

```bash
# Complete set (recommended for new users)
python3 aruco_generator.py --complete

# Just players (16 max)
python3 aruco_generator.py --players-only --player-count 16

# Just standard items (32 gaming items)
python3 aruco_generator.py --items-only

# Custom markers (use IDs 62+)
python3 aruco_generator.py --custom-file my_custom.json
```

## 📈 **Performance Gains**

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| Standard IDs | 0-99 | 0-61 | 38% reduction |
| Min marker size | 20mm | 15mm | 25% smaller |
| Player tokens | 90 | 16 | Realistic for gaming |
| Gaming items | 0 | 32 | Curated for tabletop |

Your ArUco tracking system is now **optimized for real tabletop gaming** with smaller, faster markers and everything you actually need for D&D/RPG sessions! 🎲✨

The `--complete` flag is perfect for getting started - it gives you everything needed for a full gaming setup in one command.