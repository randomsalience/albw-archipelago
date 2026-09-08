import re
from albwrandomizer import GetItem

def match_external_item(name: str, game: str) -> GetItem:
    regex = re.compile("[A-Za-z0-9]+")
    keywords = regex.findall(name.lower())

    def matches(*args) -> bool:
        for arg in args:
            if arg in keywords:
                return True
        return False

    default = GetItem.MessageBottle

    if game in ["Autopelago", "Lingo", "Lingo 2"]:
        return default

    if matches("key", "keys", "keycard", "key1", "key2", "key3", "lockpick"):
        if matches("big", "boss", "nightmare", "major", "bedroom", "shard") or game in ["Super Mario 64", "Donkey Kong 64"]:
            return GetItem.KeyBoss
        if name in ["Angler Key", "Bird Key", "Face Key", "Slime Key", "Tail Key"]:
            return GetItem.KeyBoss
        if name != "Twin Pyramid Key":
            return GetItem.KeySmall
    if matches("badge", "emblem", "medal"):
        return GetItem.BadgeBee
    if matches("compass"):
        return GetItem.Compass
    if matches("scroll", "map", "chart", "recipe", "book", "cookbook", "notebook", "spellbook", "tome", \
            "page", "pages", "card", "newspaper", "sketch", "memo", "database", "lore", "report", "blueprint", \
            "deed", "journal", "ticket", "contract", "permit"):
        if game != "Super Mario Land 2":
            return GetItem.GanbariPowerUp
    if matches("sword", "dagger", "knife", "blade", "cut", "slash", "upslash", "leftslash", "rightslash", \
            "axe", "pickaxe", "pick") or "Dream Breaker" in name \
            or name in ["Broom", "Extend", "Widen", "Progressive Melee", "Umbrella"]:
        return GetItem.ItemSwordLv2
    if matches("shield"):
        return GetItem.ItemShield
    if matches("mail", "tunic", "armor", "suit") and "Pokemon" not in game:
        if matches("red"):
            return GetItem.ClothesRed
        return GetItem.ClothesBlue
    if matches("flippers", "swim", "surf", "diving"):
        return GetItem.ItemMizukaki
    if matches("boots", "shoe", "shoes", "greaves", "run", "talaria", "kick", "jump", "bounce", "stomp", "wingboots"):
        return GetItem.DashBoots
    if matches("glove", "gloves", "mitts", "strength", "gauntlet", "gauntlets", "claw", "claws", "nails", \
            "hand", "knuckle", "carry", "climb", "climbing", "cling") or "Power Bracelet" in name:
        return GetItem.PowerGlove
    if matches("bell", "fly", "teleport", "beacon", "flute", "ocarina", "recorder", "dath", "checkpoint", "stag", "special1"):
        return GetItem.ItemBell
    if name == "Twin Pyramid Key" or "Nexus Gate" in name:
        return GetItem.ItemBell
    if matches("bracelet", "ring", "bangle", "armlet"):
        return GetItem.RingRental
    if matches("rod", "arrow", "arrows"):
        if matches("fire", "magic", "magical"):
            return GetItem.ItemFireRod
        if matches("ice"):
            return GetItem.ItemIceRod
        if matches("light"):
            return GetItem.ItemBowLight
    if "Plasma Beam" in name or name in ["Flamethrower", "Atomic Fire"]:
        return GetItem.ItemFireRod
    if "Ice Beam" in name or name in ["Ice Spreader", "Ice Spreadshot", "Progressive Ice Ring"]:
        return GetItem.ItemIceRod
    if matches("bomb", "bombs", "bombchu"):
        if matches("bag", "morph") or name == "Power Bomb (Main)" or game == "The Wind Waker":
            return GetItem.ItemBomb
        if name == "Bomb" and game in ["Super Metroid", "Metroid Zero Mission"]:
            return GetItem.ItemBomb
    if name in ["Progressive Bomb", "Crash Bomber", "Progressive Dynamite"]:
        return GetItem.ItemBomb
    if matches("hookshot", "clawshot", "grapple", "grappling", "lariat"):
        return GetItem.ItemHookShot
    if matches("boomerang"):
        return GetItem.ItemBoomerang
    if matches("hammer", "hammers", "smash"):
        return GetItem.ItemHammer
    if matches("bow") and game != "Paper Mario":
        return GetItem.ItemBow
    if matches("bottle", "bucket"):
        return GetItem.ItemBottle
    if matches("lamp", "lantern", "flash", "torches", "candle", "match", "matches", "matchbox") or name == "Ascendant Light":
        return GetItem.ItemKandelaar
    if matches("net"):
        return GetItem.ItemInsectNet
    if matches("heart"):
        if matches("container", "crystal"):
            return GetItem.HeartContainer
        if matches("piece"):
            return GetItem.HeartPiece
    if "<3" in name or name == "Health Cicada" or name == "Pipe Vial":
        return GetItem.HeartContainer
    if name in ["Mask_Shard", "Health Piece", "Heart Ore", "Box of Crayons"]:
        return GetItem.HeartPiece
    if matches("potion", "ether", "elixir", "elixer", "medicine", "medikit") or "Water of Life" in name:
        if matches("blue"):
            return GetItem.ItemPotShopBlue
        return GetItem.ItemPotShopRed
    if matches("bee"):
        return GetItem.Bee
    if matches("male", "female") and game == "Twilight Princess":
        return GetItem.Bee
    if matches("fairy", "faerie") and "Great Fairy" not in name:
        return GetItem.Fairy
    if matches("letter") or name == "Note to Mom":
        return GetItem.MessageBottle
    if matches("stone"):
        return GetItem.ItemStoneBeauty
    if matches("glasses", "sunglasses", "visor", "scope", "lens"):
        return GetItem.HintGlasses
    if matches("rupee", "rupees"):
        if matches("blue", "5", "five"):
            return GetItem.RupeeB
        if matches("red", "yellow", "20"):
            return GetItem.RupeeR
        if matches("purple", "50"):
            return GetItem.RupeePurple
        if matches("silver", "orange", "100"):
            return GetItem.RupeeSilver
        if matches("gold", "200", "300", "500"):
            return GetItem.RupeeGold
        return GetItem.RupeeG
    if matches("money", "coin", "coins", "bills", "gold", "golds", "gil", "gems", "geo", "jin", \
            "point", "points", "candy", "candies", "crystals", "moniez", "credits", "garibs", "pons") \
            or "$" in name or "Precursor Orb" in name or "Tears of Atonement" in name:
        if game not in ["Celeste (Open World)", "Final Fantasy Mystic Quest"] \
                and name not in ["Nintendo Coin", "Rareware Coin", "Coin of Crowl"]:
            return GetItem.RupeeG
    if game == "Final Fantasy" and "Gold" in name:
        return GetItem.RupeeG
    if game == "Astalon" and "Orbs" in name:
        return GetItem.RupeeG
    if name in ["5 Rings", "10 Rings", "100G", "500G", "1000G"]:
        return GetItem.RupeeG
    if matches("fruit", "berry", "strawberry", "raspberry"):
        return GetItem.EscapeFruit
    if name == "Grub":
        return GetItem.Kinsta
    if name in ["Nayru's Pearl", "Blue Questagon"]:
        return GetItem.PendantWisdom
    if name in ["Din's Pearl", "Red Questagon"]:
        return GetItem.PendantPower
    if name in ["Farore's Pearl", "Green Questagon"]:
        return GetItem.PendantCourage

    return default
