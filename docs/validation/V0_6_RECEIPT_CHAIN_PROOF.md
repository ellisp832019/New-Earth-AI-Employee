# GAIA v0.6 Receipt Chain Proof

Receipt records now carry:

- `chain_id`
- `chain_sequence`
- `previous_receipt_hash`
- `receipt_content_hash`
- `verification_status`

Verification endpoints and CLI commands are available for:

- single receipts;
- receipt chains;
- tamper detection via SHA-256 hash comparison.
