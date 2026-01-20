# server/main.py
import base64
import os
import time
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import smtplib

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Email configuration
EMAIL_HOST = os.getenv("SMTP_HOST") or os.getenv("EMAIL_HOST") or "smtp.gmail.com"
EMAIL_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("SMTP_PASS") or os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("SMTP_FROM") or EMAIL_USER or "no-reply@forensiclens.com"
EMAIL_USE_SSL = os.getenv("SMTP_SECURE", "false").lower() in ("1", "true", "yes")
EMAIL_MAX_RETRIES = int(os.getenv("EMAIL_MAX_RETRIES", "3"))
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "15"))

# CORS configuration
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app = FastAPI(title="ForensicLens Email Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Health check endpoint
@app.get("/api/health")
async def health():
    smtp_ok = bool(EMAIL_HOST and EMAIL_USER and EMAIL_PASS)
    return {
        "ok": True,
        "smtp_configured": smtp_ok,
        "smtp_host": EMAIL_HOST,
        "smtp_port": EMAIL_PORT,
        "smtp_user": EMAIL_USER,
        "smtp_from": EMAIL_FROM,
        "smtp_use_ssl": EMAIL_USE_SSL
    }

# DevTools endpoint
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def devtools_probe():
    return {}

# Favicon
FAV = Path(__file__).parent / "static" / "favicon.ico"
@app.get("/favicon.ico")
async def favicon():
    if FAV.exists():
        return FileResponse(FAV, media_type="image/x-icon")
    return JSONResponse(status_code=204, content={})

# Request model
class SendReportRequest(BaseModel):
    recipientEmail: EmailStr
    filename: str
    pdfBase64: str
    metadata: Optional[Dict[str, Any]] = None

def _send_email_smtp(
    to_address: str,
    subject: str,
    body: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None
) -> Dict[str, Any]:
    """Send email via SMTP with retry logic"""
    if not (EMAIL_HOST and EMAIL_USER and EMAIL_PASS):
        raise RuntimeError(
            f"SMTP not configured. Current values: HOST={EMAIL_HOST}, USER={EMAIL_USER}, PASS={'***' if EMAIL_PASS else 'None'}"
        )

    print(f"Attempting to send email via {EMAIL_HOST}:{EMAIL_PORT} (SSL={EMAIL_USE_SSL})")
    print(f"From: {EMAIL_FROM} -> To: {to_address}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_address
    msg.set_content(body or "Please find the attached ForensicLens report.")

    if attachment_bytes and attachment_filename:
        msg.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="pdf",
            filename=attachment_filename
        )

    last_exception = None
    for attempt in range(EMAIL_MAX_RETRIES + 1):
        try:
            if EMAIL_USE_SSL:
                # Direct SSL connection (port 465)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    EMAIL_HOST, 
                    EMAIL_PORT, 
                    context=context, 
                    timeout=EMAIL_TIMEOUT
                ) as server:
                    print(f"Connected to {EMAIL_HOST}:{EMAIL_PORT} via SSL")
                    server.login(EMAIL_USER, EMAIL_PASS)
                    print("Authentication successful")
                    server.send_message(msg)
                    print("Email sent successfully")
            else:
                # STARTTLS connection (port 587)
                with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=EMAIL_TIMEOUT) as server:
                    print(f"Connected to {EMAIL_HOST}:{EMAIL_PORT}")
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    print("STARTTLS enabled")
                    server.login(EMAIL_USER, EMAIL_PASS)
                    print("Authentication successful")
                    server.send_message(msg)
                    print("Email sent successfully")
            
            return {"ok": True, "message": "Email sent successfully", "attempt": attempt + 1}
        
        except smtplib.SMTPAuthenticationError as e:
            # Don't retry authentication errors
            print(f"SMTP Auth Error: {e}")
            raise RuntimeError(f"SMTP authentication failed: {str(e)}. Check your credentials.")
        
        except Exception as e:
            last_exception = e
            print(f"Attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < EMAIL_MAX_RETRIES:
                wait_time = min(2 ** attempt, 10)
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise RuntimeError(f"Failed to send email after {EMAIL_MAX_RETRIES + 1} attempts: {str(e)}")
    
    raise RuntimeError(f"Failed to send email: {str(last_exception)}")

# OPTIONS handler for CORS preflight
@app.options("/api/send-report")
async def send_report_options():
    return JSONResponse(content={"ok": True}, status_code=200)

# Main send-report endpoint
@app.post("/api/send-report")
async def send_report(payload: SendReportRequest):
    """Send forensic report via email"""
    try:
        # Decode base64 PDF
        try:
            pdf_bytes = base64.b64decode(payload.pdfBase64, validate=True)
            if len(pdf_bytes) == 0:
                raise ValueError("PDF is empty")
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid base64 PDF data: {str(e)}"
            )

        # Build email subject
        subject_parts = ["ForensicLens Report"]
        if payload.metadata and payload.metadata.get("caseRef"):
            subject_parts.append(f"- Case {payload.metadata['caseRef']}")
        subject = " ".join(subject_parts)

        # Build email body
        body_lines = ["ForensicLens 3D - Forensic Analysis Report", ""]
        if payload.metadata:
            if payload.metadata.get("generatedBy"):
                body_lines.append(f"Generated by: {payload.metadata['generatedBy']}")
            if payload.metadata.get("badgeId"):
                body_lines.append(f"Badge ID: {payload.metadata['badgeId']}")
            if payload.metadata.get("reportDate"):
                body_lines.append(f"Report Date: {payload.metadata['reportDate']}")
            if payload.metadata.get("caseRef"):
                body_lines.append(f"Case Reference: {payload.metadata['caseRef']}")
        body_lines.extend([
            "",
            "This email contains the official ForensicLens analysis report as a PDF attachment.",
            "",
            "CONFIDENTIAL - DO NOT DISTRIBUTE",
            "",
            "---",
            "ForensicLens 3D System"
        ])
        body = "\n".join(body_lines)

        # Send email
        result = _send_email_smtp(
            to_address=payload.recipientEmail,
            subject=subject,
            body=body,
            attachment_bytes=pdf_bytes,
            attachment_filename=payload.filename
        )

        return {
            "ok": True,
            "message": "Report sent successfully",
            "recipient": payload.recipientEmail,
            "filename": payload.filename,
            "details": result
        }

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while sending email: {str(e)}"
        )

# Mount static files for SPA (after API routes)
FRONTEND_DIST = Path(__file__).parent / "dist"
if FRONTEND_DIST.exists():
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    if (FRONTEND_DIST / "static").exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIST / "static")), name="static")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload