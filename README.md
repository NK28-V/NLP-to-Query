# EmployeeDB — Natural Language Query System

A simple full-stack system that accepts **natural language queries** and converts
them into MongoDB queries against the **EmployeeDB** database.

---

## 📂 Project Structure

This is a multi-file full-stack project organized as follows:

*   **`app.py`**: The Flask backend containing the NLP engine, MongoDB connection logic, and REST API endpoints.
*   **`templates/`**: Contains `index.html`, the main user interface for submitting queries.
*   **`static/`**: Holds `style.css`, providing the "glassmorphism" aesthetic and responsive layout.
*   **`EmployeeDB_Fixed.docx`**: Contains the full database schema design and the MongoDB setup script.
*   **`.gitignore`**: Configured to keep the repository clean from temporary Python files.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.8+    |
| MongoDB     | 6.x / 7.x |
| pip packages | flask, pymongo |

---

## Step-by-Step Setup

### 1. Install Python dependencies

```bash
pip install flask pymongo
```

### 2. Start MongoDB

```bash
# On Linux/Mac
mongod --dbpath /var/lib/mongodb

# On Windows
mongod --dbpath "C:\data\db"

# Or if installed as a service
sudo systemctl start mongod   # Linux
net start MongoDB              # Windows
```

### 3. Populate the Database

Open `mongosh` and paste the **complete insert script** from Section 4 of
the submission document (`EmployeeDB_Fixed.docx`).

```bash
mongosh
```

Then paste the script starting with `db.dropDatabase()`.

### 4. Run the Flask app

```bash
cd project
python app.py
```

Expected output:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### 5. Open the UI

Open your browser and go to: **http://127.0.0.1:5000**

---

## Supported Natural Language Queries

| Example Query | What It Does |
|---------------|--------------|
| `Show all employees` | Returns all 10 employees |
| `List employees in Sales department` | Filters by Sales dept |
| `Show employees in IT department` | Filters by IT dept |
| `Find employees who joined after 2022` | Date filter |
| `Find employees who joined before 2021` | Date filter |
| `Employees with Python skill` | Skill-based lookup |
| `Employees with MongoDB skill` | Skill-based lookup |
| `Show employees working in Mumbai` | Location filter |
| `Show employees in Bangalore` | Location filter |
| `Find average salary` | Aggregation |
| `Calculate total salary expense` | Aggregation |
| `Top 5 highest paid employees` | Sort + limit |
| `Salary greater than 80000` | Salary range filter |
| `Count employees per department` | Group by department |
| `Average salary per department` | Group + avg aggregation |
| `Show all managers` | Returns all managers |
| `Employees under Rahul Sharma` | Manager filter |
| `Employees on leave in March` | Date-range leave filter |
| `Employees enrolled in training` | Junction collection query |
| `Highest performance rating` | Performance reviews lookup |
| `Count employees in each location` | Location breakdown |

---

## API Endpoints

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/` | GET | — | Serves the UI |
| `/query` | POST | `{"query": "..."}` | Returns query results as JSON |
| `/collections` | GET | — | Lists all collections + doc counts |

### Example API Call

```bash
curl -X POST http://127.0.0.1:5000/query \
     -H "Content-Type: application/json" \
     -d '{"query": "Show employees in Sales department"}'
```

### Example Response

```json
{
  "description": "Employees in Sales department",
  "collection": "employees",
  "operation": "find({ department_id: ObjectId(\"64a00000000000000000d001\") })",
  "result": [
    { "name": "Amit Kumar", "salary": 75000, "join_date": "2021-06-15" },
    { "name": "Sneha Nair",  "salary": 82000, "join_date": "2020-03-10" }
  ]
}
```

---

## ObjectId Reference (Fixed)

| Collection | Character | Old (Invalid) | New (Valid) |
|------------|-----------|---------------|-------------|
| office_locations | `l` | `...l001` | `...c001` |
| managers | `m` | `...m01` | `...b01` |
| projects | `p` | `...p001` | `...f001` |
| skills | `s` | `...s001` | `...5001` |
| training_programs | `t` | `...t001` | `...7001` |
| departments | `d` | ✅ already valid | ✅ kept as-is |
| employees | `e` | ✅ already valid | ✅ kept as-is |

---

## Troubleshooting

**"DB Offline" shown in header**
→ MongoDB is not running. Start `mongod` (see Step 2).

**"No documents found"**
→ The database hasn't been populated. Run the insert script (see Step 3).

**Port already in use**
→ Change port in `app.py`: `app.run(port=5001)`

**Module not found**
→ Run `pip install flask pymongo`

---

*EmployeeDB | DBMS Project | April 2026*
