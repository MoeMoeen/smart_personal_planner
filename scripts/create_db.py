from app.db.db import engine
from app.models import Base

# Create all tables defined by our models
Base.metadata.create_all(bind=engine)

print("✅ All tables created successfully.")