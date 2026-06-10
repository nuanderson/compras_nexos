# Feature Landscape: Procurement Management System

**Domain:** Corporate procurement — purchase requisitions, multi-level approvals, supplier management, RFQ, price comparison, reporting
**Project:** ComprasNexos
**Researched:** 2026-06-10
**Confidence:** HIGH for procurement domain patterns (stable, well-established industry). MEDIUM for Brazil-specific NFe/fiscal integration nuances (regulatory details change; verify with fiscal consultant before Phase 2+).

---

## Table Stakes

Features users expect in any procurement system. Missing any of these causes immediate rejection or distrust.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Purchase requisition form with status tracking | Core workflow entry point — every procurement tool has this | Low | Must show current status prominently (draft / pending approval / approved / rejected / in RFQ) |
| Real-time status visibility for requester | Requesters won't trust the system if they have to ask where their request is | Low | A simple status badge + timeline log per requisition is enough; no need for live push |
| Sequential multi-level approval with audit trail | Two-level approvals (manager then director) is the norm in any company with controls | Medium | Rejecting at level 1 must skip level 2; each approval action must record who, when, and any comment |
| Approval threshold configuration (alçadas) | Every company has different dollar limits; hardcoded values cause immediate friction | Medium | Admin must be able to set value ranges for each approval level without a code change |
| Supplier directory with contact info | Buyers need a searchable list of known suppliers | Low | At minimum: company name, CNPJ, phone, email, categories served |
| CNPJ field and basic format validation | Brazilian users expect this — it's the primary business identifier | Low | Validate 14-digit format and check digit algorithm; not just regex — the check digits must compute correctly |
| Supplier categorization | Allows filtering "which suppliers can quote on this type of purchase" | Low | Configurable categories (e.g., IT, Facilities, Marketing); many-to-many with suppliers |
| RFQ creation linked to an approved requisition | A quote without a backing requisition is uncontrolled spending — users know this | Medium | RFQ must reference the originating requisition; buyer selects which suppliers to invite |
| Multi-supplier quotation entry | The entire value of an RFQ is comparing at least 2–3 prices | Low | Buyer manually enters each supplier's response (price, lead time, payment terms, notes) |
| Side-by-side price comparison view | This is THE moment of decision — if it's hard to read, the system fails at its core job | Medium | Highlight lowest price, show delta vs. selected price, allow column sorting |
| Winner selection with mandatory justification | Audit requirement — selecting the cheapest is not always the right call | Low | Free-text justification field required before confirming winner; stored permanently |
| RFQ and quotation history for audit | Procurement is auditable by nature — all decisions must be traceable | Low | Immutable log: who created RFQ, who entered each quote, who selected winner, when |
| Dashboard KPIs | Managers need a snapshot at a glance; nothing else signals "this is a real system" | Medium | At minimum: open requisitions, pending approvals, active RFQs, spend this month |
| Spend-by-category report | The #1 report every procurement manager asks for | Medium | Filterable by date range and category; should drive cost-reduction discussions |
| PDF export of reports | Brazilian corporate culture expects printable, signable documents | Medium | ReportLab is already chosen; format must look professional, not like a raw table dump |
| Role-based access (RBAC) | Users must see only what their role permits | Medium | 5 roles defined: Solicitante, Gestor, Comprador, Diretor, Admin — each with distinct view/action permissions |
| Email notifications on approval actions | Approvers forget to check a dashboard; email is the trigger | Medium | At minimum: notify approver when action is required; confirmations to requester when approved/rejected |
| BRL currency display throughout | All monetary values must display as R$ with comma decimal separator | Low | Django's `intcomma` or custom template filter; never show $, USD, or dot-decimal to users |

---

## Differentiators

