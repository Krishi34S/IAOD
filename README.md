# Invoice Anomaly & Overbilling Detector (IAOD)

> **CSMC502 Software Engineering Lab**  
> **Department of Computer Science & Engineering, Tezpur University**  
> **Project No. 22**: Invoice Anomaly & Overbilling Detection  
> **Supervised by**: Dr. Dhruba K. Bhattacharyya & Dr. Swarup Roy  
> **Team Members**:  
> - Krishi Pratim Sarma (CSM25009)  
> - Abhisekh Panjiyar (CSM25015)  
> - Kishor Kashyap (CSM25043)  

---

## 1. Executive Summary & Problem Statement

Organizations and procurement departments process hundreds of invoices monthly from multiple vendors. Manual auditing is error-prone, labor-intensive, and often misses:
1. **Mathematical Discrepancies**: Subtle errors where quantity multiplied by unit price does not equal the billed line total.
2. **Hidden Overbilling**: Discrepancies between the recalculated subtotal/tax/discount and the final billed total.
3. **Duplicate Billing**: Accidental or fraudulent double-submission of identical invoices or repeated line items within a single invoice.
4. **Price Inflation / Unfair Spikes**: Unit prices significantly higher than pre-negotiated benchmark catalog prices or historical purchase averages.
5. **Tax & Discount Mismatches**: Incorrect GST/VAT percentages or invalid discount deductions applied.

**IAOD (Invoice Anomaly & Overbilling Detector)** is an enterprise-grade, rule-based web platform designed to automate invoice reconciliation. It provides instant anomaly classification, risk severity scoring, discrepancy computation, and automated downloadable PDF audit certification reports without altering existing vendor accounting systems.

---

## 2. Alignment with Evaluation Criteria (50 Marks)

| Evaluation Component | Marks | System Implementation & Evidence |
| :--- | :---: | :--- |
| **Problem, Innovation & Commercial Need** | **10** | Solves preventable financial loss in procurement; distinct from generic CRUD apps; targets finance teams, university procurement departments, and MSMEs; offers explainable rule verification rather than opaque black-box AI. |
| **Software Engineering & Architecture** | **10** | Strict 3-layer architecture (Presentation, Application/Business Logic, Data Layer); Context DFD Level 0, Level 1; formal Entity-Relationship (ER) model; REST API design; strict separation of concerns and modular rule engine (`BaseDetectionRule`). |
| **Coding & Technical Depth** | **15** | Substantial Python Flask backend; customizable anomaly rule engine; arithmetic verification; benchmark catalog comparison; historical purchase matching; multi-format parser (PDF via PyPDF, CSV styles A/B, JSON); secure PBKDF2 authentication with 4 distinct roles (Admin, Finance Staff, Management, Organisation User). |
| **Testing, Validation & Demonstration** | **10** | Comprehensive automated test suite (`tests/`) covering 22 test scenarios across all functional requirements with 100% pass rate; realistic test datasets (`data/sample_invoices/`); seeded database with instant evaluator scenarios. |
| **Commercialization Evidence** | **5** | Productized SaaS model with tier pricing; downloadable audit PDF reports; role-tailored dashboards; pilot deployment readiness for institutional procurement offices. |

---

## 3. System Architecture & Design

