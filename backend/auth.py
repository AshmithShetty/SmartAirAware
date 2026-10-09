import os
from typing import Optional
from fastapi import Header, HTTPException, status

def verify_admin_key(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")) -> bool:
    expected_key = os.getenv("ADMIN_KEY", "")
    if not x_admin_key or not expected_key or x_admin_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key header"
        )
    return True
