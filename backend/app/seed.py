from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import DefectRecord, RepairRecord, MaintenanceTask, Notification

def seed_demo_data(db: Session):
    if db.scalar(select(func.count(DefectRecord.id))) > 0:
        return
    now = datetime.utcnow()
    records = [
        ("NR-18427", "Rajdhani Express", "AC malfunction", "Coach B2 · Unit 4", "Cooling drops below set point after 40 minutes of operation.", "High", "Inspection", 2, "Open"),
        ("NR-18427", "Rajdhani Express", "AC malfunction", "Coach B2 · Unit 4", "Cooling fault reported again on the same HVAC unit after coil cleaning.", "High", "Passenger feedback", 8, "Open"),
        ("NR-18427", "Rajdhani Express", "AC malfunction", "Coach B2 · Unit 4", "Repeated temperature fluctuation; compressor cycling remains irregular.", "Critical", "Inspection", 17, "Open"),
        ("WR-09113", "Deccan Queen", "Door malfunction", "Coach C1 · Door 2", "Door interlock does not engage consistently during test cycle.", "Critical", "Inspection", 1, "Open"),
        ("WR-09113", "Deccan Queen", "Door malfunction", "Coach C1 · Door 2", "Interlock fault returned following actuator replacement.", "High", "Maintenance log", 12, "Open"),
        ("ER-20551", "Howrah Mail", "Electrical fault", "Coach S4 · Panel 3", "Lighting circuit trips intermittently under load.", "High", "Inspection", 4, "Open"),
        ("ER-20551", "Howrah Mail", "Electrical fault", "Coach S4 · Panel 3", "Fuse carrier shows heat discoloration; repeat trip logged.", "Critical", "Maintenance log", 19, "Open"),
        ("CR-44108", "Intercity Express", "Water supply", "Coach D1 · Washroom", "Low water pressure at basin after pump service.", "Medium", "Passenger feedback", 5, "Open"),
        ("CR-44108", "Intercity Express", "Water supply", "Coach D1 · Washroom", "Pressure loss observed again during morning inspection.", "Medium", "Inspection", 23, "Open"),
        ("SR-77201", "Shatabdi Express", "Damaged fittings", "Coach E2 · Seat 18", "Fold-down table latch is loose and does not lock securely.", "Low", "Inspection", 3, "Open"),
        ("NR-32087", "Duronto Express", "AC malfunction", "Coach A3 · Unit 2", "Evaporator drain blockage causing moisture near the panel.", "High", "Inspection", 6, "Repair complete"),
        ("NR-32087", "Duronto Express", "AC malfunction", "Coach A3 · Unit 2", "Drain blockage recurred after flushing and hose replacement.", "High", "Maintenance log", 14, "Open"),
        ("WR-66713", "Pune Intercity", "Door malfunction", "Coach C3 · Door 1", "Door sensor alignment outside tolerance during inspection.", "Medium", "Inspection", 9, "Open"),
        ("ER-18302", "Coromandel Express", "Electrical fault", "Coach S2 · Reading light", "Passenger reading light circuit is unresponsive.", "Low", "Passenger feedback", 11, "Open"),
        ("CR-11579", "Mumbai Mail", "Water supply", "Coach B1 · Washroom", "Flush valve seal shows minor seepage.", "Low", "Inspection", 13, "Open"),
        ("SR-30174", "Chennai Express", "Damaged fittings", "Coach H1 · Berth 26", "Luggage hook has detached from the berth frame.", "Medium", "Passenger feedback", 15, "Open"),
        ("NR-93006", "Vande Bharat Express", "AC malfunction", "Coach C5 · Unit 1", "Return air filter differential pressure elevated.", "Medium", "Inspection", 21, "Open"),
        ("WR-61044", "Garib Rath", "Electrical fault", "Coach G2 · Panel 1", "Emergency light battery test below nominal duration.", "High", "Inspection", 25, "Open"),
        ("ER-45218", "Shalimar Express", "Water supply", "Coach B3 · Pantry", "Pump relay noise; flow rate remains within operating range.", "Low", "Maintenance log", 27, "Open"),
    ]
    inserted = []
    for coach, service, category, location, description, severity, source, days_ago, status in records:
        row = DefectRecord(coach_id=coach, service=service, category=category, location=location, description=description,
            severity=severity, source=source, reported_at=now-timedelta(days=days_ago), status=status,
            work_order_id=None)
        db.add(row); inserted.append(row)
    db.flush()
    repair_specs = [
        (inserted[0], 14, "Cleaned evaporator coil and recharged refrigerant to nominal pressure.", "A. Sharma", "Repair failed", 11, "Cooling dropped below target within one week."),
        (inserted[1], 6, "Replaced compressor contactor; performed 30-minute load test.", "R. Nair", "Awaiting verification", None, None),
        (inserted[3], 10, "Replaced door actuator and adjusted closing force.", "M. Das", "Recurrence detected", 3, "Interlock fault returned during depot test."),
        (inserted[5], 16, "Replaced fuse carrier and tightened panel connections.", "S. Iyer", "Awaiting verification", None, None),
        (inserted[7], 3, "Flushed supply line and replaced inline filter.", "P. Kumar", "Awaiting verification", None, None),
        (inserted[10], 12, "Replaced drain hose and cleared the condensate trap.", "A. Sharma", "Verified", 9, "Passed 45-minute operating test."),
    ]
    for i, (defect, repaired, summary, tech, verification, verified, notes) in enumerate(repair_specs, 1):
        work_order = f"WO-26-{4100+i}"
        defect.work_order_id = work_order
        db.add(RepairRecord(defect=defect, work_order_id=work_order, repaired_at=now-timedelta(days=repaired),
            repair_summary=summary, technician=tech, verification_status=verification,
            verified_at=now-timedelta(days=verified) if verified is not None else None, verification_notes=notes))
    # Priorities are seeded for open work that benefits from explicit queueing.
    task_specs = [
        (inserted[2], "CC-26041", "Critical", "Queued", "HVAC Response Team", "Parts available", 2, "Run a pressure and compressor cycle test; replace the expansion valve if unstable."),
        (inserted[4], "CC-26042", "Critical", "In progress", "Door Systems Team", "Technician assigned", 1, "Inspect wiring harness and interlock alignment before replacing more components."),
        (inserted[6], "CC-26043", "Critical", "Queued", "Electrical Team A", "Parts available", 1, "Isolate circuit, perform insulation resistance test, and replace heat-damaged carrier."),
        (inserted[11], "CC-26044", "High", "Queued", "HVAC Response Team", "Parts constrained", 1, "Check condensate routing and pan slope; verify under sustained cooling load."),
        (inserted[8], "CC-26045", "Medium", "Queued", "Plumbing Team", "Available", 1, "Test pump output and inspect non-return valve for intermittent restriction."),
        (inserted[9], "CC-26046", "Low", "Queued", "Interior Team", "Available", 0, "Replace latch assembly and confirm table locks under normal load."),
        (inserted[12], "CC-26047", "Medium", "Queued", "Door Systems Team", "Technician assigned", 0, "Calibrate sensor gap and validate door status from the cab panel."),
        (inserted[17], "CC-26048", "High", "Queued", "Electrical Team B", "Available", 0, "Run battery discharge test and renew the backup cell if capacity is below spec."),
    ]
    for defect, code, priority, status, team, resource, recurrence, action in task_specs:
        db.add(MaintenanceTask(defect=defect, task_code=code, priority=priority, status=status, assigned_team=team,
            resource_status=resource, due_date=now+timedelta(days=2 if priority == "Critical" else 5),
            recommended_action=action, recurrence_count=recurrence))
    db.add_all([
        Notification(title="Repeat defect detected", detail="AC malfunction has returned on coach NR-18427 after two interventions.", kind="critical", created_at=now-timedelta(minutes=18)),
        Notification(title="Verification due", detail="Three completed repairs are waiting for a depot verification outcome.", kind="warning", created_at=now-timedelta(hours=2)),
        Notification(title="Priority queue updated", detail="Critical electrical fault moved to the top of the maintenance queue.", kind="info", created_at=now-timedelta(hours=7)),
    ])
    db.commit()
