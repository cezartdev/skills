# OWASP Top 10 Security Reference Guide & Polyglot Anti-Pattern Catalog

This document establishes the official **OWASP Top 10 (2021)** security baseline and polyglot code anti-pattern reference for the `workflow-security-worker` subagent and developers.

---

## Overview of OWASP Top 10 Taxonomy

```text
A01:2021 - Broken Access Control
A02:2021 - Cryptographic Failures
A03:2021 - Injection (SQL, Command, Code, NoSQL)
A04:2021 - Insecure Design
A05:2021 - Security Misconfiguration
A06:2021 - Vulnerable and Outdated Components
A07:2021 - Identification and Authentication Failures
A08:2021 - Software and Data Integrity Failures (Unsafe Deserialization)
A09:2021 - Security Logging and Monitoring Failures
A10:2021 - Server-Side Request Forgery (SSRF)
```

---

## 1. A01:2021 – Broken Access Control

### Risks & CWEs
- CWE-22: Path Traversal (`../` directory traversal)
- CWE-284: Improper Access Control (IDOR, missing authorization middleware)
- CWE-942: Overly Permissive Cross-Origin Resource Sharing (CORS wildcard `*` with credentials)

### Polyglot Anti-Patterns & Remediations

#### Path Traversal
- ❌ **Insecure (Python)**:
  ```python
  # Vulnerable: User can pass "../../etc/passwd"
  file_path = os.path.join(UPLOAD_DIR, user_input)
  with open(file_path, "r") as f:
      data = f.read()
  ```
- ✅ **Secure (Python)**:
  ```python
  safe_filename = os.path.basename(user_input)
  file_path = os.path.abspath(os.path.join(UPLOAD_DIR, safe_filename))
  if not file_path.startswith(os.path.abspath(UPLOAD_DIR)):
      raise PermissionError("Access denied: Path traversal attempt")
  ```

#### Overly Permissive CORS
- ❌ **Insecure (Node / Express)**:
  ```typescript
  app.use(cors({ origin: "*", credentials: true }));
  ```
- ✅ **Secure (Node / Express)**:
  ```typescript
  const allowedOrigins = ["https://app.example.com"];
  app.use(cors({ origin: allowedOrigins, credentials: true }));
  ```

---

## 2. A02:2021 – Cryptographic Failures

### Risks & CWEs
- CWE-259: Hardcoded Passwords / Secrets
- CWE-327: Use of Broken or Risky Cryptographic Algorithms (MD5, SHA-1, DES, RC4)
- CWE-295: Disabled Certificate Validation (`InsecureSkipVerify: true`)

### Polyglot Anti-Patterns & Remediations

#### Deprecated Hashing & Ciphers
- ❌ **Insecure (Python / Go)**:
  ```python
  # Vulnerable: MD5 / SHA-1 for passwords or integrity
  token = hashlib.md5(user_input.encode()).hexdigest()
  ```
- ✅ **Secure (Python / Go)**:
  ```python
  # Secure: SHA-256 / Argon2 / bcrypt for passwords
  import bcrypt
  hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
  ```

#### TLS Certificate Verification Bypass
- ❌ **Insecure (Go)**:
  ```go
  tr := &http.Transport{
      TLSClientConfig: &tls.Config{InsecureSkipVerify: true}, // Vulnerable
  }
  ```
- ✅ **Secure (Go)**:
  ```go
  tr := &http.Transport{
      TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS13},
  }
  ```

---

## 3. A03:2021 – Injection

### Risks & CWEs
- CWE-89: SQL Injection (raw SQL string formatting)
- CWE-78: OS Command Injection (`shell=True`, `child_process.exec`, `system()`)
- CWE-94: Code Injection (`eval()`, `exec()`, `Function()`)

### Polyglot Anti-Patterns & Remediations

#### SQL Injection
- ❌ **Insecure (Python / TS / Go)**:
  ```python
  # Vulnerable: Formatted string SQL query
  cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
  ```
- ✅ **Secure (Python / TS / Go)**:
  ```python
  # Secure: Parameterized query
  cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
  ```

#### OS Command Injection
- ❌ **Insecure (Python / Node)**:
  ```python
  # Vulnerable: Shell interpretation allows command chaining via '; rm -rf /'
  subprocess.run(f"ping -c 1 {user_ip}", shell=True)
  ```
