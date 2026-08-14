# Issue {{ISSUE_ID}}: {{ISSUE_TITLE}}

**Spec Reference**: [{{SPEC_NAME}}](../spec.md)  
**Status**: `PENDING` <!-- PENDING | RED_PASSED | GREEN_PASSED | REFACTOR_PASSED | COMPLETED -->

---

## 1. Goal
<!-- Specific, atomic goal of this single issue. -->

## 2. Test-Driven Development (TDD) Cycle

### 🔴 Phase 1: RED (Failing Test)
- **Target Test File**: `tests/...`
- **Expected Behavior**: Write test asserting the expected behavior before writing implementation code.
- **Verification Command**: Verify that the test runner executes and fails as expected.
  ```bash
  {{TEST_COMMAND}}
  ```

### 🟢 Phase 2: GREEN (Implementation)
- **Target Implementation Files**: `src/...`
- **Implementation Goal**: Write the minimal code necessary to make the failing test pass.
- **Verification Command**: Verify that all tests pass.
  ```bash
  {{TEST_COMMAND}}
  ```

### 🔵 Phase 3: REFACTOR & Lint
- **Code Quality Checklist**:
  - [ ] No dead code or duplication.
  - [ ] Linting & formatting checks pass cleanly.
  - [ ] Strict type checking passes with zero errors.
  - [ ] All regression test suites continue to pass 100% in green.

---

## 3. Completion Checklist
- [ ] Failing test written and verified (RED).
- [ ] Implementation code written and tests passing (GREEN).
- [ ] Refactored and linters verified (REFACTOR).
- [ ] Atomic git commit recorded.
