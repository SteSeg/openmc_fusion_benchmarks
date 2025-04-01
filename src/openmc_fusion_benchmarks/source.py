class SpatialDistribution:
    def __init__(self, type_: str, location=None, bounds=None):
        self.type = type_
        self.location = location if location else []
        self.bounds = bounds if bounds else []

    def __repr__(self):
        loc_str = f"location={self.location}" if self.location else "N/A"
        bounds_str = f"bounds={self.bounds}" if self.bounds else "N/A"
        return f"<spatial distribution type={self.type}, {loc_str}, {bounds_str}>"


class EnergyDistribution:
    def __init__(self, type_: str, bins: dict, probabilities: dict, interpolation=None):
        self.type = type_
        self.interpolation = interpolation if interpolation else "histogram"
        self.bins = bins["values"] if "values" in bins else []
        self.bins_units = bins.get("units", "N/A")
        self.probabilities = probabilities["values"] if "values" in probabilities else [
        ]

    def __repr__(self):
        return (f"<EnergyDistribution type={self.type}, interpolation={self.interpolation}, "
                f"bins=({len(self.bins)} values in {self.bins_units}), probabilities={len(self.probabilities)}>")


class AngularBin:
    def __init__(self, angle_range, energy_distribution: dict):
        self.angle_range = angle_range
        self.energy_distribution = EnergyDistribution(**energy_distribution)

    def __repr__(self):
        return f"<AngularBin range={self.angle_range}, {self.energy_distribution}>"


class AngularDistribution:
    def __init__(self, type_: str, bins=None):
        self.type = type_
        self.bins = [AngularBin(**b) for b in bins] if bins else []

    def __repr__(self):
        bins_str = f"{len(self.bins)} bins" if self.bins else "N/A"
        return f"<AngularDistribution type={self.type}, {bins_str}>"


class Rate:
    def __init__(self, value: float, units: str):
        self.value = value
        self.units = units

    def __repr__(self):
        return f"<Rate value={self.value} {self.units}>"


class Source:
    def __init__(self, data: dict):
        self.particle_type = data["particle_type"]
        self.geometry = SpatialDistribution(**data["geometry"])
        self.angular_distribution = AngularDistribution(
            **data["angular_distribution"])
        self.rate = Rate(**data["rate"])

    def __repr__(self):
        return (f"<Source particle={self.particle_type}, {self.geometry}, "
                f"{self.angular_distribution}, {self.rate}>")
