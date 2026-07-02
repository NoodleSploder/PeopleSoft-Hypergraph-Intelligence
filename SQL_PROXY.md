# SQL Proxy Architecture
## Deterministic Data Masking & AI-Safe Database Access

---

# Vision

The SQL Proxy is a foundational security component of **PeopleSoft Hypergraph Intelligence (PHI)**.

Its purpose is to allow AI agents to perform meaningful diagnostics, troubleshooting, dependency analysis, runtime investigation, and SQL exploration **without ever exposing sensitive production data**.

Rather than granting AI direct access to Oracle, every SQL statement is routed through a proxy layer responsible for:

- Authorization
- Query validation
- SQL rewriting
- Row limiting
- Deterministic data masking
- Audit logging
- Policy enforcement

The SQL Proxy becomes the only database interface used by AI agents.

---

# Goals

The proxy must allow AI to:

- Reproduce production errors
- Troubleshoot runtime issues
- Analyze execution plans
- Inspect metadata
- Explore relationships
- Investigate application behavior
- Compare environments
- Analyze performance
- Understand data models

while preventing AI from ever viewing:

- Personally Identifiable Information (PII)
- Protected Health Information (PHI)
- Financial information
- Student information
- Employee information
- Customer information
- Authentication secrets
- Password hashes
- API keys
- Encryption keys
- Session tokens
- Sensitive free-text fields

---

# High Level Architecture

```
                  +----------------------+
                  |    AI Assistant      |
                  +----------+-----------+
                             |
                             |
                      SQL Request
                             |
                             v
                +-------------------------+
                |      SQL Proxy          |
                |-------------------------|
                | SQL Parser              |
                | Policy Engine           |
                | Authorization           |
                | Query Rewriter          |
                | Row Limiter             |
                | Result Masker           |
                | Audit Logger            |
                +-----------+-------------+
                            |
                     Safe SQL Execution
                            |
                            v
                  +----------------------+
                  | Oracle Database      |
                  +----------------------+
                            |
                     Raw Result Set
                            |
                            v
                +-------------------------+
                | Deterministic Masker    |
                +-------------------------+
                            |
                    Masked Result Set
                            |
                            v
                  +----------------------+
                  | AI Assistant         |
                  +----------------------+
```

---

# Security Principles

## AI Never Connects Directly

AI should never receive:

- Oracle credentials
- SYSADM credentials
- SELECT ANY TABLE
- SELECT ANY DICTIONARY
- Direct SQL*Net connectivity

All database access flows through the proxy.

---

## Read Only

The proxy is strictly read-only.

Forbidden operations:

```
INSERT
UPDATE
DELETE
MERGE
TRUNCATE
DROP
ALTER
CREATE
GRANT
REVOKE
COMMIT
ROLLBACK
```

Only safe SELECT operations are allowed.

---

## Policy Based Authorization

Each request is evaluated against a policy engine.

Policies include:

- Allowed schemas
- Allowed tables
- Allowed views
- Allowed packages
- Maximum row count
- Maximum execution time
- Maximum joins
- Maximum query complexity

---

# SQL Processing Pipeline

Every request follows this pipeline.

```
Incoming SQL
      |
Parse
      |
Validate
      |
Normalize
      |
Security Policy
      |
Rewrite
      |
Execute
      |
Mask
      |
Audit
      |
Return
```

---

# SQL Parsing

The proxy should parse SQL into an Abstract Syntax Tree (AST).

This allows detection of:

- Tables
- Columns
- Functions
- Joins
- Subqueries
- UNION
- WITH clauses
- Bind variables

String manipulation should never be used for security decisions.

---

# Query Validation

Reject:

```
INSERT
UPDATE
DELETE
MERGE
CREATE
DROP
ALTER
BEGIN
DECLARE
EXECUTE
CALL
```

Reject:

```
DBMS_SQL
UTL_FILE
UTL_HTTP
DBMS_CRYPTO
DBMS_SCHEDULER
DBMS_JOB
```

Reject:

```
SELECT ANY TABLE
```

Reject:

```
SYS
SYSTEM
XDB
MDSYS
```

unless explicitly allowed.

---

# Automatic Query Rewriting

The proxy may rewrite queries.

Example:

Original:

```sql
SELECT *
FROM PS_PERSONAL_DATA;
```

Becomes:

```sql
SELECT
EMPLID,
NAME,
EMAIL_ADDR,
EMPL_STATUS
FROM PS_PERSONAL_DATA
FETCH FIRST 100 ROWS ONLY;
```

---

# Automatic Row Limiting

Every query receives an automatic limit.

Examples:

```
FETCH FIRST 100 ROWS ONLY
```

or

```
ROWNUM <= 100
```

depending on Oracle version.

---

# Deterministic Data Masking

## Purpose

Mask sensitive values while preserving:

- relationships
- joins
- uniqueness
- troubleshooting capability

The same input must always produce the same output.

---

## Example

Real

```
EMPLID
-------
12345678
```

Masked

```
EMP_9A41C2F0
```

