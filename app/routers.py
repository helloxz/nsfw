from fastapi import APIRouter
from app.api.index import IndexHandler
from app.api.url_check import UrlCheckHandler
from app.api.upload_check import UploadCheckHandler

index_handler = IndexHandler()
url_check_handler = UrlCheckHandler()
upload_check_handler = UploadCheckHandler()

router = APIRouter()

router.get("/")(index_handler.index)
# 兼容旧接口
router.get("/check")(url_check_handler.check)
router.get("/api/url_check")(url_check_handler.check)
# 支持POST方式的URL检测
router.post("/api/url_check")(url_check_handler.post_check)
# 上传检测
router.post("/api/upload_check")(upload_check_handler.check)