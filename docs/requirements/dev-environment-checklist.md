# Developer Environment Checklist

One row per teammate. Minimum versions are in [engineering-standards.md](./engineering-standards.md#minimum-tool-versions). Mark ✅ when the version check passes, ❌ with a note when it does not.

| Teammate | Git | Java 17 | Python 3.11+ | Docker | PostgreSQL / psql | SSH or GCM | Clone + push test | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jeevan Shahi (Windows 11) | ✅ 2.49.0 | ❌ not installed | ✅ 3.13.2 | ❌ not installed | ❌ not installed (portable 16.4 binaries used for M2 validation) | ✅ HTTPS | ✅ | 2026-10-06 |

## Open actions

- [ ] Install Eclipse Temurin JDK 17 and Maven 3.9 before M4 (`winget install EclipseAdoptium.Temurin.17.JDK`).
- [ ] Install Docker Desktop before M5 (`winget install Docker.DockerDesktop`).
- [ ] Install PostgreSQL 16 server and client (`winget install PostgreSQL.PostgreSQL.16`) so `psql` is on `PATH`.
