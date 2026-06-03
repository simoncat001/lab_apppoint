ARG BASE_IMAGE=continuumio/miniconda3:latest
FROM ${BASE_IMAGE}

# 设置工作目录
WORKDIR /app

# 后端运行在独立 conda 环境中，避免依赖官方 Python slim 基础镜像。
ENV CONDA_ENV_NAME=nemo \
    PATH=/opt/conda/envs/nemo/bin:/opt/conda/bin:$PATH

# pip 下载容错参数（避免网络抖动导致构建失败）
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=12

# 可通过 --build-arg 覆盖镜像源
ARG CONDA_CHANNEL_MAIN=https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
ARG CONDA_CHANNEL_R=https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 安装系统依赖并创建 Python 3.12 conda 环境
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && conda create -y --override-channels \
    -c ${CONDA_CHANNEL_MAIN} \
    -c ${CONDA_CHANNEL_R} \
    -n ${CONDA_ENV_NAME} \
    python=3.12 \
    && conda clean -afy

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install \
    --no-cache-dir \
    --prefer-binary \
    --index-url ${PIP_INDEX_URL} \
    --trusted-host ${PIP_TRUSTED_HOST} \
    -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
