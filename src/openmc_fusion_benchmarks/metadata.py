class Author:
    def __init__(self, name: str, affiliation: str, email: str):
        self.name = name
        self.affiliation = affiliation
        self.email = email

    def __repr__(self):
        return f"<Author name={self.name}, affiliation={self.affiliation}, email={self.email}>"


class Location:
    def __init__(self, facility: str, city: str, country: str):
        self.facility = facility
        self.city = city
        self.country = country

    def __repr__(self):
        return f"<Location facility={self.facility}, city={self.city}, country={self.country}>"


class Reference:
    def __init__(self, title: str, doi: str):
        self.title = title
        self.doi = doi

    def __repr__(self):
        return f"<Reference title={self.title}, doi={self.doi}>"


class Metadata:
    def __init__(self, data: dict):
        self.title = data.get("title", "N/A")
        self.version = data.get("version", "N/A")
        self.description = data.get("description", "N/A")
        self.authors = [Author(**author) for author in data.get("authors", [])]
        self.experiment_date = data.get("experiment_date", "N/A")
        self.date_created = data.get("date_created", "N/A")
        self.last_updated = data.get("last_updated", "N/A")
        self.location = Location(
            **data.get("location", {})) if "location" in data else None
        self.experiment_type = data.get("experiment_type", "N/A")
        self.experiment_category = data.get("experiment_category", "N/A")
        self.references = [Reference(**ref)
                           for ref in data.get("references", [])]

    def __repr__(self):
        return (
            f"<Metadata title={self.title}, version={self.version}, experiment_type={self.experiment_type}, "
            f"experiment_category={self.experiment_category}, authors={len(self.authors)}, references={len(self.references)}>"
        )
