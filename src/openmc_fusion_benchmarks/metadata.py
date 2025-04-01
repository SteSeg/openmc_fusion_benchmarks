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
    def __init__(
        self, title: str, version: str, description: str, authors: list[dict],
        experiment_date: str, date_created: str, last_updated: str, location: dict,
        experiment_type: str, experiment_category: str, references: list[dict]
    ):
        self.title = title
        self.version = version
        self.description = description
        self.authors = [Author(**author) for author in authors]
        self.experiment_date = experiment_date
        self.date_created = date_created
        self.last_updated = last_updated
        self.location = Location(**location)
        self.experiment_type = experiment_type
        self.experiment_category = experiment_category
        self.references = [Reference(**ref) for ref in references]

    def __repr__(self):
        return (
            f"<Metadata title={self.title}, version={self.version}, experiment_type={self.experiment_type}, "
            f"experiment_category={self.experiment_category}, authors={len(self.authors)}, references={len(self.references)}>"
        )
