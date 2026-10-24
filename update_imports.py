import re

with open('/workspace/app/main.py', 'r') as f:
    content = f.read()

# Add disaster_recovery import after scan_alert_triggers import
content = content.replace(
    'from agents.proactive_alerts import scan_alert_triggers',
    '''from agents.proactive_alerts import scan_alert_triggers
from agents.disaster_recovery import (
    run_backup,
    verify_backup,
    run_dr_drill,
    watchdog_check,
    mitigate_incident,
    resolve_incident,
)'''
)

# Add new database imports
content = content.replace(
    'get_active_client_projects,',
    '''get_active_client_projects,
    get_backup,
    get_latest_backup,
    save_backup,
    get_incident,
    get_open_incidents,
    get_incidents_by_type_open,
    save_incident,
    save_drill,'''
)

# Add new model imports
content = content.replace(
    'TicketStatus,',
    '''TicketStatus,
    BackupRecord,
    BackupType,
    BackupStatus,
    Incident,
    IncidentType,
    IncidentSeverity,
    IncidentStatus,
    DrillResult,
    DrillStatus,'''
)

with open('/workspace/app/main.py', 'w') as f:
    f.write(content)

print("Imports updated successfully")