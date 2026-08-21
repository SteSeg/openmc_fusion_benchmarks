class PickFreezeAnalysis:
    """Statistical analysis of a pick-freeze TMC tally."""

    def __init__(self, tally):
        if tally.mode != "pick-freeze":
            raise ValueError(
                "PickFreezeAnalysis requires a TMCTally in pick-freeze mode."
            )

        self.tally = tally