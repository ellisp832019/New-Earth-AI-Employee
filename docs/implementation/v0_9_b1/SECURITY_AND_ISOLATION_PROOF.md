# Security and Isolation Proof

The B1 implementation keeps the read-only boundary intact.

## Evidence

- Git inspection uses fixed command templates with `subprocess` and `shell=False`.
- project roots are canonicalized before they are stored or compared.
- duplicate canonical roots are rejected during settings load.
- the registry does not expand the public project API surface.
- the dashboard and MicroGrow repositories are treated as read-only evidence sources only.
- the health model records state without mutating external repositories.

## Non-goals preserved

- no repository writes;
- no branch creation or automatic merges;
- no output execution;
- no change to the existing release baseline.
