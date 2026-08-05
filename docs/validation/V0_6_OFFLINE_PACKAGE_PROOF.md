# GAIA v0.6 Offline Package Proof

Deterministic review packages are supported through the trust layer.

## Package contents

- `package_manifest.json`
- `hashes.json`
- `action.json`
- `approval.json` where applicable
- `receipt.json` where applicable
- `receipt_chain.json` where applicable
- `preview.md`
- `preview.diff`
- `source_metadata.json`
- `verification_instructions.md`

## Verification posture

- archive traversal is rejected;
- duplicate entries are rejected;
- unexpected executables are rejected;
- declared hashes are verified;
- verification runs offline and uses a temporary directory.