### 3.1 Three-Layer Architectural Model
```
┌─────────────────────────────────────────────────────────────┐
│                   1. PRESENTATION LAYER                     │
│  Responsive Web UI • Dashboard • Multi-Format Ingestion     │
│  Line-Item Builder • Audit Detail View • PDF Reports        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼──────────────────────────────┐
│             2. APPLICATION & BUSINESS LOGIC LAYER           │
│  ┌───────────────────────┐       ┌────────────────────────┐  │
│  │ Authentication & RBAC │       │ Ingestion & Validation │  │
│  └───────────────────────┘       └────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Calculation Verification Engine           │  │
│  │   • Line Totals (Qty × Unit Price) • Expected Subtotal │  │
│  │   • Tax Verification • Expected Total vs Billed Total  │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Modular Anomaly Detection Engine             │  │
│  │   • Overbilling Rule         • Duplicate Invoice Rule  │  │
│  │   • Duplicate Item Rule      • Price Anomaly Rule      │  │
│  │   • Tax & Discount Rule      • Severity Risk Scoring   │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │    PDF Audit Report Generator (ReportLab Platypus)     │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │ SQLite / MySQL Relational Schema
┌──────────────────────────────▼──────────────────────────────┐
│                       3. DATA LAYER                         │
│  USERS • INVOICES • INVOICE_ITEMS • REFERENCE_PRICES        │
│  ANOMALIES • ANALYSIS_REPORTS                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Relational Database Schema (`schema.sql`)
- **`users`**: `user_id`, `name`, `email`, `password_hash`, `role` (`admin`, `finance_staff`, `management`, `user`).
- **`invoices`**: `invoice_id`, `invoice_number`, `vendor`, `invoice_date`, `billed_subtotal`, `tax_rate`, `tax_amount`, `discount_amount`, `billed_total`, `expected_subtotal`, `expected_tax`, `expected_total`, `total_discrepancy`, `status` (`NORMAL`, `SUSPICIOUS`, `PENDING`), `risk_score` (0–100), `user_id`.
- **`invoice_items`**: `item_id`, `invoice_id`, `description`, `category`, `quantity`, `unit_price`, `line_total`, `expected_line_total`.
- **`reference_prices`**: `reference_id`, `item_name`, `category`, `expected_unit_price`, `tolerance_percent`, `unit`.
- **`anomalies`**: `anomaly_id`, `invoice_id`, `item_id`, `anomaly_type`, `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `affected_value`, `expected_value`, `difference`, `explanation`.
- **`analysis_reports`**: `report_id`, `invoice_id`, `user_id`, `summary`, `total_anomalies`, `report_file`, `generated_at`.

---

## 4. Requirements Traceability Matrix

| SRS Req | Module / File | Description & Verification | Status |
| :--- | :--- | :--- | :---: |
| **FR-1.1 – FR-1.4** | `app/auth/` | Account creation, PBKDF2 login, RBAC (`@role_required`), Admin role management | ✅ Verified |
| **FR-2.1 – FR-2.4** | `app/core/parsers.py`<br>`app/core/validator.py` | Multi-format upload (PDF, CSV, JSON), manual form builder, field validation & error reporting | ✅ Verified |
| **FR-3.1 – FR-3.4** | `app/core/calculation_engine.py` | Item line verification ($Qty \times Unit Price$), subtotal summing, comparison with billed total, discrepancy identification | ✅ Verified |
| **FR-4.1 – FR-4.3** | `app/core/rules.py` (`OverbillingRule`) | Flags $Billed > Expected$, calculates monetary excess, generates human-readable explanation | ✅ Verified |
| **FR-5.1** | `DuplicateInvoiceRule` | Flags duplicate invoices matching vendor & invoice number or vendor, date & total | ✅ Verified |
| **FR-5.2** | `DuplicateItemRule` | Flags repeated line items inside the same invoice | ✅ Verified |
| **FR-5.3 – FR-5.4** | `PriceAnomalyRule` | Compares item unit price against benchmark reference catalog and historical purchases; flags deviations exceeding tolerance | ✅ Verified |
| **FR-6.1 – FR-6.3** | `TaxAndDiscountRule` | Recalculates expected tax from rate & taxable base, checks discount bounds, flags mismatches | ✅ Verified |
| **FR-7.1 – FR-7.5** | `app/core/anomaly_engine.py`<br>`app/services/report_service.py` | Severity assignment (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), risk scoring (0-100), downloadable PDF, JSON & CSV reports | ✅ Verified |
| **FR-8.1 – FR-8.4** | `app/views.py`<br>`app/api/dashboard.py` | Audited invoice history, query search, status filter, KPI cards, anomaly breakdown & severity charts | ✅ Verified |

---

## 5. Anomaly Detection & Risk Scoring Engine

The anomaly detection engine calculates a composite risk score between 0 and 100 based on severity weights:
- **`CRITICAL`** (+40 pts): Duplicate invoice, Overbilling $\ge$ 20% or $\ge$ ₹10,000, Price spike $\ge$ 50% above benchmark.
- **`HIGH`** (+25 pts): Duplicate item, Overbilling $\ge$ 5% or $\ge$ ₹1,000, Price spike $\ge$ 25% above benchmark, Arithmetic line mismatch.
- **`MEDIUM`** (+15 pts): Minor overbilling, Price spike within tolerance excess, Tax calculation mismatch.
- **`LOW`** (+5 pts): Minor discrepancies.

**Audit Status Assignment**:
- **`NORMAL`**: Risk score = 0, no anomalies detected.
- **`SUSPICIOUS`**: Risk score > 0 or any anomaly detected (marked for human review).

---

## 6. REST API Reference

