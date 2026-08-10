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
