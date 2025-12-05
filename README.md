# helloxz/nsfw

## 关于

此项目基于[AdamCodd/vit-base-nsfw-detector/](https://huggingface.co/AdamCodd/vit-base-nsfw-detector/) 实现，并封装为HTTP API调用，可用于识别网络色情图像（nsfw识别），适合纯CPU机器推理，轻量级实现方案。

> 关于AdamCodd/vit-base-nsfw-detector：基于ViT架构的保守型NSFW检测模型，能识别真实图片和绘画中的敏感内容，但对AI生成图片准确率较低。

## 特点

* 纯CPU推理，适合大多数云服务器或VPS
* 支持的图片类型：jpg/png/bmp/webp
* 支持HTTP API调用
* 支持鉴权访问
* 轻量级实现
* 支持Docker私有部署

## 私有部署

### Docker部署

```bash
docker run -d \
  --name nsfw \
  -p 6086:6086 \
  --restart always \
  helloz/nsfw
```

### 使用Docker Compose部署（推荐）

新建`docker-compose.yaml`，内容如下：

```yaml
services:
  nsfw:
    container_name: nsfw
    image: helloz/nsfw
    ports:
      - "6086:6086"
    # 环境变量
    environment:
      - TOKEN=your_token_here
      - WORKERS=1
    restart: always
```

然后启动：`docker-compose up -d`


### 环境变量

* `TOKEN`：鉴权密钥（自行设置字符串），不设置则无需鉴权
* `WORKERS`：进程数量，默认1，多核CPU可增加此数值

## HTTP调用

未启用鉴权：

```
curl 'http://localhost:6086/check?url=https://s3.bmp.ovh/imgs/2025/09/13/30be084e818e9bbf.jpg'
```

启用鉴权：

```
curl 'http://localhost:6086/check?url=https://s3.bmp.ovh/imgs/2025/09/13/30be084e818e9bbf.jpg' \
--header 'Authorization: Bearer your_token_here'
```

返回值：

```json
{
    "code": 200,
    "msg": "success",
    "data": {
        "sfw": 0.0014,
        "nsfw": 0.9986,
        "is_nsfw": true
    }
}
```

* `code`：状态码，200视为成功，其余状态码视为失败
* `msg`：消息提示，错误时会显示具体原因
* `data.sfw`：安全系数`[0-1]`，值越高表示图片越安全
* `data.nsfw`：风险系数 `[0.0-1.0]`，值越高表示风险越高
* `is_nsfw`：当`nsfw>=0.8`时判定为色情图像，也可以自行根据`nsfw`分险系数判断

## 注意

此项目仅供学习和测试使用，请勿用于商业用途和生产环境，相关风险和责任需要您自行承担！

## 其它项目

如果您有兴趣，还可以了解我们的其他产品。

* [Zdir](https://www.zdir.pro/zh/) - 一款轻量级、多功能的文件分享程序。
* [OneNav](https://www.onenav.top/) - 高效的浏览器书签管理工具，将您的书签集中式管理。
* [Zurl](https://github.com/helloxz/zurl) - Zurl 是一款简单且实用的短链接系统，可以快速生成短链接，方便分享和管理。