| Endpoint | Method | Role | Description |
| :--- | :---: | :---: | :--- |
| `/api/auth/register` | `POST` | Public | Register new user account |
| `/api/auth/login` | `POST` | Public | Authenticate user and initialize session |
| `/api/auth/logout` | `POST` | Authenticated | Terminate user session |
| `/api/auth/me` | `GET` | Authenticated | Get current authenticated user profile |
| `/api/invoices` | `POST` | Authenticated | Upload invoice file (PDF/CSV/JSON) or submit manual payload |
| `/api/invoices` | `GET` | Authenticated | List all invoices with search (`q`), `status`, and `vendor` filters |
| `/api/invoices/<id>` | `GET` | Authenticated | Retrieve full invoice details, line items, and anomalies |
| `/api/invoices/<id>/analyze` | `POST` | Authenticated | Trigger re-analysis through the anomaly detection engine |
| `/api/invoices/<id>/anomalies` | `GET` | Authenticated | Retrieve list of detected anomalies for an invoice |
| `/api/reports/<id>/download` | `GET` | Authenticated | Download audit certification report in `pdf`, `json`, or `csv` |
| `/api/dashboard/summary` | `GET` | Authenticated | Retrieve dashboard KPI counts, total overbilling, and charts data |
| `/api/reference-prices` | `GET` | Authenticated | View benchmark reference price catalog |
| `/api/reference-prices` | `POST` | Admin / Finance | Add new benchmark reference item |
| `/api/reference-prices/<id>`| `PUT` | Admin / Finance | Update benchmark item price or tolerance |
| `/api/reference-prices/<id>`| `DELETE` | Admin / Finance | Delete reference price from catalog |
| `/api/admin/users` | `GET` | Admin | List all registered user accounts |
| `/api/admin/users/<id>/role` | `PUT` | Admin | Update user access role |

---

## 7. Quick Start & Execution Guide

### 7.1 Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Windows / Linux / macOS

### 7.2 Installation
```bash
# Clone the repository
git clone https://github.com/Krishi-Sarma/IAOD.git
cd IAOD

# Install dependencies
pip install -r requirements.txt
```

### 7.3 Seed Demo Dataset
Populate the database with baseline benchmark reference prices and realistic audit test cases:
```bash
python data/seed_data.py
```

### 7.4 Run Automated Test Suite
Execute the 22 automated unit and integration tests:
```bash
python -m unittest discover tests
```

### 7.5 Launch Web Application
```bash
python run.py
```
Open your browser at **`http://127.0.0.1:5000`**.

---

## 8. Evaluator Demo Accounts & Scenarios

The login page includes **one-click demo sign-in buttons** for quick evaluation:

| Role | Email | Password | Permissions & Views |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@iaod.local` | `Admin@123` | Full system access, User Role Management, Benchmark Catalog |
| **Finance Staff** | `finance@iaod.local` | `Finance@123` | Audit reviews, Benchmark Catalog configuration |
| **Management** | `management@iaod.local` | `Manage@123` | Executive KPI dashboard, overbilling savings, report downloads |
| **Organisation User** | `user@iaod.local` | `User@123` | Invoice submission (Upload & Manual), history view |

### Pre-Configured Test Scenarios (Available in "+ New Audit" Tab)
1. **Compliant Clean Invoice**: Dell Latitude Laptops matching benchmark price and verified 18% tax ($Score = 0$, Status: `NORMAL`).
2. **Overbilling Detection**: Office Chairs billed at ₹36,000 instead of calculated ₹30,090 (+₹5,910 excess flagged).
3. **Price Spike**: Cisco Switch billed at ₹42,000 (+50% above benchmark reference price of ₹28,000).
4. **Line Item Math Error**: 5 boxes of paper billed at ₹9,500 instead of $5 \times 1,400 = 7,000$.

---

## 9. Commercialization & SaaS Deployment Roadmap

1. **Target Customers**: Higher education institutions (universities, colleges), MSMEs, hospital procurement departments, and government offices where AP clerks manually cross-check vendor bills against quotations.
2. **Value Proposition & ROI**: Immediate savings by stopping overbilling prior to payment disbursement. A single prevented price spike (e.g. ₹18,000 on laptop purchases) delivers immediate return on software investment.
3. **Commercial Business Model**:
   - **Starter / Institutional Self-Hosted**: Free for educational and non-profit procurement teams up to 50 invoices/month.
   - **Professional SaaS**: ₹4,999/month for unlimited invoices, PDF audit exports, and benchmark price catalogs.
   - **Enterprise**: Custom deployment with ERP/SAP integration and automated vendor quotation sync.
