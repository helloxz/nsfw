from app.utils.helper import show_json
import re
import io
import numpy as np
from PIL import Image
import onnxruntime as ort
import httpx

# 允许的MIME类型
ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
}
# 最大大小 10MB
MAX_SIZE = 10 * 1024 * 1024
# UA 与超时
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
TIMEOUT = 20.0
MODEL_PATH = "app/onnx/model_q4.onnx"

# 全局加载一次 ONNX 模型，避免重复初始化带来的性能损耗
try:
    ORT_SESSION = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    ORT_INPUT_NAME = ORT_SESSION.get_inputs()[0].name
except Exception as e:
    ORT_SESSION = None
    ORT_INPUT_NAME = None

def _is_valid_url(url: str) -> bool:
    # 简单URL合法性校验（仅允许 http/https）
    if not isinstance(url, str):
        return False
    return re.match(r"^https?://", url) is not None

def _softmax(x: np.ndarray) -> np.ndarray:
    # 数值稳定的softmax
    x = x.astype(np.float32)
    x = x - np.max(x)
    ex = np.exp(x)
    return ex / np.sum(ex)

def _preprocess(image: Image.Image) -> np.ndarray:
    # 预处理：RGB、resize到384x384、归一化、CHW、batch维度
    img = image.convert("RGB").resize((384, 384))
    x = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    x = (x - mean) / std
    x = np.transpose(x, (2, 0, 1))
    x = np.expand_dims(x, axis=0)
    return x

def _infer(image: Image.Image):
    if ORT_SESSION is None:
        return None, "Model not initialized, please check model_q4.onnx exists and is loadable."
    inputs = _preprocess(image)
    outputs = ORT_SESSION.run(None, {ORT_INPUT_NAME: inputs})

    # 兼容稀疏输出：如果是 SparseTensor/OrtValue，先转稠密
    out0 = outputs[0]
    # 某些版本会返回具有 to_dense 方法的稀疏对象
    if hasattr(out0, "to_dense"):
        try:
            out0 = out0.to_dense() # type: ignore
        except Exception:
            return None, "Model output conversion failed (sparse to dense)."
    # 如果是 OrtValue，尽量转为 numpy
    try:
        if hasattr(out0, "numpy"):
            out0 = out0.numpy() # type: ignore
    except Exception:
        pass

    # 统一为 numpy 数组
    logits_arr = np.array(out0)
    # 兼容不同输出形状，取第一个样本的 logits
    if logits_arr.ndim == 1:
        logits = logits_arr
    elif logits_arr.ndim >= 2:
        logits = logits_arr[0]
    else:
        return None, "Invalid model output shape."

    probs = _softmax(logits)
    sfw_raw, nsfw_raw = float(probs[0]), float(probs[1])
    # 保留4位小数（仅用于返回），阈值判定使用原始概率
    sfw_prob = round(sfw_raw, 4)
    nsfw_prob = round(nsfw_raw, 4)
    is_nsfw = nsfw_raw > 0.8
    return {"sfw": sfw_prob, "nsfw": nsfw_prob, "is_nsfw": is_nsfw}, None

