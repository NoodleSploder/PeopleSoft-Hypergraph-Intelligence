````markdown
## Remote Transaction Log Source Layer

### Goal

PeopleSoft Explorer must support reading remote flat-file logs over SSH/SFTP and attaching those log entries directly into transaction chains.

Logs are not only searchable records. They are evidence events in an end-to-end transaction timeline across:

- Browser/client request
- Nginx/reverse proxy
- PIA/WebLogic web server
- Integration Gateway
- App server
- Tuxedo
- Process Scheduler
- Oracle/session activity

---

## Configuration Model

```json
{
  "log_sources": [
    {
      "id": "hcm-web-01",
      "env": "HCM",
      "tier": "web",
      "host": "hcmdmo-web-01",
      "protocol": "ssh",
      "port": 22,
      "username": "ps_hcm",
      "auth": {
        "type": "key",
        "key_path": "/opt/deathstar-api/keys/hcm_web_01"
      },
      "paths": [
        {
          "name": "PIA WebLogic stdout",
          "path": "/opt/psoft/hcm/cfg/webserv/peoplesoft/servers/PIA/logs/PIA_weblogic.log",
          "parser": "weblogic",
          "chain_role": "web_diagnostic"
        },
        {
          "name": "PIA access log",
          "path": "/opt/psoft/hcm/cfg/webserv/peoplesoft/servers/PIA/logs/access.log",
          "parser": "pia_access",
          "chain_role": "web_access"
        }
      ]
    },
    {
      "id": "hcm-app-01",
      "env": "HCM",
      "tier": "app",
      "host": "hcmdmo-app-01",
      "protocol": "sftp",
      "port": 22,
      "username": "ps_hcm",
      "auth": {
        "type": "key",
        "key_path": "/opt/deathstar-api/keys/hcm_app_01"
      },
      "paths": [
        {
          "name": "App Server APPSRV",
          "path": "/opt/psoft/hcm/appserv/HCMDMO_APP/LOGS/APPSRV*.LOG",
          "parser": "appsrv",
          "chain_role": "app_server"
        },
        {
          "name": "Tuxedo ULOG",
          "path": "/opt/psoft/hcm/appserv/HCMDMO_APP/LOGS/TUXLOG*",
          "parser": "tuxedo",
          "chain_role": "tuxedo"
        }
      ]
    }
  ]
}
````

---

## Normalized Chain Event Shape

Every parser should emit a transaction-chain-compatible event:

```json
{
  "event_id": "evt-000001",
  "trace_id": "HCM-20260629-000001",
  "sequence": 30,
  "timestamp": "2026-06-29T16:24:11-05:00",
  "env": "HCM",
  "tier": "web",
  "host": "hcmdmo-web-01",
  "source": {
    "type": "flat_file",
    "transport": "ssh",
    "source_id": "hcm-web-01",
    "file": "/path/to/log",
    "parser": "weblogic"
  },
  "correlation": {
    "operator_id": "VP1",
    "session_id": "abc123",
    "ip": "10.0.0.44",
    "uri": "/psc/EMPLOYEE/HRMS/c/...",
    "request_id": null,
    "process_instance": null,
    "ib_message_id": null,
    "sql_session_id": null
  },
  "severity": "ERROR",
  "message": "BEA-101020 Servlet failed...",
  "raw": "Full original log line here"
}
```

---

## Backend Architecture

```text
connectors/
  remote_logs.py
  ssh_client.py
  sftp_client.py
  transaction_chain.py
  log_parsers/
    weblogic.py
    pia_access.py
    appsrv.py
    tuxedo.py
    nginx.py
    integration_gateway.py
    process_scheduler.py
```

### `remote_logs.py`

Responsible for:

* Loading configured log sources
* Validating reachability
* Listing available files
* Reading last N lines
* Streaming/tailing remote files
* Searching by time range, operator, IP, URI, session, process instance, IB message ID, or error text
* Sending parsed entries to the transaction chain layer

### `transaction_chain.py`

Responsible for:

* Accepting normalized events from logs, Oracle, nginx, tracing, and live monitors
* Assigning or resolving `trace_id`
* Ordering events by timestamp and sequence
* Correlating events across tiers
* Returning the full transaction timeline

---

## Correlation Keys

Use as many of these as available:

```text
timestamp proximity
operator_id
client_ip
uri
session_id
JSESSIONID
PS_TOKEN context
request_id
component
market
portal
node
ib_message_id
process_instance
run_control_id
sql_session_id
host
thread_id
tuxedo service name
```

---

## API Endpoints

```text
GET /api/logs/sources
GET /api/logs/files?env=HCM&tier=web
GET /api/logs/tail?source_id=hcm-web-01&path=...&lines=500
GET /api/logs/search?env=HCM&q=VP1&since=...

GET /api/trace/chain?env=HCM&operator=VP1&since=...
GET /api/trace/chain/by-session?env=HCM&session_id=...
GET /api/trace/chain/by-request?env=HCM&uri=...
GET /api/trace/chain/by-process?env=HCM&process_instance=...
GET /api/trace/chain/live?env=HCM
```

---

## Important Design Requirements

Do **not** treat remote logs as isolated search results only.

Do **not** require logs to be copied locally first.

Do **not** assume one web server or one app server.

Do **not** hardcode HCM/FSCM paths.

Do **not** require root SSH.

Use key-based authentication where possible.

Support wildcard paths:

```text
APPSRV*.LOG
TUXLOG*
PIA_weblogic*.log
access.log*
stdout*
stderr*
```

Add source health states:

```text
reachable
auth_failed
path_missing
permission_denied
empty_log
stale_log
parser_failed
clock_skew_detected
```

---

## Roadmap Addition

### Remote Transaction Log Source Layer

PeopleSoft Explorer must support remote flat-file log ingestion over SSH/SFTP and attach parsed log entries directly into transaction chains.

The system should allow multiple configured log sources per environment and tier, including web servers, app servers, process schedulers, Integration Gateway hosts, and reverse proxy hosts.

Each source should define host, protocol, authentication method, tier, environment, path patterns, parser type, and transaction chain role.

This feature is foundational for end-to-end tracing because PeopleSoft activity frequently crosses browser, nginx, PIA/WebLogic, Integration Gateway, app server, Tuxedo, Process Scheduler, and Oracle layers.

The primary user experience should be a chronological transaction chain, not disconnected log search output.

```
```
