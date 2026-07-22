# FACT-Bench — Day 10 Manual Audit Report

_Generated: 2026-07-22T01:44:51.485018+00:00_
_Sample seed: `20260717` (reproducible)_
_Validator: `src/templates/validator.py` v1.1.0 (auto-checks 8 rules)_
_Auditor: FACT-Bench audit pipeline (heuristic + automated checks)_

## 1. Scope

| Complexity | Population | Sampled | % |
|---|---|---|---|
| complex | 36 | 36 | 100% |
| medium | 94 | 28 | 30% |
| simple | 150 | 23 | 15% |
| **Total** | **280** | **87** | — |

Per plan.md Day 10 spec: 36 complex (100%) + 30% medium + 15% simple = ~87.

## 2. Outcome Summary

| Complexity | PASS | FLAG | FAIL | Findings |
|---|---|---|---|---|
| complex | 30 | 6 | 0 | 6 |
| medium | 27 | 1 | 0 | 1 |
| simple | 17 | 6 | 0 | 6 |
| **Total** | **74** | **13** | **0** | **13** |

**Finding breakdown**: 0 automated + 13 heuristic.

### Status legend
- **PASS** — no findings (template fully clean).
- **FLAG** — only heuristic findings (qualitative concern, no validator violation).
- **FAIL** — automated finding present (validator-class issue; should have been caught by `src/templates/validator.py`).

## 3. Findings by Template

### 3.1 COMPLEX

