# HealthSure — Health Insurance Policy & Claims Management System

A local Python + Flask + SQLite DBMS project based on the supplied Project 53 brief. It demonstrates policy issue, dependent entry, premium collection, claim submission, document tracking, assessment, decisions, settlement, appeals and SQL reports.

## Run on Windows

1. Extract this ZIP.
2. Open the extracted `HealthSure_Insurance_Claims_App` folder in VS Code.
3. Open Terminal in that folder.
4. (Recommended) Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Start the app:

   ```powershell
   python app.py
   ```

7. Open the local URL printed in the terminal, normally `http://127.0.0.1:5000`.

The database file `health_insurance.db` is created automatically next to `app.py`, and fictional sample data is inserted the first time. Use DB Browser for SQLite to inspect its tables. Keep the terminal running while presenting; press `Ctrl+C` to stop the server.

## Modules
- Overview dashboard and reports
- Customers and dependents
- Insurance plans and policies
- Premium payments and hospitals
- Claims, treatments and claim documents
- Assessments, decisions, settlements and appeals
- Global search by claim number, policy number or customer name

## Business rules demonstrated
- Policy number, customer number, plan code, hospital code, claim number and payment references are unique.
- Claims require an active policy that covers the claim date.
- Policy dates must be valid and sum insured must be positive.
- Settlement totals cannot exceed the lower of the claim amount and policy sum insured.
- Foreign keys and CHECK constraints protect database integrity.
- Frequently searched policy and claim fields are indexed.

## Notes
- All names and records are fictional sample data.
- This is an academic demonstration, not a production system for real medical or insurance information.
- For a fresh database, stop the app and delete `health_insurance.db`; restarting will recreate and reseed it.
