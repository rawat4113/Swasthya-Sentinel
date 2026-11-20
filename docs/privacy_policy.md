# Privacy and responsible-use notes

- This MVP accepts aggregate observations only; patient and employee identifiers are rejected when known identifier columns are supplied.
- Workforce output applies small-cell display suppression when exposed-worker counts are below `MIN_GROUP_SIZE` (default 10).
- Clinic aggregate output similarly suppresses low-count cells below the configured threshold.
- Department accounts have role-scoped input permissions. Non-administrator users can review only import jobs created by their own account.
- Local MVP accounts use password hashing and expiring signed bearer tokens. The seeded demo credentials and local authentication implementation are not a production identity-management system.
- Do not upload identifiable health or employment data.
- Logs record the username responsible for key imports, account actions and interventions. Avoid placing personal information in action notes.
- Before a shared or public deployment, rotate signing secrets, change/remove demo credentials, use an established identity provider, enforce HTTPS, add password reset and session lifecycle controls, encrypt sensitive data, establish retention/backup policies, conduct security and privacy reviews, and confirm lawful data access.
- The system is not a diagnostic device and must not be used to rank employees or make disciplinary decisions.
