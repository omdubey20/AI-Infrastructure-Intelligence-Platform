"""
Imunify360 Malware Monitoring Service
Integrates with cPanel / Imunify360 agents to automatically detect malware,
infected files, and malicious activity. Dispatches alerts to Microsoft Teams.
"""
import logging
import json
from datetime import datetime
from models import Server, SecurityAlert
from services.alerting_service import notify_alert
from services.server_scanner import connect_ssh, _run

logger = logging.getLogger(__name__)

def scan_server_for_malware(db, server: Server) -> list:
    """Execute Imunify360 malware detection scan on a server."""
    alerts_generated = []

    try:
        client = connect_ssh(server)
        if not client:
            return alerts_generated

        # Check if imunify360-agent exists
        has_imunify = _run(client, "which imunify360-agent 2>/dev/null", timeout=3)
        if not has_imunify or "not found" in has_imunify.lower():
            client.close()
            return alerts_generated

        # Run Imunify360 malware malicious list command
        cmd = "imunify360-agent malware malicious list --json"
        output = _run(client, cmd, timeout=15)
        client.close()

        if not output:
            return alerts_generated

        try:
            data = json.loads(output)
            items = data.get("items", [])
            
            if items:
                infected_count = len(items)
                sample_files = [item.get("file", "Unknown") for item in items[:3]]
                
                notify_alert(
                    db,
                    category="MALWARE_DETECTED",
                    target_name=server.name,
                    title=f"Critical Malware Detected on {server.name}",
                    description=f"Imunify360 detected {infected_count} malicious file(s) on server '{server.name}'. Examples: {', '.join(sample_files)}.",
                    severity="CRITICAL",
                    target_type="server",
                    target_id=server.id,
                    recommendation="Log in to WHM Imunify360 console immediately to quarantine or clean infected files.",
                )
                alerts_generated.append(f"Malware Detected ({infected_count} files)")
            else:
                # Auto-resolve malware alerts if clean
                db.query(SecurityAlert).filter(
                    SecurityAlert.target_name == server.name,
                    SecurityAlert.category == "MALWARE_DETECTED",
                    SecurityAlert.is_resolved == False
                ).update({"is_resolved": True, "resolved_at": datetime.utcnow()})
                db.commit()

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse Imunify360 JSON output on {server.name}")

    except Exception as e:
        logger.error(f"Error scanning malware on {server.name}: {e}")

    return alerts_generated
