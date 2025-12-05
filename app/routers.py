from fastapi import APIRouter
from app.api.index import IndexHandler
from app.api.check import CheckHandler
from app.api.upload_check import UploadCheckHandler

index_handler = IndexHandler()
check_handler = CheckHandler()
upload_check_handler = UploadCheckHandler()

router = APIRouter()

router.get("/")(index_handler.index)
# 兼容旧接口
router.get("/check")(check_handler.check)
router.get("/api/url_check")(check_handler.check)
# 上传检测
router.post("/api/upload_check")(upload_check_handler.check)