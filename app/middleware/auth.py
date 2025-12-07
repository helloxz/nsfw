from fastapi import Request, HTTPException
from app.utils.helper import show_json
from typing import Callable
from fastapi.responses import JSONResponse

# 管理员认证中间件
async def auth(request: Request, call_next: Callable):
    # 获取路由路径
    path = request.url.path
    # 首页根目录，不需要鉴权
    if path == "/" or path.startswith("/docs"):
        return await call_next(request)
    # 从环境变量中获取TOKEN
    import os
    os_token = os.getenv("TOKEN", "")
    # print(f"Auth Middleware: os_token={os_token}")
    # 如果没获取到，则不进行鉴权，直接放行
    if not os_token:
        return await call_next(request)
    # 获取请求头中的token
    auth = request.headers.get("Authorization")
    if not auth:
        return JSONResponse(status_code=401, content={"code": 401, "msg": "Token invalid"})
    
    # token的格式是Bearer xxx
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return JSONResponse(status_code=401, content={"code": 401, "msg": "Token invalid"})
    # 从header中获取的token
    header_token = parts[1]
    # 与环境变量中的token对比
    if header_token != os_token:
        return JSONResponse(status_code=401, content={"code": 401, "msg": "Token invalid"})
    
    # 鉴权通过，放行
    response = await call_next(request)
    return response
