# Rule 17: Backup and Version Control
## Added: April 11, 2026

### Non-Negotiable

#### Git Commits (Claude Code MUST follow)
1. Before ANY code change, run: `cd /home/claudeuser/agent && git add -A && git commit -m "PRE: [description of upcoming change]"`
2. After completing a change, run: `cd /home/claudeuser/agent && git add -A && git commit -m "POST: [description of completed change]"`
3. For major milestones, create a tag: `git tag -a [descriptive-name] -m "[description]"`
4. NEVER skip the pre-change commit. This is the safety net.

#### Pre-Change Database Snapshots (Claude Code MUST follow)
Before any change that touches the database (page content, image labels, gallery settings, project data):
1. Run: `PGPASSWORD=StrongPass123! pg_dump -h 127.0.0.1 -U agent_user -Fc -Z 9 marketing_agent > /var/backups/postgresql/pre_[change_name]_$(date +%Y%m%d_%H%M%S).dump`
2. Log the backup filename in the task status

#### How to Revert
- Revert files: `cd /home/claudeuser/agent && git checkout [commit-hash-or-tag]`
- Revert database: `PGPASSWORD=StrongPass123! pg_restore -h 127.0.0.1 -U agent_user -d marketing_agent --clean /var/backups/postgresql/[backup-file].dump`
- Revert everything to baseline: `cd /home/claudeuser/agent && git checkout baseline-2026-04-11`

#### Automated Backups (already running)
- Database: nightly at 2:00 AM, 7 days retained, /var/backups/postgresql/
- Files: nightly at 2:30 AM, 7 days retained, /var/backups/files/
- Git baseline: tagged as baseline-2026-04-11

#### NEVER
- Never delete backup files
- Never modify the backup scripts
- Never skip the pre-change git commit
