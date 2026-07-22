# FACT-Bench — Day 11 Distribution Check Report

_Generated: 2026-07-22T01:37:46.651287+00:00_
_Total templates: 300 (300 target)_
_Total ops: 1278_

## 1. Operation-Type Distribution

Target (per plan.md Day 11): KEEP=50% ADD=15% MODIFY=20% DELETE=10% CASCADE=5%.

| Op | Actual | Target | Δ (pp) | Status |
|---|---|---|---|---|
| KEEP | 50.2% | 50% | +0.2 | OK |
| ADD | 19.1% | 15% | +4.1 | OK |
| MODIFY | 14.8% | 20% | -5.2 | OK |
| DELETE | 12.3% | 10% | +2.3 | OK |
| CASCADE | 3.7% | 5% | -1.3 | OK |

**KL divergence (actual || target)**: `0.0170` nats
Reference: random distribution of 5 classes is ~1.609 nats; the closer to 0 the better.

### Distribution recommendations

- **MODIFY** is under-represented (actual 14.8% < target 20%). Per plan.md Day 11, edit 10-20 templates to introduce more MODIFY ops.

## 2. Slot Coverage (non-KEEP uses)

Threshold (per plan.md Day 11): each slot >= 5 non-KEEP uses.

### 2.1 finance

| Slot | Non-KEEP | Total | Status |
|---|---|---|---|
| address | 11 | 22 | OK |
| autopay | 14 | 23 | OK |
| autopay_bank | 16 | 26 | OK |
| autopay_date | 16 | 31 | OK |
| bill_amount | 10 | 19 | OK |
| card_holder_name | 14 | 49 | OK |
| card_last_four | 17 | 51 | OK |
| card_type | 9 | 14 | OK |
| credit_limit | 11 | 19 | OK |
| dispute_status | 20 | 27 | OK |
| due_date | 7 | 23 | OK |
| email | 18 | 52 | OK |
| fraud_amount | 21 | 31 | OK |
| fraud_report_id | 17 | 28 | OK |
| income | 3 | 11 | UNDER |
| loan_amount | 9 | 21 | OK |
| loan_purpose | 11 | 20 | OK |
| loan_term | 13 | 18 | OK |
| minimum_payment | 13 | 20 | OK |
| occupation | 8 | 22 | OK |
| phone | 19 | 55 | OK |
| temp_limit | 9 | 24 | OK |

### 2.2 telecom

| Slot | Non-KEEP | Total | Status |
|---|---|---|---|
| activation_date | 20 | 31 | OK |
| addon_name | 22 | 31 | OK |
| addon_price | 17 | 28 | OK |
| addon_status | 18 | 31 | OK |
| address | 16 | 50 | OK |
| billing_amount | 12 | 25 | OK |
| billing_cycle | 13 | 22 | OK |
| contract_term | 15 | 26 | OK |
| data_allowance | 14 | 35 | OK |
| device_installment | 15 | 26 | OK |
| device_model | 20 | 32 | OK |
| email | 15 | 48 | OK |
| imei | 16 | 24 | OK |
| payment_method | 19 | 50 | OK |
| phone | 13 | 47 | OK |
| plan_name | 20 | 57 | OK |
| plan_price | 18 | 32 | OK |
| service_status | 21 | 30 | OK |

### Slot coverage recommendations

- **Finance under-covered**: income. Add ADD/MODIFY/DELETE ops for these slots in 10-20 templates.

## 3. Action Coverage (templates as agent_action)

Threshold (per plan.md Day 11): each action >= 3 templates.

| Action | Domain | Templates | Status |
|---|---|---|---|
| verify_identity | finance | 9 | OK |
| check_balance | finance | 7 | OK |
| make_payment | finance | 7 | OK |
| update_contact_info | finance | 28 | OK |
| enable_autopay | finance | 6 | OK |
| disable_autopay | finance | 6 | OK |
| request_credit_limit_increase | finance | 4 | OK |
| set_temporary_limit | finance | 4 | OK |
| report_fraud | finance | 11 | OK |
| dispute_transaction | finance | 6 | OK |
| check_dispute_status | finance | 4 | OK |
| issue_replacement_card | finance | 10 | OK |
| apply_for_loan | finance | 12 | OK |
| check_loan_status | finance | 10 | OK |
| escalate_to_human | finance | 8 | OK |
| inform_customer | finance | 25 | OK |
| confirm_intent | finance | 25 | OK |
| verify_identity_tfa | finance | 3 | OK |
| request_supervisor_approval | finance | 12 | OK |
| verify_identity | telecom | 9 | OK |
| check_data_usage | telecom | 8 | OK |
| change_plan | telecom | 6 | OK |
| add_addon | telecom | 6 | OK |
| remove_addon | telecom | 6 | OK |
| update_contact_info | telecom | 28 | OK |
| suspend_service | telecom | 11 | OK |
| resume_service | telecom | 10 | OK |
| activate_device | telecom | 9 | OK |
| report_lost_device | telecom | 4 | OK |
| upgrade_device | telecom | 7 | OK |
| pay_bill | telecom | 4 | OK |
| change_billing_cycle | telecom | 4 | OK |
| check_contract_status | telecom | 10 | OK |
| escalate_to_human | telecom | 8 | OK |
| dispute_bill | telecom | 7 | OK |
| report_outage | telecom | 11 | OK |
| inform_customer | telecom | 25 | OK |
| confirm_intent | telecom | 25 | OK |


## 4. Verdict

- Operation-type deviation: **1 under-represented / 0 over-represented** (KL=0.0170)
- Slot coverage: **1 slots under threshold**
- Action coverage: **0 actions under threshold**

**FLAG**: distribution gaps exist. Per plan.md Day 11, manually edit 10-20 templates to close the under-represented categories. (Editing is intentionally NOT automated — see plan.md Day 10 audit philosophy.)
