from app.database.connection import initialize_store
import app.database.models  # register all models


def init_db():
    initialize_store()
