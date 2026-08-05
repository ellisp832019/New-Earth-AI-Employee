# GAIA v0.2 Known Limitations

- Ollama support is optional and must already be installed locally.
- The release uses deterministic fallback when Ollama is unavailable, so live model output is not guaranteed.
- GAIA remains a read-only inspector for MicroGrow and does not edit external projects.
- Conversational answers are evidence-constrained and can still be incomplete when the evidence is thin.
- Prompt-injection detection is defensive, not a perfect classifier.
- Agent-run history is stored locally in SQLite and is not meant for publication.
- Windows path semantics such as mixed separators and case-folding are validated separately from portable Linux CI behavior.
- The compatibility repair keeps Linux CI self-contained; the separate real MicroGrow proof remains a Windows-only validation lane.
- The release does not introduce autonomous tool execution or external workflow automation.
- The release is not the Windows desktop dashboard planned for v0.3.
