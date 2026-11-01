from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload
from .database import Base, engine, get_db
from .models import DefectRecord, RepairRecord, MaintenanceTask, Notification
from .schemas import PriorityUpdate, VerificationUpdate, DefectCreate
from .seed import seed_demo_data

Base.metadata.create_all(bind=engine)
with next(get_db()) as _db:
    seed_demo_data(_db)

app = FastAPI(title="CoachCare API", version="1.0.0", description="Railway maintenance intelligence demo API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def record_dict(r: DefectRecord, recurrence_count: int = 0, latest_repair: RepairRecord | None = None) -> dict[str, Any]:
    return {"id": r.id, "coach_id": r.coach_id, "service": r.service, "category": r.category, "location": r.location,
        "description": r.description, "severity": r.severity, "source": r.source, "reported_at": r.reported_at.isoformat(),
        "status": r.status, "work_order_id": r.work_order_id, "recurrence_count": recurrence_count,
        "last_repair": latest_repair.repaired_at.isoformat() if latest_repair else None,
        "repair_summary": latest_repair.repair_summary if latest_repair else None,
        "verification_status": latest_repair.verification_status if latest_repair else None}

def cluster_records(db: Session):
    records = db.scalars(select(DefectRecord).options(selectinload(DefectRecord.repairs)).order_by(DefectRecord.reported_at.desc())).all()
    tasks = db.scalars(select(MaintenanceTask)).all()
    groups: dict[tuple[str, str, str], list[DefectRecord]] = defaultdict(list)
    for r in records:
        groups[(r.coach_id, r.category, r.location)].append(r)
    result = []
    for key, rows in groups.items():
        rows_asc = sorted(rows, key=lambda x: x.reported_at)
        recent = rows[0]
        repairs = sorted([rep for row in rows for rep in row.repairs], key=lambda x: x.repaired_at, reverse=True)
        linked_task = next((task for task in tasks if task.defect_id == recent.id), None)
        if linked_task is None:
            linked_task = next((task for task in tasks if task.defect_id in {row.id for row in rows}), None)
        recurrence = max(0, len(rows)-1)
        last_repair = repairs[0] if repairs else None
        result.append({**record_dict(recent, recurrence, last_repair), "record_count": len(rows), "first_reported": rows_asc[0].reported_at.isoformat(),
            "recommended_action": linked_task.recommended_action if linked_task else "Inspect the root cause and confirm the fault under operating conditions.",
            "repair_count": len(repairs), "history": [record_dict(row, max(0, len([p for p in rows_asc if p.reported_at <= row.reported_at])-1),
                max(row.repairs, key=lambda x: x.repaired_at) if row.repairs else None) for row in rows_asc]})
    return result

def task_dict(t: MaintenanceTask):
    d = t.defect
    return {"id": t.id, "task_code": t.task_code, "defect_id": d.id, "coach_id": d.coach_id, "service": d.service,
        "category": d.category, "location": d.location, "description": d.description, "severity": d.severity,
        "priority": calculated_priority(t), "status": t.status, "assigned_team": t.assigned_team, "resource_status": t.resource_status,
        "due_date": t.due_date.isoformat(), "recurrence_count": t.recurrence_count, "recommended_action": t.recommended_action}

def calculated_priority(task: MaintenanceTask) -> str:
    severity_weight = {"Critical": 80, "High": 60, "Medium": 40, "Low": 20}.get(task.defect.severity, 20)
    recurrence_weight = min(task.recurrence_count, 2) * 15
    resource = task.resource_status.lower()
    resource_weight = 0 if "constrain" in resource or "assessment" in resource else 3 if "assigned" in resource else 5
    score = severity_weight + recurrence_weight + resource_weight
    if score >= 75: return "Critical"
    if score >= 55: return "High"
    if score >= 35: return "Medium"
    return "Low"

@app.get("/api/health")
def health(): return {"status": "ok", "service": "CoachCare API"}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.utcnow(); day30 = now-timedelta(days=30); day60 = now-timedelta(days=60)
    records = db.scalars(select(DefectRecord).options(selectinload(DefectRecord.repairs)).order_by(DefectRecord.reported_at)).all()
    tasks = db.scalars(select(MaintenanceTask)).all()
    repairs = db.scalars(select(RepairRecord)).all()
    by_key = defaultdict(int)
    recurring_categories = defaultdict(int)
    trend = []
    running = defaultdict(int)
    for r in records:
        key=(r.coach_id,r.category,r.location)
        if r.reported_at >= day30:
            is_repeat = running[key] > 0
            trend.append((r.reported_at, is_repeat, r.category))
        running[key] += 1
        by_key[key] += 1
    for r in records:
        key=(r.coach_id,r.category,r.location)
        if by_key[key] > 1:
            recurring_categories[r.category] += 1
    chart_categories = [{"category": k, "count": v} for k,v in sorted(recurring_categories.items(), key=lambda x: -x[1])]
    # Daily points are based on the full date range, including quiet days.
    trend_by_day = defaultdict(lambda: {"reports": 0, "recurring": 0})
    for r in records:
        if r.reported_at >= day30:
            stamp=r.reported_at.date().isoformat(); trend_by_day[stamp]["reports"] += 1
    seen=set()
    for r in records:
        if r.reported_at >= day30:
            key=(r.coach_id,r.category,r.location)
            if key in seen: trend_by_day[r.reported_at.date().isoformat()]["recurring"] += 1
            seen.add(key)
    trend_data=[]
    for i in range(30):
        d=(day30.date()+timedelta(days=i)); vals=trend_by_day[d.isoformat()]
        trend_data.append({"date": d.strftime("%b %d"), "reports": vals["reports"], "recurring": vals["recurring"]})
    priority_counts={p: sum(1 for t in tasks if calculated_priority(t)==p and t.status!="Completed") for p in ["Critical","High","Medium","Low"]}
    clusters=cluster_records(db)
    attention=[c for c in clusters if c["recurrence_count"]>0 and (c["status"]!="Repair complete" or c["verification_status"] in ("Repair failed","Recurrence detected"))]
    attention.sort(key=lambda c: (c["severity"] not in ("Critical","High"), -c["recurrence_count"], c["reported_at"]))
    activity=[]
    for r in records:
        activity.append({"id":f"d-{r.id}","type":"reported","title":f"{r.category} reported","detail":f"{r.coach_id} · {r.location}","at":r.reported_at.isoformat(),"tone":"blue"})
    for repair in repairs:
        activity.append({"id":f"r-{repair.id}","type":"repair","title":"Repair completed","detail":f"{repair.work_order_id} · {repair.defect.coach_id}","at":repair.repaired_at.isoformat(),"tone":"amber"})
        if repair.verified_at:
            activity.append({"id":f"v-{repair.id}","type":"verification","title":repair.verification_status,"detail":f"{repair.work_order_id} · {repair.defect.coach_id}","at":repair.verified_at.isoformat(),"tone":"green" if repair.verification_status=="Verified" else "red"})
    activity.sort(key=lambda x:x["at"], reverse=True)
    previous_count=sum(1 for r in records if day60 <= r.reported_at < day30)
    current_count=sum(1 for r in records if day30 <= r.reported_at <= now)
    prev_recurring=len({(r.coach_id,r.category,r.location) for r in records if day60<=r.reported_at<day30})
    curr_recurring=len({(r.coach_id,r.category,r.location) for r in records if day30<=r.reported_at<=now and by_key[(r.coach_id,r.category,r.location)]>1})
    return {"metrics":{"total_defect_records":len(records),"recurring_defects":sum(1 for c in clusters if c["recurrence_count"]>0),
        "high_priority_tasks":sum(1 for t in tasks if calculated_priority(t) in ("Critical","High") and t.status!="Completed"),
        "awaiting_verification":sum(1 for r in repairs if r.verification_status=="Awaiting verification"),
        "period_comparison":{"records_current":current_count,"records_previous":previous_count,"recurring_current":curr_recurring,"recurring_previous":prev_recurring}},
        "recurring_by_category":chart_categories,"trend":trend_data,"priority_distribution":[{"priority":p,"count":n} for p,n in priority_counts.items()],
        "activity":activity[:7],"attention":attention[:6]}

@app.get("/api/recurring-defects")
def recurring_defects(q: str = "", category: str = "All", severity: str = "All", include_all: bool = False, db: Session = Depends(get_db)):
    rows=cluster_records(db)
    if not include_all: rows=[c for c in rows if c["recurrence_count"]>0]
    if category!="All": rows=[c for c in rows if c["category"]==category]
    if severity!="All": rows=[c for c in rows if c["severity"]==severity]
    if q:
        needle=q.lower(); rows=[c for c in rows if needle in " ".join(str(c.get(k,"")) for k in ("coach_id","category","location","service","work_order_id")).lower()]
    rows.sort(key=lambda c:(c["severity"] not in ("Critical","High"),-c["recurrence_count"],c["reported_at"]))
    return {"items":rows,"total":len(rows)}

@app.get("/api/recurring-defects/{defect_id}")
def recurring_defect_detail(defect_id: int, db: Session = Depends(get_db)):
    row=db.get(DefectRecord, defect_id)
    if not row: raise HTTPException(404,"Defect record not found")
    key=(row.coach_id,row.category,row.location)
    cluster=next((c for c in cluster_records(db) if (c["coach_id"],c["category"],c["location"])==key),None)
    return cluster or record_dict(row)

@app.get("/api/priorities")
def priorities(q: str = "", priority: str = "All", status: str = "All", db: Session = Depends(get_db)):
    query=select(MaintenanceTask).options(selectinload(MaintenanceTask.defect)).order_by(MaintenanceTask.priority, MaintenanceTask.due_date)
    tasks=db.scalars(query).all()
    order={"Critical":0,"High":1,"Medium":2,"Low":3}
    tasks.sort(key=lambda t:(order.get(calculated_priority(t),4),t.due_date))
    rows=[task_dict(t) for t in tasks]
    if priority=="Critical + High": rows=[r for r in rows if r["priority"] in ("Critical","High")]
    elif priority!="All": rows=[r for r in rows if r["priority"]==priority]
    if status!="All": rows=[r for r in rows if r["status"]==status]
    if q:
        needle=q.lower(); rows=[r for r in rows if needle in " ".join(str(r.get(k,"")) for k in ("task_code","coach_id","category","assigned_team")).lower()]
    return {"items":rows,"total":len(rows)}

@app.patch("/api/priorities/{task_id}")
def update_priority(task_id: int, payload: PriorityUpdate, db: Session = Depends(get_db)):
    task=db.get(MaintenanceTask, task_id)
    if not task: raise HTTPException(404,"Maintenance task not found")
    if payload.status is not None: task.status=payload.status
    if payload.assigned_team is not None: task.assigned_team=payload.assigned_team.strip()
    db.commit(); db.refresh(task)
    return task_dict(task)

@app.get("/api/verification")
def verifications(status: str = "All", q: str = "", db: Session = Depends(get_db)):
    repairs=db.scalars(select(RepairRecord).options(selectinload(RepairRecord.defect)).order_by(RepairRecord.repaired_at.desc())).all()
    items=[]
    for r in repairs:
        d=r.defect
        items.append({"id":r.id,"defect_id":d.id,"work_order_id":r.work_order_id,"coach_id":d.coach_id,"service":d.service,
            "category":d.category,"location":d.location,"repair_summary":r.repair_summary,"technician":r.technician,
            "repaired_at":r.repaired_at.isoformat(),"verification_status":r.verification_status,
            "verified_at":r.verified_at.isoformat() if r.verified_at else None,"verification_notes":r.verification_notes})
    if status!="All": items=[i for i in items if i["verification_status"]==status]
    if q:
        needle=q.lower(); items=[i for i in items if needle in " ".join(str(i.get(k,"")) for k in ("coach_id","work_order_id","category","technician")).lower()]
    return {"items":items,"total":len(items)}

@app.post("/api/verification/{repair_id}")
def verify_repair(repair_id: int, payload: VerificationUpdate, db: Session = Depends(get_db)):
    repair=db.get(RepairRecord, repair_id)
    if not repair: raise HTTPException(404,"Repair record not found")
    repair.verification_status=payload.outcome; repair.verified_at=datetime.utcnow(); repair.verification_notes=payload.notes.strip()
    if payload.outcome in ("Repair failed","Recurrence detected"):
        repair.defect.status="Open"
    db.commit(); db.refresh(repair)
    return {"id":repair.id,"verification_status":repair.verification_status,"verified_at":repair.verified_at.isoformat(),"verification_notes":repair.verification_notes}

@app.get("/api/notifications")
def notifications(db: Session = Depends(get_db)):
    rows=db.scalars(select(Notification).order_by(Notification.created_at.desc())).all()
    return {"items":[{"id":n.id,"title":n.title,"detail":n.detail,"kind":n.kind,"created_at":n.created_at.isoformat(),"read":n.read} for n in rows],"unread":sum(not n.read for n in rows)}

@app.post("/api/defects")
def create_defect(payload: DefectCreate, db: Session = Depends(get_db)):
    prior_reports=db.scalar(select(func.count(DefectRecord.id)).where(DefectRecord.coach_id==payload.coach_id,
        DefectRecord.category==payload.category,DefectRecord.location==payload.location)) or 0
    row=DefectRecord(**payload.model_dump(), reported_at=datetime.utcnow(), status="Open")
    db.add(row); db.commit(); db.refresh(row)
    # Create a queue entry so reported work can be triaged immediately.
    priority=payload.severity if payload.severity in ("Critical","High") else payload.severity
    task=MaintenanceTask(defect_id=row.id,task_code=f"CC-{datetime.utcnow():%y%m%d}-{row.id:03d}",priority=priority,status="Queued",
        assigned_team="Unassigned",resource_status="Assessment required",due_date=datetime.utcnow()+timedelta(days=4),
        recommended_action="Review the new finding, confirm recurrence history, and plan an inspection.",recurrence_count=prior_reports)
    db.add(task); db.commit()
    return record_dict(row)

@app.get("/api/search")
def search(q: str = Query(min_length=1, max_length=80), db: Session = Depends(get_db)):
    like=f"%{q}%"
    defects=db.scalars(select(DefectRecord).where(or_(DefectRecord.coach_id.ilike(like),DefectRecord.category.ilike(like),DefectRecord.work_order_id.ilike(like))).order_by(DefectRecord.reported_at.desc()).limit(8)).all()
    tasks=db.scalars(select(MaintenanceTask).where(MaintenanceTask.task_code.ilike(like)).limit(4)).all()
    return {"items":[{"id":r.id,"coach_id":r.coach_id,"category":r.category,"location":r.location,"label":f"{r.coach_id} · {r.category}","detail":r.location,"type":"defect","path":f"/recurring-defects/{r.id}"} for r in defects] +
        [{"id":t.id,"label":t.task_code,"detail":f"{t.defect.coach_id} · {t.defect.category}","type":"work_order","path":"/maintenance-priorities"} for t in tasks]}
