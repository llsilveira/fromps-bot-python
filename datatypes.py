import enum


class Games(enum.Enum):
    ALTTPR = (
        "A Link to the Past Randomizer",
        ["alttp", "alttpr"],
    )
    OOT = (
        "Ocarina of Time Randomizer",
        ["oot", "ootr", "ocarina"],
    )
    MMR = (
        "Majora's Mask Randomizer",
        ["mm", "mmr", "majora", "majoras", "majora's"],
    )
    SMZ3 = (
        "SMZ3 Combo Randomizer",
        ["smz3", "alttpsm", "s3z3", "combo"],
    )
    PKMN_CRYSTAL_FULL = (
        "Pokemon Crystal Full Item Randomizer",
        ["pkmnfull"],
    )

    def __init__(self, str, keys):
        self.str = str
        self.keys = keys

    def __str__(self):
        return self.str