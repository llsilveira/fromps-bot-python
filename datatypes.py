import enum


class WeeklyStatus(enum.Enum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'


class EntryStatus(enum.Enum):
    REGISTERED = 'REGISTERED'
    TIME_SUBMITTED = 'TIME_SUBMITTED'
    DONE = 'DONE'
    DNF = 'DNF'



class Games(enum.Enum):
    ALTTPR = (
        "A Link to the Past Randomizer",
        ["alttp", "alttpr"],
    )
    OOTR = (
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
    PKMN_CRYSTAL = (
        "Pokemon Crystal Full Item Randomizer",
        ["pkmn", "pokemon"],
    )

    def __init__(self, str, keys):
        self.str = str
        self.keys = keys

    def __str__(self):
        return self.str