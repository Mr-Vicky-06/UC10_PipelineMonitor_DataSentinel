# Team Development Workflow

All developers work from the same Git repository (`main`). Each developer works on a dedicated branch.

## Example Branches
```text
main
│
├── pipeline/ingestion
├── pipeline/validation
├── pipeline/cleaning
├── pipeline/transformation
├── pipeline/features
└── pipeline/rules
```

## Workflow Protocol
Nobody directly pushes implementation work to `main`. 

1. `main`
2. developer branch
3. implementation
4. tests
5. git diff inspection
6. commit
7. push
8. pull request
9. review
10. integration
11. `main`

**Every developer must pull the latest shared project knowledge before starting work.**

## Shared Development Protocol (Agent Behavior)
Every Antigravity agent must follow this protocol before making significant changes:
1. WHAT
2. WHY
3. INPUT
4. DESIGN
5. COMMAND
6. EXPECTED RESULT
7. EXECUTE
8. RESULT
9. INTERPRETATION
10. NEXT STEP

Agents must explain what they are doing so the developer can understand and learn the implementation.

**Branch Awareness:** The shared knowledge is PROJECT-WIDE. The developer's branch determines WHAT they are currently implementing. The shared project knowledge determines HOW the implementation must fit into the overall system.
