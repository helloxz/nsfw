#!/bin/bash

# 工作目录
WORKDIR="/opt/nsfw"
# 安装依赖
install_deps(){
    apt-get update
    apt-get install -y python3 python3-pip python3-venv procps
    mkdir -p  ${WORKDIR} && cd ${WORKDIR}
}

# 安装 Python 依赖
install_python_deps(){
    python3 -m venv myenv
    source myenv/bin/activate
    cd ${WORKDIR}
    pip3 install -r requirements.txt
}


# 清理缓存，缩小镜像体积
clean(){
    apt-get clean
    pip3 cache purge
    rm -rf /var/lib/apt/lists/*
}

install_deps && install_python_deps && clean