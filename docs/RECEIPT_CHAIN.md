# Receipt Chain

GAIA v0.6 uses a tamper-evident hash chain for execution receipts.

## Fields

- chain ID
- sequence number
- current receipt hash
- previous receipt hash
- schema version
- action ID
- approval binding hash
- target hash
- resulting content hash
- timestamp

## Verification outcomes

- valid
- invalid
- incomplete
- missing predecessor
- hash mismatch
- unsupported version

This is a hash chain, not a cryptographic signature system.
