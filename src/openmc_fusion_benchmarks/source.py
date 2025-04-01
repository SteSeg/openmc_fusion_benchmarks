class SpatialDistribution:
    def __init__(self, spatialdistribution_type: str, location=None, bounds=None):
        self.type = spatialdistribution_type
        self.location = location if location else []
        self.bounds = bounds if bounds else []

    def __repr__(self):
        loc_str = f"location={self.location}" if self.location else "N/A"
        bounds_str = f"bounds={self.bounds}" if self.bounds else "N/A"
        return f"<spatial distribution type={self.type}, {loc_str}, {bounds_str}>"


class EnergyDistribution:
    def __init__(self, energydistribution_type: str, bins: dict, probabilities: dict, interpolation=None):
        self.type = energydistribution_type
        self.interpolation = interpolation if interpolation else "histogram"
        self.bins = bins.get("values", [])
        self.bins_units = bins.get("units", "N/A")
        self.probabilities = probabilities.get("values", [])

    def __repr__(self):
        bin_preview = ", ".join(
            f"{b:.3g}" for b in self.bins[:3]) + ("..." if len(self.bins) > 3 else "")
        prob_preview = ", ".join(
            f"{p:.3g}" for p in self.probabilities[:3]) + ("..." if len(self.probabilities) > 3 else "")

        return (f"<EnergyDistribution type={self.type}, interpolation={self.interpolation}, "
                f"bins=[{bin_preview}] {self.bins_units}, probabilities=[{prob_preview}]>")


class AngularBin:
    def __init__(self, angle_range, energy_distribution: dict):
        self.angle_range = angle_range
        self.energy_distribution = EnergyDistribution(**energy_distribution)

    def __repr__(self):
        return f"<AngularBin range={self.angle_range}, energy_distribution={self.energy_distribution}>"


class AngularDistribution:
    def __init__(self, angulardistribution_type: str, bins=None):
        self.type = angulardistribution_type
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
    def __init__(self, data):
        if isinstance(data, list):  # Handle multiple sources
            data = data[0]  # Take the first source (modify as needed)

        self.particle_type = data["particle_type"]
        self.spatial_distribution = SpatialDistribution(
            **data["spatial_distribution"])
        self.angular_distribution = AngularDistribution(
            **data["angular_distribution"])
        self.rate = Rate(**data["rate"])

    def __repr__(self):
        return (f"<Source particle={self.particle_type}, {self.spatial_distribution}, "
                f"{self.angular_distribution}, {self.rate}>")
