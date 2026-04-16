"""
EmployeeDB — Natural Language Query Flask Backend
================================================
Run:  pip install flask pymongo
      python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import json, re

app = Flask(__name__)

# ─── MongoDB connection ────────────────────────────────────────────────────
client = MongoClient("mongodb://localhost:27017")
db     = client["EmployeeDB"]

# ─── Valid ObjectIds (must match your insert script exactly) ──────────────
DEPT_IDS = {
    "sales":     "64a00000000000000000d001",
    "hr":        "64a00000000000000000d002",
    "it":        "64a00000000000000000d003",
    "finance":   "64a00000000000000000d004",
    "marketing": "64a00000000000000000d005",
}
LOC_IDS = {
    "mumbai":    "64a00000000000000000c001",
    "delhi":     "64a00000000000000000c002",
    "bangalore": "64a00000000000000000c003",
    "pune":      "64a00000000000000000c004",
    "hyderabad": "64a00000000000000000c005",
}
SKILL_IDS = {
    "python":  "64a000000000000000005001",
    "sql":     "64a000000000000000005002",
    "java":    "64a000000000000000005003",
    "excel":   "64a000000000000000005004",
    "mongodb": "64a000000000000000005005",
}

# ─── JSON serialiser (handles ObjectId, datetime) ─────────────────────────
class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d")
        return super().default(obj)

def mongo_to_json(docs):
    return json.loads(json.dumps(docs, cls=MongoEncoder))

# ─── Natural language → MongoDB query mapper ──────────────────────────────
def parse_query(text):
    t = text.lower().strip()

    # ── Count queries ─────────────────────────────────────────────────────
    if re.search(r"count.*employee", t):
        total = db.employees.count_documents({})
        return {"description": "Count of all employees",
                "collection": "employees",
                "operation": "countDocuments({})",
                "result": [{"total_employees": total}]}

    if re.search(r"count.*manager", t):
        total = db.managers.count_documents({})
        return {"description": "Count of all managers",
                "collection": "managers",
                "operation": "countDocuments({})",
                "result": [{"total_managers": total}]}

    if re.search(r"count.*department", t):
        total = db.departments.count_documents({})
        return {"description": "Count of all departments",
                "collection": "departments",
                "operation": "countDocuments({})",
                "result": [{"total_departments": total}]}

    if re.search(r"count.*leave.*march|leave.*march.*count", t):
        total = db.leaves.count_documents({
            "leave_date": {"$gte": datetime(2025,3,1), "$lt": datetime(2025,4,1)}
        })
        return {"description": "Count of leaves in March 2025",
                "collection": "leaves",
                "operation": 'countDocuments({ leave_date: { $gte: ISODate("2025-03-01"), $lt: ISODate("2025-04-01") } })',
                "result": [{"leaves_in_march_2025": total}]}

    # ── Aggregation: average salary ───────────────────────────────────────
    if re.search(r"average salary|avg salary|mean salary", t):
        res = list(db.employees.aggregate([
            {"$group": {"_id": None, "avgSalary": {"$avg": "$salary"}}},
            {"$project": {"_id": 0, "avgSalary": {"$round": ["$avgSalary", 2]}}}
        ]))
        return {"description": "Average salary of all employees",
                "collection": "employees",
                "operation": 'aggregate([ {$group:{_id:null,avgSalary:{$avg:"$salary"}}} ])',
                "result": res}

    # ── Aggregation: total salary ─────────────────────────────────────────
    if re.search(r"total salary|salary expense|payroll", t):
        res = list(db.employees.aggregate([
            {"$group": {"_id": None, "totalSalary": {"$sum": "$salary"}}},
            {"$project": {"_id": 0, "totalSalary": 1}}
        ]))
        return {"description": "Total salary expense",
                "collection": "employees",
                "operation": 'aggregate([ {$group:{_id:null,totalSalary:{$sum:"$salary"}}} ])',
                "result": res}

    # ── Aggregation: count per department ─────────────────────────────────
    if re.search(r"count.*per department|employee.*each department|employees.*department", t) and "show" not in t and "list" not in t:
        res = list(db.employees.aggregate([
            {"$group": {"_id": "$department_id", "count": {"$sum": 1}}},
            {"$lookup": {"from": "departments", "localField": "_id", "foreignField": "_id", "as": "dept"}},
            {"$unwind": "$dept"},
            {"$project": {"_id": 0, "department": "$dept.department_name", "count": 1}},
            {"$sort": {"count": -1}}
        ]))
        return {"description": "Employee count per department",
                "collection": "employees",
                "operation": "aggregate( [$group, $lookup, $sort] )",
                "result": res}

    # ── Aggregation: average salary per department ────────────────────────
    if re.search(r"salary.*department|department.*salary|avg.*department", t):
        res = list(db.employees.aggregate([
            {"$group": {"_id": "$department_id", "avgSalary": {"$avg": "$salary"}}},
            {"$lookup": {"from": "departments", "localField": "_id", "foreignField": "_id", "as": "dept"}},
            {"$unwind": "$dept"},
            {"$project": {"_id": 0, "department": "$dept.department_name", "avgSalary": 1}},
            {"$sort": {"avgSalary": -1}}
        ]))
        return {"description": "Average salary per department",
                "collection": "employees + departments",
                "operation": "aggregate( [$group, $lookup, $project, $sort] )",
                "result": res}

    # ── Employee + department lookup ──────────────────────────────────────
    if re.search(r"department name|with department|show department", t):
        res = list(db.employees.aggregate([
            {"$lookup": {"from": "departments", "localField": "department_id", "foreignField": "_id", "as": "dept"}},
            {"$unwind": "$dept"},
            {"$project": {"_id": 0, "name": 1, "department": "$dept.department_name", "salary": 1}}
        ]))
        return {"description": "Employees with their department names",
                "collection": "employees + departments",
                "operation": "aggregate([ $lookup, $unwind, $project ])",
                "result": res}

    # ── Filter by department name ─────────────────────────────────────────
    for dept_key, dept_id in DEPT_IDS.items():
        pattern = rf"\b{dept_key}\b"
        if re.search(pattern, t):
            docs = list(db.employees.find(
                {"department_id": ObjectId(dept_id)},
                {"_id": 0, "name": 1, "salary": 1, "join_date": 1}
            ))
            return {"description": f"Employees in {dept_key.title()} department",
                    "collection": "employees",
                    "operation": f'find({{ department_id: ObjectId("{dept_id}") }})',
                    "result": docs}

    # ── Filter by location/city ───────────────────────────────────────────
    for city_key, loc_id in LOC_IDS.items():
        if city_key in t:
            docs = list(db.employees.find(
                {"location_id": ObjectId(loc_id)},
                {"_id": 0, "name": 1, "salary": 1}
            ))
            return {"description": f"Employees working in {city_key.title()}",
                    "collection": "employees",
                    "operation": f'find({{ location_id: ObjectId("{loc_id}") }})',
                    "result": docs}

    # ── Filter by skill ───────────────────────────────────────────────────
    for skill_key, skill_id in SKILL_IDS.items():
        if skill_key in t:
            emp_ids = db.employee_skills.distinct("employee_id", {"skill_id": ObjectId(skill_id)})
            docs = list(db.employees.find(
                {"_id": {"$in": emp_ids}},
                {"_id": 0, "name": 1, "salary": 1}
            ))
            return {"description": f"Employees with {skill_key.title()} skill",
                    "collection": "employee_skills + employees",
                    "operation": f'employee_skills.distinct(...) → employees.find({{ _id: {{ $in: empIds }} }})',
                    "result": docs}

    # ── Salary filters ────────────────────────────────────────────────────
    m = re.search(r"salary.*(?:greater|more|above|over|>)\s*(?:than\s*)?(\d+)", t)
    if m:
        threshold = int(m.group(1))
        docs = list(db.employees.find(
            {"salary": {"$gt": threshold}},
            {"_id": 0, "name": 1, "salary": 1}
        ).sort("salary", -1))
        return {"description": f"Employees with salary > {threshold}",
                "collection": "employees",
                "operation": f'find({{ salary: {{ $gt: {threshold} }} }}).sort({{ salary: -1 }})',
                "result": docs}

    m = re.search(r"salary.*(?:less|below|under|<)\s*(?:than\s*)?(\d+)", t)
    if m:
        threshold = int(m.group(1))
        docs = list(db.employees.find(
            {"salary": {"$lt": threshold}},
            {"_id": 0, "name": 1, "salary": 1}
        ).sort("salary", -1))
        return {"description": f"Employees with salary < {threshold}",
                "collection": "employees",
                "operation": f'find({{ salary: {{ $lt: {threshold} }} }}).sort({{ salary: -1 }})',
                "result": docs}

    if re.search(r"highest salary|top paid|highest paid|max salary", t):
        docs = list(db.employees.find(
            {}, {"_id": 0, "name": 1, "salary": 1}
        ).sort("salary", -1).limit(5))
        return {"description": "Top 5 highest paid employees",
                "collection": "employees",
                "operation": 'find({}).sort({ salary: -1 }).limit(5)',
                "result": docs}

    # ── Date filters ──────────────────────────────────────────────────────
    m = re.search(r"joined after\s*(\d{4})", t)
    if m:
        yr = int(m.group(1))
        docs = list(db.employees.find(
            {"join_date": {"$gt": datetime(yr, 12, 31)}},
            {"_id": 0, "name": 1, "join_date": 1}
        ))
        return {"description": f"Employees who joined after {yr}",
                "collection": "employees",
                "operation": f'find({{ join_date: {{ $gt: ISODate("{yr}-12-31") }} }})',
                "result": docs}

    m = re.search(r"joined before\s*(\d{4})", t)
    if m:
        yr = int(m.group(1))
        docs = list(db.employees.find(
            {"join_date": {"$lt": datetime(yr, 1, 1)}},
            {"_id": 0, "name": 1, "join_date": 1}
        ))
        return {"description": f"Employees who joined before {yr}",
                "collection": "employees",
                "operation": f'find({{ join_date: {{ $lt: ISODate("{yr}-01-01") }} }})',
                "result": docs}

    # ── Managers ──────────────────────────────────────────────────────────
    if re.search(r"show.*manager|list.*manager|all manager", t):
        docs = list(db.managers.find({}, {"_id": 0, "manager_name": 1}))
        return {"description": "All managers",
                "collection": "managers",
                "operation": 'find({}, { manager_name: 1, _id: 0 })',
                "result": docs}

    m = re.search(r"manager\s+(\w+\s+\w+)", t)
    if m:
        mgr_name = m.group(1).title()
        mgr = db.managers.find_one({"manager_name": {"$regex": mgr_name, "$options": "i"}})
        if mgr:
            docs = list(db.employees.find(
                {"manager_id": mgr["_id"]},
                {"_id": 0, "name": 1, "salary": 1}
            ))
            return {"description": f"Employees under {mgr['manager_name']}",
                    "collection": "employees",
                    "operation": f'find({{ manager_id: ObjectId("{mgr["_id"]}") }})',
                    "result": docs}

    # ── Projects ──────────────────────────────────────────────────────────
    if re.search(r"project alpha|alpha project", t):
        proj = db.projects.find_one({"project_name": "Project Alpha"})
        if proj:
            emp_ids = list(db.employee_projects.find({"project_id": proj["_id"]}, {"employee_id": 1, "_id": 0}))
            ids = [e["employee_id"] for e in emp_ids]
            docs = list(db.employees.find({"_id": {"$in": ids}}, {"_id": 0, "name": 1}))
            return {"description": "Employees assigned to Project Alpha",
                    "collection": "employee_projects + employees",
                    "operation": "employee_projects.find(...) → employees.find({ _id: {$in: ...} })",
                    "result": docs}

    if re.search(r"all project|list project|show project", t):
        docs = list(db.projects.find({}, {"_id": 0, "project_name": 1}))
        return {"description": "All projects",
                "collection": "projects",
                "operation": 'find({}, { project_name: 1, _id: 0 })',
                "result": docs}

    if re.search(r"count.*project|project.*count|employees per project", t):
        res = list(db.employee_projects.aggregate([
            {"$group": {"_id": "$project_id", "count": {"$sum": 1}}},
            {"$lookup": {"from": "projects", "localField": "_id", "foreignField": "_id", "as": "proj"}},
            {"$unwind": "$proj"},
            {"$project": {"_id": 0, "project": "$proj.project_name", "count": 1}},
            {"$sort": {"count": -1}}
        ]))
        return {"description": "Employee count per project",
                "collection": "employee_projects + projects",
                "operation": "aggregate( [$group, $lookup, $sort] )",
                "result": res}

    # ── Leave / Attendance ────────────────────────────────────────────────
    if re.search(r"leave.*march|march.*leave|leave in march", t):
        emp_ids = list(db.leaves.find({
            "leave_date": {"$gte": datetime(2025,3,1), "$lt": datetime(2025,4,1)}
        }, {"employee_id": 1, "_id": 0}))
        ids = [e["employee_id"] for e in emp_ids]
        docs = list(db.employees.find({"_id": {"$in": ids}}, {"_id": 0, "name": 1}))
        return {"description": "Employees who took leave in March 2025",
                "collection": "leaves + employees",
                "operation": 'leaves.find({ leave_date: {$gte: ..., $lt: ...} }) → employees.find()',
                "result": docs}

    if re.search(r"attendance|present|absent", t):
        docs = list(db.attendance.find({}, {"_id": 0, "date": 1, "status": 1}).limit(20))
        return {"description": "Recent attendance records",
                "collection": "attendance",
                "operation": 'find({}).limit(20)',
                "result": docs}

    # ── Performance reviews ────────────────────────────────────────────────
    if re.search(r"performance|rating|review", t):
        max_rating = 5
        emp_ids = db.performance_reviews.distinct("employee_id", {"rating": max_rating})
        docs = list(db.employees.find({"_id": {"$in": emp_ids}}, {"_id": 0, "name": 1}))
        return {"description": f"Employees with highest performance rating ({max_rating})",
                "collection": "performance_reviews + employees",
                "operation": 'performance_reviews.distinct(...) → employees.find()',
                "result": docs}

    # ── Training programs ──────────────────────────────────────────────────
    if re.search(r"training|enrolled", t):
        trained_ids = db.employee_training.distinct("employee_id")
        docs = list(db.employees.find(
            {"_id": {"$in": trained_ids}},
            {"_id": 0, "name": 1}
        ))
        return {"description": "Employees enrolled in training programs",
                "collection": "employee_training + employees",
                "operation": 'employee_training.distinct("employee_id") → employees.find()',
                "result": docs}

    # ── Skills ────────────────────────────────────────────────────────────
    if re.search(r"all skill|list skill|show skill", t):
        docs = list(db.skills.find({}, {"_id": 0, "skill_name": 1}))
        return {"description": "All skills",
                "collection": "skills",
                "operation": 'find({}, { skill_name: 1, _id: 0 })',
                "result": docs}

    # ── Locations ────────────────────────────────────────────────────────
    if re.search(r"location|office|city|cities", t):
        res = list(db.employees.aggregate([
            {"$group": {"_id": "$location_id", "count": {"$sum": 1}}},
            {"$lookup": {"from": "office_locations", "localField": "_id", "foreignField": "_id", "as": "loc"}},
            {"$unwind": "$loc"},
            {"$project": {"_id": 0, "city": "$loc.city", "count": 1}},
            {"$sort": {"count": -1}}
        ]))
        return {"description": "Employee count by office location",
                "collection": "employees + office_locations",
                "operation": "aggregate([ $group, $lookup, $sort ])",
                "result": res}

    # ── Default: show all employees ────────────────────────────────────────
    docs = list(db.employees.find({}, {"_id": 0, "name": 1, "salary": 1, "join_date": 1}))
    return {"description": "All employees (default query)",
            "collection": "employees",
            "operation": 'find({}, { name: 1, salary: 1, join_date: 1, _id: 0 })',
            "result": docs}


# ─── Flask routes ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json(silent=True) or {}
    user_input = data.get("query", "").strip()
    if not user_input:
        return jsonify({"error": "Empty query"}), 400

    # Save to user_queries collection
    db.user_queries.insert_one({"user_query": user_input, "timestamp": datetime.utcnow()})

    result = parse_query(user_input)
    result["result"] = mongo_to_json(result["result"])
    return jsonify(result)

@app.route("/collections", methods=["GET"])
def list_collections():
    cols = db.list_collection_names()
    counts = {c: db[c].count_documents({}) for c in cols}
    return jsonify({"collections": counts})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