class UrlCheckHandler:
    async def check(self, url: str):
        # 1. URL合法性校验
        if not _is_valid_url(url):
            return show_json(-1000, "Invalid URL, only http/https are supported.")

        # 2. 通过HTTP头获取类型与大小（尽量避免不必要下载）
        headers = {
            "User-Agent": UA,
            "Referer": url,
            "Accept": "image/*"
        }

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                # 尝试HEAD以获取内容类型与大小
                head_resp = await client.head(url, headers=headers)
                # 某些服务可能不支持HEAD，回退GET但不读取主体
                if head_resp.status_code >= 400:
                    head_resp = await client.get(url, headers=headers)
                    await head_resp.aclose()

                content_type = head_resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
                # print("Content-Type from HEAD:", content_type)
                content_length = head_resp.headers.get("Content-Length")

                # MIME校验
                if content_type not in ALLOWED_MIME:
                    return show_json(-1000, f"Unsupported file type: {content_type or 'unknown'}, only jpg/png/bmp/webp allowed.")

                # 大小校验（头部）
                if content_length:
                    try:
                        cl = int(content_length)
                        if cl > MAX_SIZE:
                            return show_json(-1000, "File too large (>10MB), refusing to download.")
                    except ValueError:
                        pass  # 无法解析则继续后续流程

                # 3. 下载文件（流式），避免超大内存使用
                get_resp = await client.get(url, headers=headers)
                if get_resp.status_code >= 400:
                    return show_json(-1000, f"Download failed, status code: {get_resp.status_code}")

                data = get_resp.content

        except httpx.TimeoutException:
            return show_json(-1000, "Request timed out (>20s).")
        except httpx.RequestError as e:
            return show_json(-1000, f"Network request error: {str(e)}")
        except Exception as e:
            return show_json(-1000, f"Unknown error: {str(e)}")

        # 4. 下载后再次检查大小
        if len(data) > MAX_SIZE:
            return show_json(-1000, "File too large (>10MB), refusing to process.")

        # 5. 打开并校验图像
        try:
            image = Image.open(io.BytesIO(data))
        except Exception:
            return show_json(-1000, "Image parsing failed.")

        # 6. 推理
        result, err = _infer(image)
        if err:
            return show_json(-1000, err)

        # 7. 返回结果
        return show_json(200, "success", result)
    
    # 通过POST方式传递URL
    async def post_check(self, req: dict):
        url = req.get("url", "")
        # 1. URL合法性校验
        if not _is_valid_url(url):
            return show_json(-1000, "Invalid URL, only http/https are supported.")

        # 2. 通过HTTP头获取类型与大小（尽量避免不必要下载）
        headers = {
            "User-Agent": UA,
            "Referer": url,
            "Accept": "image/*"
        }

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                # 尝试HEAD以获取内容类型与大小
                head_resp = await client.head(url, headers=headers)
                # 某些服务可能不支持HEAD，回退GET但不读取主体
                if head_resp.status_code >= 400:
                    head_resp = await client.get(url, headers=headers)
                    await head_resp.aclose()

                content_type = head_resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
                # print("Content-Type from HEAD:", content_type)
                content_length = head_resp.headers.get("Content-Length")

                # MIME校验
                if content_type not in ALLOWED_MIME:
                    return show_json(-1000, f"Unsupported file type: {content_type or 'unknown'}, only jpg/png/bmp/webp allowed.")

                # 大小校验（头部）
                if content_length:
                    try:
                        cl = int(content_length)
                        if cl > MAX_SIZE:
                            return show_json(-1000, "File too large (>10MB), refusing to download.")
                    except ValueError:
                        pass  # 无法解析则继续后续流程

                # 3. 下载文件（流式），避免超大内存使用
                get_resp = await client.get(url, headers=headers)
                if get_resp.status_code >= 400:
                    return show_json(-1000, f"Download failed, status code: {get_resp.status_code}")

                data = get_resp.content

        except httpx.TimeoutException:
            return show_json(-1000, "Request timed out (>20s).")
        except httpx.RequestError as e:
            return show_json(-1000, f"Network request error: {str(e)}")
        except Exception as e:
            return show_json(-1000, f"Unknown error: {str(e)}")

        # 4. 下载后再次检查大小
        if len(data) > MAX_SIZE:
            return show_json(-1000, "File too large (>10MB), refusing to process.")

        # 5. 打开并校验图像
        try:
            image = Image.open(io.BytesIO(data))
        except Exception:
            return show_json(-1000, "Image parsing failed.")

        # 6. 推理
        result, err = _infer(image)
        if err:
            return show_json(-1000, err)

        # 7. 返回结果
        return show_json(200, "success", result)