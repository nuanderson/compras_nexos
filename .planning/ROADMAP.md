# Roadmap: ComprasNexos

**Project:** ComprasNexos — Sistema de Gestão de Compras
**Mode:** MVP Vertical
**Granularity:** Standard
**Coverage:** 39/39 v1 requirements mapped

---

## Phases

- [ ] **Phase 1: Foundation** - Custom user model, login, unit management — database and auth foundation
- [ ] **Phase 2: Requisitions & Approvals** - Full purchase requisition workflow with configurable 2-level approval
- [ ] **Phase 3: Suppliers & Inventory** - Supplier directory with CNPJ validation and per-unit stock management
- [ ] **Phase 4: Quotations (RFQ)** - RFQ creation, multi-supplier quote entry, price comparison, winner selection
- [ ] **Phase 5: Reports & Dashboard** - Cross-app KPI dashboard, spending reports, and PDF export

---

## Phase Details

### Phase 1: Foundation
**Goal:** Users can authenticate, and the Admin can manage accounts and organizational units
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, UNIT-01, UNIT-02, UNIT-03
**Success Criteria** (what must be TRUE):
  1. User can log in with email and password and remain authenticated across browser refreshes
  2. User can request a password reset and receive a reset link by email
  3. Admin can create, edit, and deactivate user accounts via the admin panel
  4. Admin can assign one of five roles (Solicitante, Gestor, Comprador, Diretor, Admin) to each user
  5. Admin can create organizational units and link users to them; each user has a default unit pre-selected when opening a requisition
**Plans:** TBD
**UI hint:** yes

---

### Phase 2: Requisitions & Approvals
**Goal:** Solicitantes can submit purchase requisitions and the full 2-level approval workflow runs end-to-end
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** REQ-01, REQ-02, REQ-03, REQ-04, APROV-01, APROV-02, APROV-03, APROV-04, APROV-05, APROV-06
**Success Criteria** (what must be TRUE):
  1. Solicitante can open a requisition with description, category, estimated value, justification, and unit — and see its status update in real time on the tracking page
  2. Gestor receives an email notification when a new requisition awaits their review, and can approve or reject it from their queue (rejection requires a mandatory reason)
  3. Diretor sees only requisitions already approved by the Gestor and can apply the 2nd-level decision; rejected requisitions at either level are permanently closed with an audit trail
  4. Every approval/rejection event is recorded with actor, timestamp, and reason — visible to the Solicitante on their requisition detail page
  5. Admin can configure approval thresholds by value via the admin panel without a code deployment
**Plans:** TBD
**UI hint:** yes

---

### Phase 3: Suppliers & Inventory
**Goal:** Buyers can manage a searchable supplier directory and each unit can track its own inventory
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** FORN-01, FORN-02, FORN-03, FORN-04, FORN-05, EST-01, EST-02, EST-03, EST-04, EST-05, EST-06
**Success Criteria** (what must be TRUE):
  1. Buyer can register a supplier with CNPJ (validated by python-stdnum including the July 2026 alphanumeric format), company name, email, and phone — duplicates are rejected at the database level
  2. Buyer can assign configurable categories to suppliers and filter/search the directory by name, CNPJ, or category
  3. Buyer can deactivate a supplier without losing historical data, and reactivate them later
  4. Solicitante can add stock items to their unit with name, unit of measure, current quantity, and minimum threshold — items below the minimum are visually highlighted
  5. Each unit sees only its own inventory; Buyer and Admin see a consolidated view across all units
**Plans:** TBD
**UI hint:** yes

---

### Phase 4: Quotations (RFQ)
**Goal:** Buyers can run a full RFQ cycle — from creating the request to selecting a winner — for any approved requisition
**Mode:** mvp
**Depends on:** Phase 2, Phase 3
**Requirements:** COT-01, COT-02, COT-03, COT-04
**Success Criteria** (what must be TRUE):
  1. Buyer can create an RFQ linked to an approved requisition (one RFQ per requisition enforced by the system)
  2. Buyer can register quotes from multiple suppliers with unit price, delivery time, and payment conditions — and add or remove lines without a full-page reload
  3. System displays a side-by-side price comparison that automatically highlights the lowest-price quote and shows the percentage delta between each supplier and the winner
  4. Buyer can select a winning supplier with a mandatory written justification; the selection is immutable once saved and the full quote history remains accessible for audit
**Plans:** TBD
**UI hint:** yes

---

### Phase 5: Reports & Dashboard
**Goal:** All roles can view real-time KPIs and spending reports, and export formatted PDFs
**Mode:** mvp
**Depends on:** Phase 2, Phase 3, Phase 4
**Requirements:** REL-01, REL-02, REL-03, REL-04, UNIT-04
**Success Criteria** (what must be TRUE):
  1. Dashboard displays live KPIs — open requisitions, active RFQs, current-month spend, and active suppliers — populated from real transaction data
  2. Spending report shows totals by category and period, filterable by unit
  3. Requisition status panel shows all requisitions with filters for status and unit
  4. Any report can be exported as a formatted PDF (ReportLab Platypus layout) directly from the browser
**Plans:** TBD
**UI hint:** yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/? | Not started | - |
| 2. Requisitions & Approvals | 0/? | Not started | - |
| 3. Suppliers & Inventory | 0/? | Not started | - |
| 4. Quotations (RFQ) | 0/? | Not started | - |
| 5. Reports & Dashboard | 0/? | Not started | - |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| AUTH-01 | Phase 1 |
| AUTH-02 | Phase 1 |
| AUTH-03 | Phase 1 |
| AUTH-04 | Phase 1 |
| AUTH-05 | Phase 1 |
| AUTH-06 | Phase 1 |
| UNIT-01 | Phase 1 |
| UNIT-02 | Phase 1 |
| UNIT-03 | Phase 1 |
| REQ-01 | Phase 2 |
| REQ-02 | Phase 2 |
| REQ-03 | Phase 2 |
| REQ-04 | Phase 2 |
| APROV-01 | Phase 2 |
| APROV-02 | Phase 2 |
| APROV-03 | Phase 2 |
| APROV-04 | Phase 2 |
| APROV-05 | Phase 2 |
| APROV-06 | Phase 2 |
| FORN-01 | Phase 3 |
| FORN-02 | Phase 3 |
| FORN-03 | Phase 3 |
| FORN-04 | Phase 3 |
| FORN-05 | Phase 3 |
| EST-01 | Phase 3 |
| EST-02 | Phase 3 |
| EST-03 | Phase 3 |
| EST-04 | Phase 3 |
| EST-05 | Phase 3 |
| EST-06 | Phase 3 |
| COT-01 | Phase 4 |
| COT-02 | Phase 4 |
| COT-03 | Phase 4 |
| COT-04 | Phase 4 |
| REL-01 | Phase 5 |
| REL-02 | Phase 5 |
| REL-03 | Phase 5 |
| REL-04 | Phase 5 |
| UNIT-04 | Phase 5 |

**Total mapped: 39/39 v1 requirements**

---

*Roadmap created: 2026-06-10*
*Last updated: 2026-06-10 after initial creation*
