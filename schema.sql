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
