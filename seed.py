from database import SessionLocal, engine
from models import Base, Admin
from auth import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

# Check if admin exists
existing_admin = db.query(Admin).filter(Admin.user_id == "admin").first()
if not existing_admin:
    hashed_password = get_password_hash("admin0967")
    admin = Admin(user_id="admin", password_hash=hashed_password, answer1="dogy", answer2="red")
    db.add(admin)
    db.commit()
    print("Admin created")
else:
    print("Admin already exists")

db.close()
