from app.utils.helper import show_json
from fastapi import Request, UploadFile
import io
from PIL import Image
from app.api.check import ALLOWED_MIME, MAX_SIZE, _infer

# 仅用于将 PIL 的格式名映射到标准 MIME（以实际解码结果为准）
FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "BMP": "image/bmp",
    "WEBP": "image/webp",
}

class UploadCheckHandler:
    # 新增：通用关闭与推理辅助
    async def _safe_close(self, upload: UploadFile):
        try:
            await upload.close()
        except Exception:
            try:
                upload.file.close()
            except Exception:
                pass

    async def _infer_bytes(self, data: bytes):
        if not data:
            return show_json(-1000, "Empty upload.")
        if len(data) > MAX_SIZE:
            return show_json(-1000, "File too large (>10MB), refusing to process.")

        image = None
        try:
            image = Image.open(io.BytesIO(data))
            fmt = getattr(image, "format", None)
            detected_mime = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "BMP": "image/bmp",
                "WEBP": "image/webp",
            }.get(fmt or "", "")
            if detected_mime not in ALLOWED_MIME:
                return show_json(-1000, f"Unsupported file type: {detected_mime or 'unknown'}, only jpg/png/bmp/webp allowed.")
            result, err = _infer(image)
        except Exception:
            return show_json(-1000, "Image parsing failed.")
        finally:
            try:
                if image is not None:
                    image.close()
            except Exception:
                pass

        if err:
            return show_json(-1000, err)
        return show_json(200, "success", result)

    async def check(self, request: Request, file: UploadFile):
        # 1) 头部大小预检（快速拒绝；multipart 开销可能导致略大于真实文件）
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_SIZE:
                    return show_json(-1000, "File too large (>10MB), refusing to process.")
            except ValueError:
                pass

        # 2) 读取文件（限流 MAX_SIZE+1）
        try:
            data = await file.read(MAX_SIZE + 1)
        except Exception:
            await self._safe_close(file)
            return show_json(-1000, "Read uploaded file failed.")
        finally:
            await self._safe_close(file)

        if len(data) > MAX_SIZE:
            return show_json(-1000, "File too large (>10MB), refusing to process.")

        # 3) 解码+真实 MIME 校验 + 推理
        return await self._infer_bytes(data)