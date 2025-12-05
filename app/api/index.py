from fastapi import FastAPI
from fastapi.responses import HTMLResponse

class IndexHandler:
    async def index(self):
        return HTMLResponse(content="<h3>NSFW Detection API is running.</h3><p>Please visit <a href = 'https://github.com/helloxz/nsfw' target='_blank'>Github</a> to view the usage instructions.</p>", status_code=200)
        # 获取WEBUI是否开启
        import os
        webui = os.getenv("TOKEN", "on")
        if webui.lower() == "off":
            return HTMLResponse(content="<h1>NSFW Detection API is running.</h1>", status_code=200)
        else:
            html_path = "app/static/html/new_index.html"
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)