Features that go beyond baseline expectations. Users don't demand them upfront, but they drive satisfaction and adoption.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Supplier performance scoring after purchase | Turns ad-hoc "that supplier was late" into structured data; buyers can filter RFQs by rating | Medium | Post-purchase evaluation form: delivery time, quality, documentation, communication — each 1–5; stored per transaction, averaged over time |
| Spend vs. approved budget indicator | Shows at a glance whether a category is running over estimate | High | Requires budget configuration by category or cost center — out of scope for v1 but architecture should accommodate it |
| Savings tracking (quoted price vs. selected price delta) | Quantifies the buyer's work — "we saved R$ X this month by negotiating" | Medium | Derived from RFQ data already captured; just needs a summary view and dashboard widget |
| Requisition duplicate detection | Prevents two requesters from opening identical purchases independently | High | Fuzzy matching on description + category; too complex for v1 — flag as v2 |
| Inline approval comments visible to requester | Removes back-channel email to understand why a request was rejected | Low | Approver's rejection comment surfaces in requester's requisition detail page |
| Configurable approval routing by category | Some categories (e.g., IT equipment) may require different approvers | High | Not needed for v1 given the client's two-level model; plan the data model to support it |
| Quotation PDF/attachment upload | Buyer can attach the actual supplier quote document to each quotation entry | Medium | File storage on S3; needed for thorough audit trail — v2 candidate |
| Requisition search and filtering | As volume grows, listing all requisitions becomes unusable | Low-Medium | Filter by status, category, date range, requester; full-text search on description is valuable but can be deferred |
| Approval deadline / SLA indicator | Shows how long a requisition has been waiting for approval; triggers urgency | Medium | Simple: calculate business days since submission; flag items over N days — configurable by Admin |
| Cost center / department tagging on requisitions | Enables spend reporting by department, not just category | Low | Single-select field on requisition form; values configurable by Admin |

---

## Anti-Features

Features to deliberately NOT build for this context. Building them wastes time and creates maintenance debt.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Supplier-facing portal | Out of scope per PROJECT.md; adds auth complexity and security surface area for a 20-user internal tool | Buyer communicates via email/phone and manually records responses |
| Purchase Order (PO) PDF generation at v1 | Client hasn't validated the full workflow yet; PO format varies and requires legal review | Scope it explicitly as Phase 2 after requisition-to-payment flow is proven |
| ERP/financial system integration | Target system not yet identified; premature integration creates coupling to an unknown | Design clean internal APIs now; integrate only when ERP is selected and confirmed |
| Automated budget enforcement (block if over budget) | Client has not defined budgets by department; building this requires budget setup first | Informational spend indicators are acceptable; hard blocks require policy alignment first |
| NFe (Nota Fiscal Eletrônica) issuance or parsing | NFe is issued by the seller, not the buyer; the buyer only receives and archives it | Record supplier invoice number and date as metadata fields; do not attempt XML parsing or SEFAZ integration in v1 |
| 2FA / SSO / LDAP | Not required at this company size; adds setup complexity for users without IT support | Simple email+password login with Django's built-in auth; revisit if client moves to Microsoft 365 or Google Workspace |
| Public registration / self-service onboarding | This is an internal corporate tool; open registration is a security risk | Admin creates and manages all user accounts |
| Mobile-native app | HTMX + responsive Django templates cover the use case adequately for office users | Ensure templates are mobile-responsive as a quality requirement, not a separate product |
| AI/ML spend prediction | Way beyond scope for a greenfield v1 with no historical data | After 12+ months of data, reconsider — the data model should not preclude it |
| Real-time push notifications (WebSockets) | Email is the right notification channel; WebSockets add infrastructure complexity | HTMX polling or page refresh for status updates is sufficient |
| Workflow automation / no-code rules engine | Overkill for a two-level approval model with simple value thresholds | The Admin panel for alçadas configuration is sufficient |
| Multi-company / multi-tenant | One client, one internal system; multi-tenancy adds model complexity for zero benefit | Tenant-per-deployment is the right model |
| Inventory management | A different problem domain; procurement ≠ inventory | Scope clearly as not-procurement; link POs to inventory only post-v1 if client requests |

---

## Brazilian-Specific Considerations

### CNPJ Validation (HIGH confidence)

CNPJ is a 14-digit number (XX.XXX.XXX/XXXX-XX format). Validation requires:

1. Strip formatting to 14 raw digits.
2. Reject all-same-digit CNPJs (e.g., 11.111.111/1111-11 are invalid by rule).
3. Compute first check digit: weighted sum of first 12 digits (weights: 5,4,3,2,9,8,7,6,5,4,3,2), remainder mod 11. If remainder < 2, digit = 0; else digit = 11 - remainder.
4. Compute second check digit: same algorithm over 13 digits (weights: 6,5,4,3,2,9,8,7,6,5,4,3,2).
5. Compare computed digits against digits 13 and 14.

