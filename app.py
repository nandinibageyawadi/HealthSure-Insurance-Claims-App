from flask import Flask, render_template, request, redirect, url_for, flash, abort
import sqlite3
from pathlib import Path
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "replace-this-for-real-deployment"
DB_PATH = Path(__file__).with_name("health_insurance.db")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS customers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_no TEXT NOT NULL UNIQUE,
 full_name TEXT NOT NULL,
 phone TEXT,
 email TEXT,
 date_of_birth TEXT,
 address TEXT
);
CREATE TABLE IF NOT EXISTS dependents (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL,
 full_name TEXT NOT NULL,
 relationship TEXT NOT NULL,
 date_of_birth TEXT,
 FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS plans (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 plan_code TEXT NOT NULL UNIQUE,
 plan_name TEXT NOT NULL,
 coverage_limit REAL NOT NULL CHECK(coverage_limit > 0),
 annual_premium REAL NOT NULL CHECK(annual_premium >= 0),
 description TEXT
);
CREATE TABLE IF NOT EXISTS policies (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 policy_number TEXT NOT NULL UNIQUE,
 customer_id INTEGER NOT NULL,
 plan_id INTEGER NOT NULL,
 start_date TEXT NOT NULL,
 end_date TEXT NOT NULL,
 sum_insured REAL NOT NULL CHECK(sum_insured > 0),
 status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Expired','Suspended','Cancelled')),
 FOREIGN KEY(customer_id) REFERENCES customers(id),
 FOREIGN KEY(plan_id) REFERENCES plans(id),
 CHECK(end_date >= start_date)
);
CREATE TABLE IF NOT EXISTS premium_payments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 policy_id INTEGER NOT NULL,
 payment_date TEXT NOT NULL,
 amount REAL NOT NULL CHECK(amount > 0),
 payment_method TEXT NOT NULL,
 reference_no TEXT UNIQUE,
 FOREIGN KEY(policy_id) REFERENCES policies(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS hospitals (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 hospital_code TEXT NOT NULL UNIQUE,
 hospital_name TEXT NOT NULL,
 city TEXT NOT NULL,
 network_status TEXT NOT NULL DEFAULT 'Network' CHECK(network_status IN ('Network','Non-network'))
);
CREATE TABLE IF NOT EXISTS claims (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_number TEXT NOT NULL UNIQUE,
 policy_id INTEGER NOT NULL,
 hospital_id INTEGER NOT NULL,
 claim_date TEXT NOT NULL,
 amount_claimed REAL NOT NULL CHECK(amount_claimed > 0),
 description TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Under Review','Approved','Rejected','Settled','Appealed')),
 FOREIGN KEY(policy_id) REFERENCES policies(id),
 FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
);
CREATE TABLE IF NOT EXISTS treatments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL,
 treatment_name TEXT NOT NULL,
 treatment_date TEXT NOT NULL,
 cost REAL NOT NULL CHECK(cost >= 0),
 notes TEXT,
 FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS claim_documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL,
 document_type TEXT NOT NULL,
 document_reference TEXT NOT NULL,
 received_date TEXT NOT NULL,
 verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)),
 FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS assessments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL,
 assessor_name TEXT NOT NULL,
 assessment_date TEXT NOT NULL,
 eligible_amount REAL NOT NULL CHECK(eligible_amount >= 0),
 remarks TEXT,
 FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS decisions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL,
 decision_date TEXT NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('Approved','Rejected','More Information Required')),
 reason TEXT NOT NULL,
 FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS settlements (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL,
 settlement_date TEXT NOT NULL,
 amount REAL NOT NULL CHECK(amount > 0),
 payment_reference TEXT NOT NULL UNIQUE,
 FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS appeals (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL,
 appeal_date TEXT NOT NULL,
 reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Under Review','Resolved','Rejected')),
 resolution_notes TEXT,
 FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_policies_customer ON policies(customer_id);
CREATE INDEX IF NOT EXISTS idx_policies_status_dates ON policies(status, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_claims_policy ON claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_claims_status_date ON claims(status, claim_date);
CREATE INDEX IF NOT EXISTS idx_payments_policy ON premium_payments(policy_id);
"""

MODULES = {
 "customers": {
  "title":"Customers", "singular":"Customer", "table":"customers", "icon":"◉",
  "fields":[("customer_no","Customer ID","text",True),("full_name","Full name","text",True),("phone","Phone","text",False),("email","Email","email",False),("date_of_birth","Date of birth","date",False),("address","Address","text",False)],
  "columns":["customer_no","full_name","phone","email"]
 },
 "dependents": {
  "title":"Dependents", "singular":"Dependent", "table":"dependents", "icon":"♧",
  "fields":[("customer_id","Policy holder","select:customers",True),("full_name","Dependent name","text",True),("relationship","Relationship","text",True),("date_of_birth","Date of birth","date",False)],
  "columns":["full_name","relationship","date_of_birth","customer_id"]
 },
 "plans": {
  "title":"Insurance Plans", "singular":"Plan", "table":"plans", "icon":"▤",
  "fields":[("plan_code","Plan code","text",True),("plan_name","Plan name","text",True),("coverage_limit","Coverage limit (₹)","number",True),("annual_premium","Annual premium (₹)","number",True),("description","Description","text",False)],
  "columns":["plan_code","plan_name","coverage_limit","annual_premium"]
 },
 "policies": {
  "title":"Policies", "singular":"Policy", "table":"policies", "icon":"▣",
  "fields":[("policy_number","Policy number","text",True),("customer_id","Customer","select:customers",True),("plan_id","Plan","select:plans",True),("start_date","Start date","date",True),("end_date","End date","date",True),("sum_insured","Sum insured (₹)","number",True),("status","Status","options:Active|Expired|Suspended|Cancelled",True)],
  "columns":["policy_number","customer_id","plan_id","start_date","end_date","sum_insured","status"]
 },
 "premium_payments": {
  "title":"Premium Payments", "singular":"Premium payment", "table":"premium_payments", "icon":"₹",
  "fields":[("policy_id","Policy","select:policies",True),("payment_date","Payment date","date",True),("amount","Amount (₹)","number",True),("payment_method","Payment method","options:UPI|Card|Bank Transfer|Cash|Net Banking",True),("reference_no","Reference number","text",False)],
  "columns":["policy_id","payment_date","amount","payment_method","reference_no"]
 },
 "hospitals": {
  "title":"Hospitals", "singular":"Hospital", "table":"hospitals", "icon":"✚",
  "fields":[("hospital_code","Hospital code","text",True),("hospital_name","Hospital name","text",True),("city","City","text",True),("network_status","Network status","options:Network|Non-network",True)],
  "columns":["hospital_code","hospital_name","city","network_status"]
 },
 "claims": {
  "title":"Claims", "singular":"Claim", "table":"claims", "icon":"▧",
  "fields":[("claim_number","Claim number","text",True),("policy_id","Policy","select:policies",True),("hospital_id","Hospital","select:hospitals",True),("claim_date","Claim date","date",True),("amount_claimed","Amount claimed (₹)","number",True),("description","Claim description","text",True),("status","Status","options:Pending|Under Review|Approved|Rejected|Settled|Appealed",True)],
  "columns":["claim_number","policy_id","hospital_id","claim_date","amount_claimed","status"]
 },
 "treatments": {
  "title":"Treatments", "singular":"Treatment", "table":"treatments", "icon":"✚",
  "fields":[("claim_id","Claim","select:claims",True),("treatment_name","Treatment name","text",True),("treatment_date","Treatment date","date",True),("cost","Cost (₹)","number",True),("notes","Notes","text",False)],
  "columns":["claim_id","treatment_name","treatment_date","cost","notes"]
 },
 "claim_documents": {
  "title":"Claim Documents", "singular":"Claim document", "table":"claim_documents", "icon":"▤",
  "fields":[("claim_id","Claim","select:claims",True),("document_type","Document type","text",True),("document_reference","Document reference","text",True),("received_date","Received date","date",True),("verified","Verified","options:0|1",True)],
  "columns":["claim_id","document_type","document_reference","received_date","verified"]
 },
 "assessments": {
  "title":"Assessments", "singular":"Assessment", "table":"assessments", "icon":"✓",
  "fields":[("claim_id","Claim","select:claims",True),("assessor_name","Assessor name","text",True),("assessment_date","Assessment date","date",True),("eligible_amount","Eligible amount (₹)","number",True),("remarks","Remarks","text",False)],
  "columns":["claim_id","assessor_name","assessment_date","eligible_amount","remarks"]
 },
 "decisions": {
  "title":"Claim Decisions", "singular":"Decision", "table":"decisions", "icon":"⚖",
  "fields":[("claim_id","Claim","select:claims",True),("decision_date","Decision date","date",True),("decision","Decision","options:Approved|Rejected|More Information Required",True),("reason","Reason","text",True)],
  "columns":["claim_id","decision_date","decision","reason"]
 },
 "settlements": {
  "title":"Settlements", "singular":"Settlement", "table":"settlements", "icon":"₹",
  "fields":[("claim_id","Claim","select:claims",True),("settlement_date","Settlement date","date",True),("amount","Settlement amount (₹)","number",True),("payment_reference","Payment reference","text",True)],
  "columns":["claim_id","settlement_date","amount","payment_reference"]
 },
 "appeals": {
  "title":"Appeals", "singular":"Appeal", "table":"appeals", "icon":"↗",
  "fields":[("claim_id","Claim","select:claims",True),("appeal_date","Appeal date","date",True),("reason","Appeal reason","text",True),("status","Status","options:Open|Under Review|Resolved|Rejected",True),("resolution_notes","Resolution notes","text",False)],
  "columns":["claim_id","appeal_date","reason","status","resolution_notes"]
 }
}

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with connect() as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
            con.executemany("INSERT INTO customers(customer_no,full_name,phone,email,date_of_birth,address) VALUES(?,?,?,?,?,?)", [
                ("CUS-1001","Aarav Mehta","9876501201","aarav@example.com","1991-04-12","Hyderabad"),
                ("CUS-1002","Diya Sharma","9876501202","diya@example.com","1987-09-03","Secunderabad"),
                ("CUS-1003","Kabir Rao","9876501203","kabir@example.com","1995-01-21","Warangal")
            ])
            con.executemany("INSERT INTO plans(plan_code,plan_name,coverage_limit,annual_premium,description) VALUES(?,?,?,?,?)", [
                ("HLT-ESS","Health Essential",500000,8500,"Core hospitalization cover"),
                ("HLT-PLUS","Health Plus",1000000,14500,"Higher coverage with broader benefits"),
                ("HLT-FAM","Family Secure",1500000,21000,"Family floater demonstration plan")
            ])
            con.executemany("INSERT INTO hospitals(hospital_code,hospital_name,city,network_status) VALUES(?,?,?,?)", [
                ("HSP-01","Sunrise Multispeciality","Hyderabad","Network"),
                ("HSP-02","City Care Hospital","Secunderabad","Network"),
                ("HSP-03","Green Valley Clinic","Warangal","Non-network")
            ])
            con.executemany("INSERT INTO dependents(customer_id,full_name,relationship,date_of_birth) VALUES(?,?,?,?)", [
                (1,"Anaya Mehta","Daughter","2015-06-18"),(2,"Rohan Sharma","Spouse","1985-02-09")
            ])
            con.executemany("INSERT INTO policies(policy_number,customer_id,plan_id,start_date,end_date,sum_insured,status) VALUES(?,?,?,?,?,?,?)", [
                ("POL-2026-001",1,1,"2026-01-01","2026-12-31",500000,"Active"),
                ("POL-2026-002",2,2,"2026-04-01","2027-03-31",1000000,"Active"),
                ("POL-2025-019",3,1,"2025-01-01","2025-12-31",500000,"Expired")
            ])
            con.executemany("INSERT INTO premium_payments(policy_id,payment_date,amount,payment_method,reference_no) VALUES(?,?,?,?,?)", [
                (1,"2026-01-01",8500,"UPI","PREM-REF-1001"),
                (2,"2026-04-01",14500,"Bank Transfer","PREM-REF-1002")
            ])
            con.executemany("INSERT INTO claims(claim_number,policy_id,hospital_id,claim_date,amount_claimed,description,status) VALUES(?,?,?,?,?,?,?)", [
                ("CLM-2026-001",1,1,"2026-09-12",68000,"Hospitalization and diagnostic care","Pending"),
                ("CLM-2026-002",2,2,"2026-09-20",125000,"Planned surgical procedure","Under Review"),
                ("CLM-2025-011",3,3,"2025-11-14",42000,"Treatment under expired policy","Rejected")
            ])
            con.executemany("INSERT INTO treatments(claim_id,treatment_name,treatment_date,cost,notes) VALUES(?,?,?,?,?)", [
                (1,"Diagnostic tests","2026-09-12",8500,"Sample record"),(1,"In-patient care","2026-09-13",59500,"Sample record")
            ])
            con.executemany("INSERT INTO claim_documents(claim_id,document_type,document_reference,received_date,verified) VALUES(?,?,?,?,?)", [
                (1,"Hospital invoice","DOC-CLM-001","2026-09-14",1),(1,"Discharge summary","DOC-CLM-002","2026-09-14",0)
            ])
            con.executemany("INSERT INTO assessments(claim_id,assessor_name,assessment_date,eligible_amount,remarks) VALUES(?,?,?,?,?)", [
                (2,"Claims Assessment Team","2026-09-22",110000,"Pending final review")
            ])
            con.executemany("INSERT INTO decisions(claim_id,decision_date,decision,reason) VALUES(?,?,?,?)", [
                (3,"2025-11-20","Rejected","Policy coverage had expired on the treatment date")
            ])
            con.executemany("INSERT INTO settlements(claim_id,settlement_date,amount,payment_reference) VALUES(?,?,?,?)", [
                (2,"2026-09-28",50000,"SET-2026-002")
            ])
            con.executemany("INSERT INTO appeals(claim_id,appeal_date,reason,status,resolution_notes) VALUES(?,?,?,?,?)", [
                (3,"2025-11-25","Request for reconsideration","Under Review","Sample appeal record")
            ])

def row_label(table, row):
    if table == "customers": return f'{row["customer_no"]} — {row["full_name"]}'
    if table == "plans": return f'{row["plan_code"]} — {row["plan_name"]}'
    if table == "policies": return f'{row["policy_number"]} (ID {row["id"]})'
    if table == "hospitals": return f'{row["hospital_code"]} — {row["hospital_name"]}'
    if table == "claims": return f'{row["claim_number"]} (ID {row["id"]})'
    if table == "invoices": return f'Invoice {row["id"]}'
    return f'{table[:-1].title()} #{row["id"]}'

def label_for(table, value, con):
    row = con.execute(f"SELECT * FROM {table} WHERE id=?", (value,)).fetchone()
    if not row: return value
    return row_label(table, row)

def get_rows(module, search=""):
    conf = MODULES[module]
    with connect() as con:
        query = f'SELECT * FROM "{conf["table"]}"'
        params = []
        if search:
            searchable = [f[0] for f in conf["fields"] if not f[2].startswith("select:") and not f[2].startswith("options:")]
            if searchable:
                query += " WHERE " + " OR ".join([f'CAST("{c}" AS TEXT) LIKE ?' for c in searchable])
                params = [f"%{search}%"] * len(searchable)
        query += " ORDER BY id DESC LIMIT 200"
        rows = con.execute(query, params).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            for col in conf["columns"]:
                if col.endswith("_id"):
                    ref = col[:-3]
                    table_name = {
                        "customer":"customers","plan":"plans","policy":"policies","hospital":"hospitals","claim":"claims"
                    }.get(ref)
                    if table_name:
                        item[col + "_label"] = label_for(table_name, item[col], con)
            out.append(item)
        return out

def choices_for(field_type, con):
    if field_type.startswith("select:"):
        table_name = field_type.split(":",1)[1]
        rows = con.execute(f'SELECT * FROM "{table_name}" ORDER BY id DESC').fetchall()
        return [(r["id"], row_label(table_name, r)) for r in rows]
    if field_type.startswith("options:"):
        return [(v, v) for v in field_type.split(":",1)[1].split("|")]
    return []

def validate_and_insert(module, form):
    conf = MODULES[module]
    values, cols = [], []
    for key, label, typ, required in conf["fields"]:
        value = form.get(key, "").strip()
        if required and not value:
            raise ValueError(f"{label} is required.")
        if not value:
            value = None
        if typ == "number" and value is not None:
            try: value = float(value)
            except ValueError: raise ValueError(f"{label} must be a number.")
            if value < 0: raise ValueError(f"{label} cannot be negative.")
        if typ.startswith("select:") and value is not None:
            value = int(value)
        if typ == "date" and value:
            try: datetime.strptime(value, "%Y-%m-%d")
            except ValueError: raise ValueError(f"{label} must be a valid date.")
        cols.append(key); values.append(value)

    with connect() as con:
        if module == "policies":
            if values[4] < values[3]:
                raise ValueError("Policy end date must be on or after its start date.")
        if module == "claims":
            policy_id = int(form["policy_id"])
            policy = con.execute("SELECT * FROM policies WHERE id=?", (policy_id,)).fetchone()
            if not policy:
                raise ValueError("Select an existing policy.")
            claim_date = form["claim_date"]
            if policy["status"] != "Active" or not (policy["start_date"] <= claim_date <= policy["end_date"]):
                raise ValueError("Claims require an active policy that covers the claim date.")
        if module == "treatments":
            claim = con.execute("""SELECT c.claim_date,p.start_date,p.end_date,p.status
                FROM claims c JOIN policies p ON p.id=c.policy_id WHERE c.id=?""",(int(form["claim_id"]),)).fetchone()
            if not claim: raise ValueError("Select an existing claim.")
            treatment_date = form["treatment_date"]
            # Treatment dates must always fall within the linked policy's validity period.
            if not (claim["start_date"] <= treatment_date <= claim["end_date"]):
                raise ValueError("Treatment date must fall within the policy validity period.")
        if module == "settlements":
            claim_id = int(form["claim_id"])
            claim = con.execute("""SELECT c.amount_claimed,p.sum_insured
                FROM claims c JOIN policies p ON p.id=c.policy_id WHERE c.id=?""",(claim_id,)).fetchone()
            if not claim: raise ValueError("Select an existing claim.")
            prior = con.execute("SELECT COALESCE(SUM(amount),0) FROM settlements WHERE claim_id=?",(claim_id,)).fetchone()[0]
            amount = float(form["amount"])
            if amount + prior > min(claim["amount_claimed"], claim["sum_insured"]):
                raise ValueError("Settlement exceeds the claim amount or policy sum insured.")
        if module == "premium_payments":
            if float(form["amount"]) <= 0: raise ValueError("Premium payment must be greater than zero.")
        placeholders = ",".join(["?"]*len(cols))
        con.execute(f'INSERT INTO "{conf["table"]}" ({",".join(cols)}) VALUES ({placeholders})', values)
        if module == "decisions":
            decision = form.get("decision")
            status = {"Approved":"Approved","Rejected":"Rejected","More Information Required":"Under Review"}.get(decision,"Pending")
            con.execute("UPDATE claims SET status=? WHERE id=?", (status, int(form["claim_id"])))
        if module == "settlements":
            con.execute("UPDATE claims SET status='Settled' WHERE id=?", (int(form["claim_id"]),))
        if module == "appeals":
            con.execute("UPDATE claims SET status='Appealed' WHERE id=?", (int(form["claim_id"]),))

@app.context_processor
def inject_globals():
    return {"modules": MODULES, "current_year": date.today().year}

@app.route("/")
def dashboard():
    with connect() as con:
        stats = {
            "customers": con.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "active_policies": con.execute("SELECT COUNT(*) FROM policies WHERE status='Active' AND start_date<=? AND end_date>=?", (date.today().isoformat(), date.today().isoformat())).fetchone()[0],
            "claims_pending": con.execute("SELECT COUNT(*) FROM claims WHERE status IN ('Pending','Under Review')").fetchone()[0],
            "settled_total": con.execute("SELECT COALESCE(SUM(amount),0) FROM settlements").fetchone()[0],
        }
        recent = con.execute("""SELECT c.claim_number, c.claim_date, c.amount_claimed, c.status,
                    cu.full_name, h.hospital_name
                    FROM claims c JOIN policies p ON p.id=c.policy_id
                    JOIN customers cu ON cu.id=p.customer_id
                    JOIN hospitals h ON h.id=c.hospital_id
                    ORDER BY c.id DESC LIMIT 6""").fetchall()
        status_rows = con.execute("SELECT status,COUNT(*) AS count FROM claims GROUP BY status ORDER BY count DESC").fetchall()
        reports = con.execute("""SELECT p.policy_number, cu.full_name, pl.plan_name, p.end_date, p.sum_insured
            FROM policies p JOIN customers cu ON cu.id=p.customer_id JOIN plans pl ON pl.id=p.plan_id
            WHERE p.status='Active' AND p.end_date>=? ORDER BY p.end_date LIMIT 5""",(date.today().isoformat(),)).fetchall()
    return render_template("dashboard.html", stats=stats, recent=recent, status_rows=status_rows, active_policies=reports)

@app.route("/module/<module>", methods=["GET","POST"])
def module_page(module):
    if module not in MODULES: abort(404)
    conf = MODULES[module]
    if request.method == "POST":
        try:
            validate_and_insert(module, request.form)
            flash(f'{conf["singular"]} saved successfully.', "success")
            return redirect(url_for("module_page", module=module))
        except (ValueError, sqlite3.IntegrityError, sqlite3.Error) as e:
            message = str(e)
            if isinstance(e, sqlite3.IntegrityError):
                message = "Could not save. Check unique values and related records; a duplicate or invalid reference may already exist."
            flash(message, "error")
    with connect() as con:
        field_data = []
        for key, label, typ, required in conf["fields"]:
            field_data.append({"key":key,"label":label,"type":typ,"required":required,"choices":choices_for(typ, con)})
    rows = get_rows(module, request.args.get("q",""))
    return render_template("module.html", module_key=module, conf=conf, field_data=field_data, rows=rows, search=request.args.get("q",""))

@app.route("/reports")
def reports():
    with connect() as con:
        claim_summary = con.execute("SELECT status, COUNT(*) AS count, COALESCE(SUM(amount_claimed),0) AS amount FROM claims GROUP BY status ORDER BY status").fetchall()
        premium_summary = con.execute("""SELECT p.policy_number, cu.full_name, COALESCE(SUM(pp.amount),0) AS paid,
            p.sum_insured, p.status FROM policies p JOIN customers cu ON cu.id=p.customer_id
            LEFT JOIN premium_payments pp ON pp.policy_id=p.id GROUP BY p.id ORDER BY paid DESC""").fetchall()
        hospital_summary = con.execute("""SELECT h.hospital_name, COUNT(c.id) AS claim_count,
            COALESCE(SUM(c.amount_claimed),0) AS claim_value
            FROM hospitals h LEFT JOIN claims c ON c.hospital_id=h.id GROUP BY h.id ORDER BY claim_count DESC""").fetchall()
        approval = con.execute("""SELECT COUNT(*) AS total,
            SUM(CASE WHEN status IN ('Approved','Settled') THEN 1 ELSE 0 END) AS approved
            FROM claims""").fetchone()
        approval_rate = round((approval["approved"] or 0) * 100 / approval["total"], 1) if approval["total"] else 0
        settlement_total = con.execute("SELECT COALESCE(SUM(amount),0) FROM settlements").fetchone()[0]
        premium_due = con.execute("""SELECT p.policy_number,cu.full_name,p.end_date,pl.annual_premium,
            COALESCE(SUM(pp.amount),0) AS paid
            FROM policies p JOIN customers cu ON cu.id=p.customer_id JOIN plans pl ON pl.id=p.plan_id
            LEFT JOIN premium_payments pp ON pp.policy_id=p.id
            GROUP BY p.id HAVING paid < pl.annual_premium""").fetchall()
    return render_template("reports.html", claim_summary=claim_summary, premium_summary=premium_summary,
        hospital_summary=hospital_summary, approval_rate=approval_rate, settlement_total=settlement_total, premium_due=premium_due)

@app.route("/search")
def global_search():
    q = request.args.get("q","").strip()
    results = []
    if q:
        with connect() as con:
            results = con.execute("""SELECT c.claim_number,c.claim_date,c.status,c.amount_claimed,
                cu.full_name,p.policy_number,h.hospital_name
                FROM claims c JOIN policies p ON p.id=c.policy_id
                JOIN customers cu ON cu.id=p.customer_id JOIN hospitals h ON h.id=c.hospital_id
                WHERE c.claim_number LIKE ? OR cu.full_name LIKE ? OR p.policy_number LIKE ?
                ORDER BY c.id DESC LIMIT 50""",(f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    return render_template("search.html", q=q, results=results)

@app.route("/health")
def health():
    return {"status":"ok","database":str(DB_PATH.name)}

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