Every occurrence of:

```
12345678
```

always becomes

```
EMP_9A41C2F0
```

---

# Why Deterministic Masking?

If an employee exists in:

- JOB
- PERSONAL_DATA
- BENEFITS
- SECURITY
- PAYCHECK

the masked identifier must remain identical.

Otherwise joins become impossible.

---

# Token Categories

| Category | Prefix |
|-----------|---------|
| Employee | EMP |
| Operator | USER |
| Department | DEPT |
| Position | POS |
| Email | EMAIL |
| Address | ADDR |
| Phone | PHONE |
| Vendor | VENDOR |
| Student | STUDENT |
| Customer | CUSTOMER |

---

# Sensitive Column Detection

The proxy maintains a configurable catalog.

Example

```
EMPLID
OPRID
NAME
FIRST_NAME
LAST_NAME
EMAIL_ADDR
PHONE
ADDRESS1
ADDRESS2
NATIONAL_ID
SSN
BIRTHDATE
BANK_ACCOUNT
ACCOUNT_NUM
```

Every returned value is masked automatically.

---

# Stable Token Generation

Example algorithm

```
token =
PREFIX
+
SHA256(secret_salt + value)
```

Result

```
EMP_9A41C2F0
```

The AI cannot reverse the value.

---

# Human Decode Capability

Humans occasionally need to identify the real record.

Rather than exposing raw values to AI, the proxy maintains a secure token vault.

```
EMP_9A41C2F0

↓

12345678
```

Only privileged administrators may perform this lookup.

AI never receives decode permissions.

---

# Token Vault

```
TOKEN_TYPE

REAL_VALUE

MASKED_VALUE

CREATED_DATE

LAST_USED
```

The token vault is inaccessible to AI.

---

# Free Text Masking

Free-text fields present special challenges.

Examples

```
COMMENTS

DESCRLONG

MESSAGE_TEXT

EMAIL_BODY

NOTES
```

Strategies:

- redact entirely
- summarize
- named entity masking
- configurable exclusion

---

# Date Handling

Dates generally remain visible.

Sometimes dates should shift consistently.

Example

Real

```
2026-07-01
```

Masked

```
2026-07-06
```

Every date shifts by the same deterministic offset.

This preserves timelines.

---

# Numeric Masking

Examples

Salary

```
104,523
```

could become

```
101,812
```

or

```
100K-110K
```

depending on policy.

---

# SQL Result Masking

Example

Before

| EMPLID | NAME | EMAIL |
|----------|---------|----------------|
|12345678|Bob Smith|bob@company.com|

After

| EMPLID | NAME | EMAIL |
|----------|-------------|------------------------|
|EMP_9A41C2F0|Person_9A41|user9A41@example.invalid|

---

# Metadata Protection

The AI should still see

```
column names
data types
constraints
indexes
foreign keys
statistics
```

Metadata is extremely valuable for troubleshooting.

---

# Query Audit Logging

Every request is recorded.

Fields

```
timestamp

user

environment

database

sql_hash

execution_time

rows_returned

tables_accessed

policy_applied
```

No sensitive values are logged.

---

# Explain Plan Support

Allow

```
EXPLAIN PLAN
```

Allow

```
DBMS_XPLAN
```

These are extremely valuable for diagnostics.

---

# Runtime Diagnostics

Allowed

```
V$SESSION

GV$SESSION

ASH

AWR

PeopleSoft Monitor

Application Engine status

Process Scheduler metadata
```

Bind values should be masked.

---

# AI Capabilities

The proxy should fully support:

- SQL troubleshooting
- Explain Plan analysis
- Index recommendations
- Join analysis
- Runtime diagnostics
- Blocking session analysis
- Wait event analysis
- Metadata exploration
- Object dependency analysis
- Environment comparison
- Graph construction

---

# Future Enhancements

## Dynamic Policy Engine

Policies driven by YAML.

---

## Environment Profiles

Different rules for:

- DEV
- TEST
- UAT
- PROD

---

## Column Classification

Automatic discovery of PII.

---

## Oracle Data Safe Integration

Support Oracle Data Safe masking rules.

---

## Prompt Context Injection

Automatically include:

- table descriptions
- foreign keys
- PeopleSoft object definitions

---

## AI Trust Levels

Different capabilities depending on model.

Example

```
Observer

Analyst

Engineer

Administrator
```

Each level exposes progressively more metadata while maintaining masking guarantees.

---

# Design Principles

The SQL Proxy is not simply a SQL gateway.

It is an intelligent security and diagnostics layer that enables AI to reason about complex enterprise systems without exposing sensitive information.

The primary objectives are:

- Security by default
- Least privilege
- Read-only operation
- Deterministic masking
- Reproducible troubleshooting
- Human-decodable tokens
- Complete auditability
- Extensible policy engine
- Oracle and PeopleSoft awareness
- AI-native architecture

The long-term goal is for every AI interaction with enterprise data to pass through the SQL Proxy, making it one of the core security and intelligence components of PeopleSoft Hypergraph Intelligence.