- **FIN-SOPVI-101** (finance/sop_violation/request_credit_limit_increase) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of request_credit_limit_increase's expected keywords ['credit limit', 'increase limit', 'raise limit', 'limit increase']
- **FIN-NOACT-102** (finance/no_action_abstention/escalate_to_human) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-TARGE-614** (finance/target_shift/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SUPER-104** (finance/supervisor_approval/request_supervisor_approval) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-105** (finance/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-106** (finance/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SOPVI-107** (finance/sop_violation/request_credit_limit_increase) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of request_credit_limit_increase's expected keywords ['credit limit', 'increase limit', 'raise limit', 'limit increase']
- **FIN-NOACT-108** (finance/no_action_abstention/escalate_to_human) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-TARGE-109** (finance/target_shift/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SUPER-110** (finance/supervisor_approval/request_supervisor_approval) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-322** (finance/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-332** (finance/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SOPVI-113** (finance/sop_violation/request_credit_limit_increase) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of request_credit_limit_increase's expected keywords ['credit limit', 'increase limit', 'raise limit', 'limit increase']
- **FIN-NOACT-114** (finance/no_action_abstention/escalate_to_human) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-TARGE-115** (finance/target_shift/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SUPER-116** (finance/supervisor_approval/request_supervisor_approval) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-117** (finance/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-118** (finance/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SOPVI-101** (telecom/sop_violation/report_lost_device) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of report_lost_device's expected keywords ['lost', 'stolen', 'device']
- **TEL-NOACT-102** (telecom/no_action_abstention/escalate_to_human) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-213** (telecom/device_activation/activate_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-104** (telecom/device_upgrade/upgrade_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-105** (telecom/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-106** (telecom/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SOPVI-107** (telecom/sop_violation/report_lost_device) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of report_lost_device's expected keywords ['lost', 'stolen', 'device']
- **TEL-NOACT-108** (telecom/no_action_abstention/escalate_to_human) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-109** (telecom/device_activation/activate_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-110** (telecom/device_upgrade/upgrade_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-701** (telecom/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-809** (telecom/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SOPVI-113** (telecom/sop_violation/report_lost_device) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of report_lost_device's expected keywords ['lost', 'stolen', 'device']
- **TEL-NOACT-114** (telecom/no_action_abstention/escalate_to_human) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-115** (telecom/device_activation/activate_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-116** (telecom/device_upgrade/upgrade_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-117** (telecom/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-118** (telecom/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_

### 3.2 MEDIUM

- **FIN-DIALO-121** (finance/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DIALO-133** (finance/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DISPU-107** (finance/dispute_followup/dispute_transaction) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DISPU-118** (finance/dispute_followup/dispute_transaction) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-DISPU-140** (finance/dispute_followup/check_dispute_status) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-FRAUD-116** (finance/fraud_report/report_fraud) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-LOANF-108** (finance/loan_followup/check_loan_status) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-LOANF-141** (finance/loan_followup/check_loan_status) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-MULTI-102** (finance/multi_slot_mixed/set_temporary_limit) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of set_temporary_limit's expected keywords ['temporary', 'temp limit', 'short-term']
- **FIN-REPLA-106** (finance/replacement/issue_replacement_card) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SUPER-109** (finance/supervisor_approval/request_supervisor_approval) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-TARGE-136** (finance/target_shift/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-TARGE-147** (finance/target_shift/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-CASCA-101** (telecom/cascade_plan_change/change_plan) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-CASCA-113** (telecom/cascade_addon_subscribe/add_addon) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-CASCA-135** (telecom/cascade_addon_subscribe/add_addon) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-CONTR-120** (telecom/contract_check/check_contract_status) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-CONTR-131** (telecom/contract_check/check_contract_status) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-114** (telecom/device_activation/activate_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-117** (telecom/device_upgrade/upgrade_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DEVIC-147** (telecom/device_activation/activate_device) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-144** (telecom/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-MULTI-126** (telecom/multi_slot_mixed/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-MULTI-137** (telecom/multi_slot_mixed/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-OUTAG-127** (telecom/outage_report/report_outage) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SERVI-140** (telecom/service_resume/resume_service) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SERVI-141** (telecom/service_suspend/suspend_service) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SERVI-394** (telecom/service_suspend/suspend_service) — PASS (auto=0, heur=0)
  - _no findings_

### 3.3 SIMPLE

- **FIN-DISPU-173** (finance/dispute_followup/check_dispute_status) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-FRAUD-171** (finance/fraud_report/report_fraud) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-IDENT-120** (finance/identity_verification/verify_identity_tfa) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-IDENT-146** (finance/identity_verification/verify_identity_tfa) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-LOANA-105** (finance/loan_application/apply_for_loan) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-LOANA-144** (finance/loan_application/apply_for_loan) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-LOANA-157** (finance/loan_application/apply_for_loan) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-LOANF-148** (finance/loan_followup/check_loan_status) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-PUREQ-153** (finance/pure_query/check_balance) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-PUREQ-166** (finance/pure_query/check_balance) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SINGL-104** (finance/single_delete/disable_autopay) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of disable_autopay's expected keywords ['disable', 'autopay', 'cancel', 'turn off']
- **FIN-SINGL-117** (finance/single_delete/disable_autopay) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of disable_autopay's expected keywords ['disable', 'autopay', 'cancel', 'turn off']
- **FIN-SINGL-128** (finance/single_add/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SINGL-141** (finance/single_add/update_contact_info) — PASS (auto=0, heur=0)
  - _no findings_
- **FIN-SINGL-167** (finance/single_add/apply_for_loan) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of apply_for_loan's expected keywords ['loan', 'apply', 'borrow']
- **FIN-SINGL-168** (finance/single_modify/make_payment) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of make_payment's expected keywords ['pay', 'payment', 'balance', 'settle']
- **TEL-CONTR-146** (telecom/contract_check/check_contract_status) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-111** (telecom/dialogue_inform/inform_customer) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-DIALO-112** (telecom/dialogue_confirm/confirm_intent) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-IDENT-167** (telecom/identity_verification/verify_identity) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-PUREQ-113** (telecom/pure_query/check_data_usage) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of check_data_usage's expected keywords ['data', 'usage', 'how much data']
- **TEL-SERVI-168** (telecom/service_suspend/suspend_service) — PASS (auto=0, heur=0)
  - _no findings_
- **TEL-SINGL-103** (telecom/single_modify/pay_bill) — FLAG (auto=0, heur=1)
  - H1 user_goal / agent_paraphrase mention none of pay_bill's expected keywords ['pay', 'bill']

## 4. Patterns & Recommendations

### Finding frequency

| Rule | Count |
|---|---|
| H1 | 13 |

### Top recommendations


## 5. Conclusion

Of **87 templates** audited (36 complex + 28 medium + 23 simple):
- **74 PASS** (85%) — fully clean.
- **13 FLAG** (15%) — heuristic-only concerns (typically H1 user_goal phrasing).
- **0 FAIL** (0%) — would have been caught by validator; double-check these.

Mock-generated templates are schema-valid and operationally coherent but linguistically thin. Regenerate with `--provider openai` for a real benchmark-quality corpus.
