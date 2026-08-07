# Codex Prompt Generation

The generated prompt is a review artifact, not an executable command.

## Content goals

- explain the repository objective;
- show the reviewed evidence set;
- list scope, non-goals, prerequisites, and validation commands;
- make the STOP point explicit;
- preserve the exact revision and prompt fingerprints.

## Safety rules

- never auto-run the prompt;
- never infer extra instructions from the evidence block;
- keep the prompt consistent with the current approved revision;
- regenerate if the source evidence becomes stale.
