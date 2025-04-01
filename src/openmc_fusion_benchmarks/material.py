class Density:
    def __init__(self, value: float, units: str):
        self.value = value
        self.units = units

    def __repr__(self):
        return f"{self.value} {self.units}"

    # def to_openmc(self):
    #     # Return in a format compatible with openmc.Material
    #     return {'density': self.value, 'units': self.units}


class Composition:
    def __init__(self, composition_type: str, fraction_type: str, data: dict):
        self.composition_type = composition_type
        self.fraction_type = fraction_type
        self.data = data

    def __repr__(self):
        lines = [
            f"<Composition type={self.composition_type}, fraction_type={self.fraction_type}, nuclides={len(self.data)}>"]
        for nuclide, fraction in self.data.items():
            lines.append(f"<{nuclide}: {fraction}>")
        return "\n".join(lines)

    # def to_openmc(self):
    #     return {
    #         'type': self.type,
    #         'fraction_type': self.fraction_type,
    #         'data': self.data
    #     }


class Material:
    def __init__(self, material_id: int, name: str, composition: dict, density: dict):
        self.material_id = material_id
        self.name = name
        self.composition = Composition(
            composition_type=composition['composition_type'],
            fraction_type=composition['fraction_type'],
            data=composition['data']
        )
        self.density = Density(**density)

    def __repr__(self):
        return (f"<Material id={self.material_id}, name={self.name}, "
                f"composition={self.composition}, density={self.density}>")

    # def to_openmc(self):
    #     import openmc
    #     mat = openmc.Material()
    #     mat.name = self.name
    #     mat.set_density(self.density.units, self.density.value)

    #     if self.composition.fraction_type == 'atomic':
    #         method = mat.add_nuclide
    #     elif self.composition.fraction_type == 'weight':
    #         method = mat.add_nuclide  # openmc uses same method but needs `percent_type`
    #     else:
    #         raise ValueError(f"Unsupported fraction_type: {self.composition.fraction_type}")

    #     for nuclide, fraction in self.composition.data.items():
    #         method(nuclide, fraction, self.composition.fraction_type)

    #     return mat
