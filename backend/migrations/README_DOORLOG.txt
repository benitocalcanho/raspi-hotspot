# DoorLog Table Migration

If you use Flask-Migrate/Alembic:
1. Generate migration:
   flask db migrate -m "add door_log table"
2. Apply migration:
   flask db upgrade

If you use manual migration:
- Add the door_log table to your database schema as per backend/models/door_log.py.

Table fields:
- id (int, primary key)
- timestamp (datetime, not null)
- state (string, not null)
- source (string, nullable)