Use the `python-cnpj` or `validate-docbr` library rather than implementing from scratch. The `validate-docbr` library (PyPI: `validate-docbr`) covers both CPF and CNPJ and is the standard choice in the Django/Python Brazilian ecosystem.

Confidence: HIGH (CNPJ algorithm is a published federal standard, unchanged for decades).

### BRL Currency Formatting (HIGH confidence)

- Always display as `R$ 1.234,56` (dot as thousands separator, comma as decimal).
- Django's `humanize` templatetag provides `intcomma` but uses US formatting. Use a custom template filter or the `babel` library configured for `pt_BR` locale.
- Store monetary values as `DecimalField(max_digits=12, decimal_places=2)` in PostgreSQL — never as float.
- Avoid JavaScript number formatting inconsistencies: let the server render all currency values.

Confidence: HIGH (formatting standard is fixed by Brazilian banking conventions).

### NFe / Fiscal Requirements (MEDIUM confidence — verify before any fiscal feature)

For a procurement buyer (not the seller), the relevant fiscal touchpoints are:

- **NFe received**: When a supplier delivers goods or services, they issue an NFe. The buyer's obligation is to **store the DANFE** (printed/PDF version of NFe) for 5 years (Instrução Normativa RFB nº 2.138/2023 or similar — verify current regulation). The buyer does NOT issue NFe.
- **v1 scope**: Simply record the supplier invoice number (chave de acesso de 44 dígitos) and date in the quotation/order record. No XML processing needed.
- **Future scope**: If the client wants to validate received NFes, the SEFAZ public web service (`nfeStatusServico`) can be queried with the access key. Libraries like `nfelib` (Python) exist for this.
- **DANFE archiving**: Out of scope for v1 — file attachment feature covers this adequately.

