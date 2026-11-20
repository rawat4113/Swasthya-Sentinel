# Department portals and local MVP accounts

Swasthya Sentinel now starts with a sign-in screen and presents a role-specific workspace after login.

## Roles

- `district_admin`: all modules, all input categories, user management, simulations and district-wide import review.
- `health_officer`: aggregated health-service submissions and population health, AI and alert views.
- `environmental_officer`: environmental submissions, monitoring, geographic views and zone GeoJSON import.
- `workplace_safety_officer`: aggregated workplace submissions and related workforce, AI and alert views.

## Seeded local demo accounts

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@Sentinel2026` | district_admin |
| `health` | `Health@Sentinel2026` | health_officer |
| `environment` | `Env@Sentinel2026` | environmental_officer |
| `workplace` | `Work@Sentinel2026` | workplace_safety_officer |

Accounts are seeded only when `DEMO_USERS_ENABLED=true`. An administrator can create accounts in the User Management page. Public registration is intentionally disabled to prevent self-assigned privileged roles.

## Input lifecycle

1. The department user signs in and sees only permitted pages.
2. The user submits a manual observation or uploads a CSV/XLSX file.
3. The backend checks category permission, validates the record and stores the submitting username with the import job.
4. File uploads are staged and reviewed before commit.
5. The import endpoint commits valid records and records the actor in the audit log.
6. The backend recomputes the affected zone risk assessments.
7. The Department Portal shows the user's submission history. Non-admin users see only their own import jobs.

## Security boundary

The authentication is an MVP local signed-token/password-hash implementation. It is not a substitute for production identity management. Before shared or public deployment, disable seeded demo accounts, rotate the signing secret, add HTTPS, implement password reset/account lifecycle policies, and obtain a security review.
