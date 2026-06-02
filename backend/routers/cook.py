from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from dependencies import get_current_user
from schemas.cook import (
    StepExtractRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    SessionState,
    OcrFrameRequest,
    OcrFrameResponse,
    AdvanceStepResponse,
    RecipeStepOut,
)
from services.cook_service import (
    extract_recipe_steps,
    get_recipe_steps,
    create_session,
    get_session,
    get_user_sessions,
    advance_step,
    pause_session,
    resume_session,
    abandon_session,
    process_ocr_frame,
)
from logging_config import logger
import json

router = APIRouter(tags=["Live Cooking Assistance"])


@router.post("/api/cook/extract-steps")
async def api_extract_steps(req: StepExtractRequest):
    try:
        steps = extract_recipe_steps(req.recipe_id, req.markdown)
        return {"status": "success", "steps": steps}
    except Exception as e:
        logger.exception("Step extraction failed")
        raise HTTPException(status_code=500, detail=f"Step extraction failed: {e}")


@router.get("/api/cook/sessions")
async def api_list_sessions(
    user_id: str = Depends(get_current_user),
):
    sessions = get_user_sessions(user_id)
    return {"status": "success", "sessions": sessions}


@router.post("/api/cook/session")
async def api_create_session(
    req: CreateSessionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    try:
        session = create_session(user_id, req.recipe_id, background_tasks)
        if not session:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return {"status": "success", "session": session}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Session creation failed")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {e}")


@router.get("/api/cook/session/{session_id}")
async def api_get_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "session": session}


@router.post("/api/cook/session/{session_id}/step")
async def api_advance_step(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    result = advance_step(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"status": "success", **result}


@router.post("/api/cook/session/{session_id}/pause")
async def api_pause_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    pause_session(session_id)
    return {"status": "paused"}


@router.post("/api/cook/session/{session_id}/resume")
async def api_resume_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    resume_session(session_id)
    return {"status": "resumed"}


@router.post("/api/cook/session/{session_id}/abandon")
async def api_abandon_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    abandon_session(session_id)
    return {"status": "abandoned"}


@router.post("/api/cook/session/{session_id}/ocr")
async def api_ocr_frame(
    session_id: str,
    req: OcrFrameRequest,
    user_id: str = Depends(get_current_user),
):
    try:
        result = process_ocr_frame(session_id, req.image, freeform=False)
        return {"status": "success", "ocr": result}
    except Exception as e:
        logger.exception("OCR frame processing failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")


@router.post("/api/cook/session/{session_id}/ocr-freeform")
async def api_ocr_freeform(
    session_id: str,
    req: OcrFrameRequest,
    user_id: str = Depends(get_current_user),
):
    try:
        result = process_ocr_frame(session_id, req.image, freeform=True)
        return {"status": "success", "ocr": result}
    except Exception as e:
        logger.exception("Freeform OCR failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")


@router.websocket("/ws/cook/{session_id}")
async def cook_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")

            if action == "next_step":
                result = advance_step(session_id)
                if "error" in result:
                    await websocket.send_json({"type": "error", "detail": result["error"]})
                else:
                    await websocket.send_json({"type": "step_update", **result})

            elif action == "ocr_snapshot":
                image = data.get("image", "")
                freeform = data.get("freeform", False)
                result = process_ocr_frame(session_id, image, freeform=freeform)
                await websocket.send_json({"type": "ocr_result", "ocr": result})

            elif action == "pause":
                pause_session(session_id)
                await websocket.send_json({"type": "status", "status": "paused"})

            elif action == "resume":
                resume_session(session_id)
                await websocket.send_json({"type": "status", "status": "resumed"})

            elif action == "abandon":
                abandon_session(session_id)
                await websocket.send_json({"type": "status", "status": "abandoned"})

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({"type": "error", "detail": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for session {session_id}")
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
