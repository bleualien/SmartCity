from models import db
from models.user import User
from models.department import Department
from models.tag import Tag
import uuid


# 1. CREATE DEPARTMENTS (IF NOT EXISTS)
def create_base_departments():
    departments = [
        "Waste Management",
        "Water",
        "Electricity",
        "Roads",
        "Ward Office"
    ]

    for name in departments:
        exists = Department.query.filter_by(name=name).first()
        if not exists:
            d = Department(id=str(uuid.uuid4()), name=name)
            db.session.add(d)

    db.session.commit()
    print("✔ Base departments created")


# 2. CREATE BASE TAGS + LINK TO DEPARTMENTS
def create_base_tags():
    """
    Each tag belongs to a department.
    Tags help classify detections (waste, pothole, etc.)
    """

    tag_map = {
        "waste": "Waste Management",
        "garbage": "Waste Management",
        "trash": "Waste Management",

        "pothole": "Roads",
        "road_damage": "Roads",

        "water_leak": "Water",
        "pipeline_break": "Water",

        "electric_fault": "Electricity",
        "wire_damage": "Electricity",
    }

    for tag_name, dept_name in tag_map.items():
        dept = Department.query.filter_by(name=dept_name).first()
        if not dept:
            continue
        
        exists = Tag.query.filter_by(name=tag_name).first()
        if not exists:
            t = Tag(
                id=str(uuid.uuid4()),
                name=tag_name,
                department_id=dept.id
            )
            db.session.add(t)

    db.session.commit()
    print("✔ Base tags created and linked to departments")


# 3. CREATE DEFAULT USER 

def create_default_user():
    """Create a default system user for testing."""
    exists = User.query.filter_by(email="default@system.com").first()
    if exists:
        return exists

    u = User(
        id=str(uuid.uuid4()),
        name="System Default",
        email="default@system.com"
    )
    db.session.add(u)
    db.session.commit()

    print("✔ Default user created")
    return u


# 4. RUN ALL BASE DATA SETUP
def initialize_base_data():
    create_base_departments()
    create_base_tags()
    create_default_user()
    print("🎯 Base SmartCity data initialized")
