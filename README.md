# Llama3-Tutorial（Llama 3 超级课程）

带大家熟悉 Llama 3 微调、量化部署、评测全链路（基于书生·浦语大模型工具链）


<div align="center">
  <img src="https://github.com/SmartFlowAI/X-Llama3/assets/25839884/b2a9d3f1-3463-44aa-af77-7e1caa541aed" alt="image" width="200" height="200">
</div>

<div align="center">
欢迎加入 Llama 3 微信交流群～
</div>

## 实践教程（InternStudio 版）

### 环境配置

```shell
conda create -n llama3 python=3.10
conda activate llama3
conda install pytorch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 pytorch-cuda=12.1 -c pytorch -c nvidia
```

### 下载模型


安装 git-lfs 依赖

```shell
conda install git
git-lfs install
```
下载模型
```shell
mkdir -p ~/model
cd ~/model
git clone https://code.openxlab.org.cn/MrCat/Llama-3-8B-Instruct.git Meta-Llama-3-8B-Instruct
```
或者软链接 InternStudio 中的模型

```shell
ln -s /root/share/new_models/meta-llama/Meta-Llama-3-8B-Instruct ~/model/Meta-Llama-3-8B-Instruct
```

### Web Demo 部署

```shell
cd ~
git clone https://github.com/SmartFlowAI/Llama3-XTuner-CN
```

安装 XTuner 时会自动安装其他依赖
```shell
cd ~
git clone -b v0.1.18 https://github.com/InternLM/XTuner
cd XTuner
pip install -e .
```

运行 web_demo.py

```shell
streamlit run ~/Llama3-XTuner-CN/tools/internstudio_web_demo.py \
  /root/model/Llama-3-8B-Instruct
```

![image](https://github.com/SmartFlowAI/Llama3-XTuner-CN/assets/25839884/30ab70ea-9e60-4fed-a685-b3b3edbce7e6)


### XTuner 微调 Llama3 个人小助手认知

文档位于 [assistant.md](./docs/assistant.md)

### XTuner 微调 Llama3 图片理解多模态

文档位于 [llava.md](./docs/llava.md)

### XTuner+Agent-FLAN 微调 Llama 3 工具调用能力 (敬请期待)
