from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/eap/status")
async def eap_status():
    return {"enabled": False, "message": "EAP integration placeholder"}


@router.post("/eap/push")
async def eap_push():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="EAP integration not configured")
