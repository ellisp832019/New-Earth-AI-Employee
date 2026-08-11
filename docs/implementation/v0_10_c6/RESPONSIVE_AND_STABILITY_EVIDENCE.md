# Responsive and Stability Evidence

## Target Sizes

- 1280 x 720;
- 1366 x 768;
- 1600 x 900;
- 1920 x 1080.

## Stability Strategy

- keep the existing outer shell intact;
- use a nested workspace rail instead of more top-level entries;
- keep scrolling bounded inside cards and lists;
- keep selection state local to the workspace view;
- keep refresh explicit.

## Validation

- Flutter widget tests covered the shell at the four target sizes;
- the new programme workspace widget was exercised at desktop sizes;
- no layout overflow was observed in the automated checks.

## Windows Soak Acceptance

- release executable used for the soak;
- managed GAIA backend was started and healthy before the final connected application launch;
- GAIA Windows Control Centre showed `Connected`;
- backend version was `0.9.0`;
- soak start: `11/08/2026 12:56:32`;
- soak end: `11/08/2026 13:06:32`;
- exact duration: `00:10:00.1552832`;
- soak process PID: `28076`;
- process-level result: `PASS` - GAIA remained running for the entire soak;
- the Programme Intelligence workspace was exercised during the soak;
- no unconfirmed visual observations are recorded here.
