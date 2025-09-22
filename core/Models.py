from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    organization = db.Column(db.String(100), nullable=True)
    installation_date = db.Column(db.Date, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    variables = db.Column(db.String(255), nullable=False)
    instrument_type = db.Column(db.String(100), nullable=False)
    airlinkID = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String, default='offline')

    def __init__(self, id, name, airlinkID, image, organization, installation_date, latitude, longitude, variables, instrument_type):
        self.id = id
        self.name = name
        self.airlinkID = airlinkID
        self.image = image
        self.organization = organization
        self.installation_date = installation_date
        self.latitude = latitude
        self.longitude = longitude
        self.variables = variables
        self.instrument_type = instrument_type

    @classmethod
    def get_airlinkID_by_id(cls, id):
        instrument = cls.query.filter_by(id=id).first()
        if instrument:
            return instrument.airlinkID
        return None

    @classmethod
    def get_variables_by_id(cls, id):
        instrument = cls.query.filter_by(id=id).first()
        if instrument:
            return instrument.variables
        return None