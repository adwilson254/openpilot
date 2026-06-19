## OpenRivian Feature Pull Request

Thank you for contributing to OpenRivian! Please ensure your pull request adheres to the testing and CI/CD workflow requirements.

### Target Branch
- [ ] My PR targets the `dev-test` branch. (Do **NOT** target `dev` directly! The `dev` branch is protected by automation).

### CI & Automated Testing
- [ ] I have verified that GitHub Actions passes on my feature branch.
- [ ] If I added a new Python daemon, I have included it in `selfdrive/openrivian/tests/test_daemons.py` for isolation and syntax testing.
- [ ] I have ensured that my background daemon implements `os.nice(19)` to prioritize safety and self-drive compute.
- [ ] My feature can fail gracefully (e.g., if the internet drops, API goes down, or MQTT crashes, it won't crash the entire system).

### Testing Locally
If you want to verify your code locally before pushing, run:
```bash
PYTHONPATH=. uv run python3 selfdrive/openrivian/tests/test_daemons.py
```

---
*Note: Once this PR is merged into `dev-test`, the CI pipeline will run integration tests one last time. If it passes, GitHub Actions will automatically fast-forward the `dev` branch to deploy your code to active vehicles.*
