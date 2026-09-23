import uuid
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.api import deps
from app.db.session import SessionLocal
from app.utils.excel_handler import (
    process_students_file,
    process_employees_file,
    generate_students_template,
    generate_employees_template
)

router = APIRouter()
import_progress = {}

@router.get("/template/students")
def download_students_template(
    current_user = Depends(deps.get_current_active_admin)
):
    buf = generate_students_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_estudiantes_padres.xlsx"}
    )

@router.get("/template/employees")
def download_employees_template(
    current_user = Depends(deps.get_current_active_admin)
):
    buf = generate_employees_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_empleados_staff.xlsx"}
    )

@router.get("/status/{task_id}")
async def get_import_status(task_id: str):
    # Devolver 0 si no existe para evitar errores en el front
    return import_progress.get(task_id, {"progress": 0, "status": "processing"})

@router.post("/students")
async def import_students_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), # 'file' debe coincidir con formData.append('file', ...)
    current_user = Depends(deps.get_current_active_admin)
):
    task_id = str(uuid.uuid4())
    import_progress[task_id] = {"progress": 0, "status": "processing", "result": None}
    
    contents = await file.read()
    
    # Lanzar tarea en segundo plano
    background_tasks.add_task(run_async_import, task_id, contents, "students")
    
    return {"task_id": task_id}

@router.post("/employees")
async def import_employees_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user = Depends(deps.get_current_active_admin)
):
    task_id = str(uuid.uuid4())
    import_progress[task_id] = {"progress": 0, "status": "processing", "result": None}
    
    contents = await file.read()
    background_tasks.add_task(run_async_import, task_id, contents, "employees")
    
    return {"task_id": task_id}

def run_async_import(task_id: str, contents: bytes, import_type: str):
    db = SessionLocal()
    try:
        if import_type == "students":
            res = process_students_file(contents, db, task_id, import_progress)
        else:
            res = process_employees_file(contents, db, task_id, import_progress)
        
        import_progress[task_id].update({"progress": 100, "status": "completed", "result": res})
    except Exception as e:
        import_progress[task_id].update({"progress": 0, "status": "failed", "error": str(e)})
    finally:
        db.close()