from app.database import engine
from app.models.user import Base
from app.models.calculation import Calculation  # Register the table before creating metadata.

def init_db():
    Base.metadata.create_all(bind=engine)

def drop_db():
    Base.metadata.drop_all(bind=engine)

if __name__ == "__main__":
    init_db() # pragma: no cover