Confidence: MEDIUM — NFe regulations are updated periodically by SEFAZ/Receita Federal. The general direction (buyer stores, doesn't issue) is stable, but retention periods and validation obligations should be confirmed with a fiscal accountant (contador) before building any fiscal integration feature.

### PIX / Payment Terms (LOW confidence — not in scope but worth noting)

Brazilian payment culture uses PIX (instant), boleto bancário, and 30/60/90-day terms (net 30/60/90 in BR context written as "30/60/90 dias"). Quotation forms should capture payment terms as a text/select field rather than assuming wire transfer. This affects supplier comparison but has no system integration requirement in v1.

---

## Approval Workflow Patterns: Intuitive vs. Frustrating

### What makes approval flows intuitive

1. **Approver sees everything needed on one screen**: The approval page must show — without clicking away — the requisition description, category, estimated value, requester name, date, and justification. Making the approver navigate to find context creates friction and delays.

2. **One-click approve with optional comment, mandatory comment on reject**: Approval should be fast. Rejection must require a comment so the requester knows what to fix. This asymmetry is correct UX for approval flows.

3. **Approver action is irreversible but the process can restart**: Once approved or rejected, the record is immutable. If a requester wants to fix a rejection, they open a new requisition (or the system supports a "resubmit" flow). Do not allow editing approved requisitions.

4. **Clear state machine with named states**: The status field is a strict state machine. Valid transitions:

   ```
   DRAFT → PENDING_MANAGER
   PENDING_MANAGER → PENDING_DIRECTOR (approved by manager, value requires director)
   PENDING_MANAGER → APPROVED (approved by manager, value below director threshold)
   PENDING_MANAGER → REJECTED
   PENDING_DIRECTOR → APPROVED
   PENDING_DIRECTOR → REJECTED
   APPROVED → IN_RFQ (buyer creates an RFQ against it)
   IN_RFQ → COMPLETED (buyer selects winner)
   ```

   Any status not in this list is invalid. Enforce at the model layer, not just the view.

5. **Threshold-based routing is invisible to the requester**: The system automatically routes based on value. The requester should not have to know that "above R$ X goes to the director." The workflow engine determines this.

6. **Approver notification is email-first, dashboard-second**: Email triggers action. The dashboard shows what's pending but is not the action trigger. Without email, items stall.

### What makes approval flows frustrating

1. **Ambiguous status names**: "In progress" could mean anything. Use precise labels: "Aguardando Gestor", "Aguardando Diretor", "Aprovado", "Reprovado".

2. **No explanation on rejection**: The requester submits again with the same problem. Always surface the rejection comment in the requester's view.

3. **Approval by proxy / editing after submission**: If a manager edits a requisition before approving it, the audit trail is contaminated. Approvers can only approve, reject, or comment — never edit.

4. **Parallel approvals for a sequential business process**: This client uses sequential approval (manager first, then director). Parallel approval (both notified simultaneously, either can approve) is wrong for a hierarchy-based authorization model.

5. **No pending-approval list for approver**: Approvers need a queue view: "these are the items waiting for my decision." Without this, they rely solely on email and things fall through.

---

## RFQ Best Practices: Price Comparison UI

### Data to Capture Per Quotation Entry

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Supplier (FK) | Select | Yes | From active supplier list |
| Unit price | Decimal | Yes | Per unit; system calculates total |
| Quantity | Integer | Yes | Defaults from requisition quantity |
| Total price | Decimal | Computed | quantity × unit price |
| Payment terms | Text/Select | Yes | e.g., "30 dias boleto", "À vista PIX" |
| Lead time | Integer (days) | Yes | Delivery time in business days |
| Validity date | Date | Yes | Until when the price is valid |
| Notes | Text | No | Special conditions, warranty, etc. |
| Quotation reference | Text | No | Supplier's quote number or email subject |

### Price Comparison UI Patterns That Work

1. **Table layout, not cards**: When comparing 3–5 suppliers, a horizontal table with suppliers as columns is faster to scan than individual cards. Rows are the fields above.

2. **Highlight the lowest price automatically**: Visual emphasis (bold + background color) on the lowest `total price` cell. Do not require the buyer to scan manually.

3. **Show delta from cheapest**: For each supplier that is not the cheapest, show "+R$ X (+Y%)" so the buyer can quickly quantify the premium.

4. **Separate the price decision from the selection action**: First the buyer reviews the comparison; then a deliberate "Select Winner" action appears. Don't let a single click accidentally finalize the choice.

5. **Allow partial comparisons**: Some suppliers may not respond. The RFQ should allow marking a quotation as "no response" or "declined" — these still appear in the audit log.

6. **Sort by total price by default, allow re-sort**: Total price descending/ascending should be the default sort. Buyers also sort by lead time when urgency matters.

7. **Non-price factors visible**: Payment terms and lead time must be in the same view as price. The cheapest supplier with 90-day payment and 45-day lead time may lose to a slightly pricier one with 30-day payment and 7-day delivery.

---

## Supplier Evaluation: Standard Rating Criteria

After a purchase is completed, the buyer evaluates the supplier. Standard criteria in procurement:

| Criterion | What It Measures | Weight Guidance |
|-----------|-----------------|-----------------|
| Delivery punctuality | Did goods/services arrive on or before committed date? | High — often most important |
| Product/service quality | Did the delivered item match the specification? | High |
| Documentation accuracy | Was the NFe/invoice correct? Any corrections needed? | Medium |
| Communication responsiveness | Response time to RFQ and during delivery? | Medium |
| Price competitiveness | Was the price fair relative to market? | Low (already captured in RFQ comparison) |
| Post-sale support | Handled warranty/defect claims promptly? | Medium (more relevant for equipment) |

**Recommended implementation for v1**: A simple 1–5 star scale per criterion, free-text comment field, linked to the specific RFQ winner selection. Store as individual criterion scores; the supplier's overall rating is the rolling average. Do not force buyers to evaluate — make it a prompted (but skippable in v1) step after selecting winner.

**Display**: Show the supplier's overall rating and number of evaluations in the supplier directory and in the RFQ comparison table. A supplier with 4.2 stars from 12 purchases is more trustworthy than one with no history.

---

## Reporting: KPIs Procurement Managers Actually Care About

### Dashboard KPIs (real-time or daily refresh)

| KPI | Formula / Source | Why It Matters |
|-----|-----------------|----------------|
| Requisitions open (pending approval) | COUNT where status IN (PENDING_MANAGER, PENDING_DIRECTOR) | Signals backlog in approval chain |
| RFQs in progress | COUNT where RFQ status = ACTIVE | Buyer's current workload |
| Spend this month (approved POs/completed RFQs) | SUM(selected quotation total) where completed this month | Budget awareness |
| Avg approval cycle time | AVG(days from submission to final approval), last 30 days | Identifies bottleneck — is the manager or director slow? |
| Requisitions rejected this month | COUNT where status = REJECTED this month | Quality signal — are requesters providing enough info? |
| Active suppliers | COUNT of suppliers with at least 1 completed RFQ | Measures supplier base health |

### Periodic Reports (filterable by date range)

| Report | Dimensions | Why Useful |
|--------|------------|------------|
| Spend by category | Category + Period | Cost allocation; identifies highest-spend areas |
| Spend by requester/department | Requester or Cost Center + Period | Internal chargebacks or awareness |
| Requisition funnel | Status transitions count + avg time per stage | Process efficiency |
| Savings report | SUM(cheapest quote - selected quote) per period | Justifies procurement function's value |
| Supplier performance ranking | Avg rating + total spend per supplier | Preferred supplier decisions |
| RFQ cycle time | Days from RFQ creation to winner selection, by category | Identifies slow procurement areas |

### Report Output Considerations

- **PDF via ReportLab**: Professional header with company name (configurable), date range, generation timestamp, and page numbers. Tables must handle long text gracefully (wrap, not clip).
- **On-screen before PDF**: Always render the report in the browser first; PDF is an export action, not the primary view.
- **Excel/CSV export**: More useful than PDF for analysis. Strongly recommend adding `openpyxl` export as a differentiator — procurement managers paste into their own spreadsheets constantly.

---

## Feature Dependencies

```
Auth + RBAC
  └─ Requisition creation (requires Solicitante role)
       └─ Approval workflow (requires Gestor + Diretor roles)
            └─ RFQ creation (requires approved requisition + Comprador role)
                 └─ Quotation entry (requires active RFQ)
                      └─ Price comparison view (requires >= 1 quotation entry)
                           └─ Winner selection (requires comparison; produces completed RFQ)
                                └─ Supplier evaluation (requires completed RFQ)
                                     └─ Supplier rating display (requires >= 1 evaluation)

Supplier directory (prerequisite for RFQ — must have suppliers to invite)
  └─ CNPJ validation (during supplier registration)
  └─ Category assignment (enables filtered RFQ invitations)

Dashboard (requires completed transactions for meaningful data)
Reports (require completed transactions + date range data)
  └─ PDF export (requires working report views first)
  └─ CSV/Excel export (parallel to PDF, shared data layer)

Admin: alçada configuration (must exist before first approval routing decision)
Email notifications (orthogonal — can be added after core workflow works)
```

---

## MVP Recommendation

Given the PROJECT.md scope and 20-user internal context, prioritize in this order:

**Must ship in v1 (table stakes, no deferral):**
1. Auth + RBAC (5 roles, Admin user management)
2. Requisition creation + status tracking
3. Two-level approval workflow with configurable thresholds (alçadas)
4. Supplier directory with CNPJ validation
5. RFQ creation linked to approved requisition
6. Quotation entry (multi-supplier)
7. Price comparison view with lowest-price highlighting
8. Winner selection with mandatory justification
9. Dashboard KPIs (4–6 key metrics)
10. Spend-by-category report + PDF export
11. Email notification to approver when action required

**Defer to v2 (differentiators, not blockers):**
- Supplier performance evaluation (data model it now, UI later)
- Savings tracking report
- CSV/Excel export
- Approval SLA / deadline indicators
- Inline approval comments visible to requester (ship in v1 if low effort — it is)
- Requisition search and filtering (ship basic filters in v1)

**Do not build (anti-features confirmed):**
- Supplier portal, PO PDF generation, ERP integration, NFe processing, budget enforcement, 2FA/SSO, AI features

---

## Sources

- Domain knowledge: Procurement management industry standards (SAP Ariba, Coupa, TOTVS Compras, Mercado Eletrônico) — patterns derived from established systems
- Brazilian regulatory: CNPJ algorithm per Receita Federal published standard; NFe framework per SEFAZ/NF-e Nacional documentation (verify current retention rules with fiscal consultant)
- PROJECT.md scope and constraints: `C:\Users\admre\compras_nexos\.planning\PROJECT.md`
- Confidence: HIGH for procurement domain patterns and CNPJ algorithm; MEDIUM for NFe scope boundaries; LOW for specific regulatory retention periods (subject to IN updates)
