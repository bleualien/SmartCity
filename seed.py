from models import db, Department, Tag
from app import create_app

app = create_app()
app.app_context().push()

departments = [
    "Waste Management",
    "Road Maintenance",
    "Drainage",
    "Electricity",
    "Water Management"
]

for name in departments:
    if not Department.query.filter_by(name=name).first():
        db.session.add(Department(name=name))

db.session.commit()
print("Departments added.")
