# OpenRivian
This is a fork of sunnypilot specifically designed for integrating Rivian vehicle support. 

## Branch Topology

**IMPORTANT**: This repository uses a highly structured, automated branching strategy.
- `clean`: The pristine base state. Active development is built upon this branch.
- `dev-test`: CI/CD automated staging ground where feature branches are combined and tested for compute safety.
- `dev`: The production release candidate. **This is the branch that runs on the Comma device in the vehicle.**
- `can-debug`: Isolated, experimental CAN sniffing utilities. **Never driven.**
- **Feature Branches**: Independent modules (`api`, `mqtt`, `web-dashboard`) built from `clean`.

### Development Workflow
To contribute a new feature:
1. Branch off `clean` (e.g., `git checkout -b feature/my-new-feature origin/clean`).
2. Add your feature branch name to the `FEATURE_BRANCHES` array in `.github/workflows/openrivian_tests.yml`.
3. Commit and push. GitHub Actions will automatically test your branch, combine it with the others into `dev-test`, run integration tests, and then fast-forward `dev` for Comma deployment.

### Compute Safety (os.nice)
Any custom Python daemons designed for Rivian (like `openriviand`, `cereal2mqtt`, `mqttd`) MUST invoke `os.nice(19)` at the top of their `main()` routine. This ensures they drop to the lowest CPU priority, immediately yielding compute to OpenPilot's core driving logic.

### Experimental CAN Sniffing (`can-debug`)
Experimental scripts intended to dump, parse, or sniff CAN messages directly off the network (such as high-voltage state extraction) are strictly banned from `dev`. Including them in `dev` can crash OpenPilot's process manager (`manager.py`). They must reside only in the `can-debug` branch. When testing CAN tools on the vehicle, ensure the vehicle is parked and manually check out `can-debug` on the Comma. Revert to `dev` before driving.
