# Labelling guidelines: support-ticket classification

Six categories. Pick exactly one per ticket, in this priority order when more than
one could apply (an explicit ask higher in this list always wins):

1. **Refund** — the customer explicitly asks for money back: a refund, a
   reimbursement, "cancel and refund me," a chargeback threat. If the ticket is
   about a late/damaged package but the customer's actual ask is money back
   rather than a replacement or an ETA, it's Refund, not Shipping.
2. **Account access** — the customer cannot get into their account: login
   failure, forgotten password/username, 2FA problems, locked or suspended
   account, identity verification. A bug *in* the reset flow (e.g. "the reset
   email never arrives") is still Account access, not Technical issue.
3. **Billing** — charges, invoices, subscription cost, payment method
   problems, being billed the wrong amount or twice, plan/pricing questions.
   Only Billing if the customer is *not* asking for the money back (see
   Refund) — e.g. "why was I charged twice" with no refund ask is Billing;
   "charge me twice, refund the extra" is Refund.
4. **Shipping** — delivery tracking, delayed or lost packages, wrong address,
   shipping method/cost questions, damaged-in-transit where the ask is a
   replacement or status, not money back.
5. **Technical issue** — the product/app/website doesn't work as intended:
   crashes, error messages, broken features, performance problems — for a
   reason unrelated to logging in or billing.
6. **Other** — feedback, compliments, complaints with no clear category,
   feature requests, partnership/business inquiries, or anything that
   doesn't fit above, including multi-topic tickets with no single dominant
   ask.

## Notes on ambiguity

A handful of tickets in this dataset are deliberately ambiguous (e.g. a
billing complaint that's really a refund request, or a vague complaint that
belongs in Other) — this is intentional per the PRD's risk mitigation: an
eval task where every config scores 95%+ doesn't produce an interesting
finding. Ambiguous rows carry a `notes` field explaining the intended label.

## Provenance

These 100 tickets were drafted by an LLM (varied tone, length and category
mix) and then reviewed against the rules above before being committed to
`data.jsonl`. They are not real customer data.