- ✅ **Secure (Python / Node)**:
  ```python
  # Secure: Array format, shell=False, strict input validation
  subprocess.run(["ping", "-c", "1", user_ip], shell=False, check=True)
  ```

#### Code Injection (`eval`)
- ❌ **Insecure (TypeScript / Python)**:
  ```typescript
  const result = eval(`(${untrustedJson})`);
  ```
- ✅ **Secure (TypeScript / Python)**:
  ```typescript
  const result = JSON.parse(untrustedJson);
  ```

---

## 4. A04:2021 – Insecure Design

### Risks & CWEs
- CWE-799: Improper Control of Generation of Frequent Architectural Requests (Missing Rate Limiting)
- CWE-1059: Incomplete Threat Modeling

### Mitigations
- Implement rate limiters on all public endpoints (e.g. token bucket, Redis rate limiting).
- Validate business logic state transitions explicitly on the server side.

---

## 5. A05:2021 – Security Misconfiguration

### Risks & CWEs
- CWE-209: Generation of Error Message Containing Sensitive Information (Stack traces leaked)
- CWE-1004: Sensitive Cookie Without 'HttpOnly' Flag
- CWE-614: Sensitive Cookie in HTTPS Session Without 'Secure' Attribute

### Polyglot Anti-Patterns & Remediations
- ❌ **Insecure (Flask / Django / Express)**:
  ```python
  app.run(debug=True, host="0.0.0.0")  # Leaks interactive debugger
  ```
- ✅ **Secure**:
  ```python
  app.run(debug=False, host="127.0.0.1")
  ```

---

## 6. A06:2021 – Vulnerable and Outdated Components

### Ecosystem Audit Commands & Actions
- **Python**: `uv pip audit` or `pip-audit`
- **Node.js**: `pnpm audit --prod` or `npm audit --omit=dev`
- **Rust**: `cargo audit`
- **Go**: `govulncheck ./...`
- **.NET**: `dotnet list package --vulnerable`

---

## 7. A07:2021 – Identification and Authentication Failures

### Risks & CWEs
- CWE-384: Session Fixation
- CWE-613: Insufficient Session Expiration
- CWE-798: Use of Hard-coded Credentials

### Mitigations
- Always set `HttpOnly`, `Secure`, and `SameSite=Lax/Strict` on authentication cookies.
- Rotate session IDs immediately upon privilege escalation or login.

---

## 8. A08:2021 – Software and Data Integrity Failures

### Risks & CWEs
- CWE-502: Deserialization of Untrusted Data (`pickle`, unsafe `yaml`, `ObjectInputStream`)

### Polyglot Anti-Patterns & Remediations
- ❌ **Insecure (Python / PyYAML)**:
  ```python
  import pickle, yaml
  obj = pickle.loads(untrusted_payload)  # RCE vulnerability!
  cfg = yaml.load(untrusted_yaml, Loader=yaml.Loader)  # RCE vulnerability!
  ```
- ✅ **Secure (Python / PyYAML)**:
  ```python
  import json, yaml
  obj = json.loads(untrusted_payload)
  cfg = yaml.safe_load(untrusted_yaml)
  ```

---

## 9. A09:2021 – Security Logging and Monitoring Failures

### Risks & CWEs
- CWE-532: Insertion of Sensitive Information into Log File

### Mitigations
- ❌ Do NOT log: Passwords, authorization headers, credit card numbers, PII, API tokens.
- ✅ Mask sensitive parameters before logging: `logger.info(f"User login: {mask_email(email)}")`.

---

## 10. A10:2021 – Server-Side Request Forgery (SSRF)

### Risks & CWEs
- CWE-918: Server-Side Request Forgery (SSRF)

### Polyglot Anti-Patterns & Remediations
- ❌ **Insecure (Python / Node)**:
  ```python
  # Vulnerable: User can target http://169.254.169.254/latest/meta-data/ or localhost
  url = request.args.get("webhook_url")
  response = requests.get(url)
  ```
- ✅ **Secure (Python / Node)**:
  ```python
  import ipaddress, urllib.parse
  parsed = urllib.parse.urlparse(url)
  if parsed.scheme not in ["http", "https"]:
      raise ValueError("Invalid protocol")
  ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
  if ip.is_private or ip.is_loopback or ip.is_link_local:
      raise PermissionError("SSRF Blocked: Destination IP is private or restricted")
  response = requests.get(url, timeout=5)
  ```
