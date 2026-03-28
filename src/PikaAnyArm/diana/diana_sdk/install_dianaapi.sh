#!/bin/bash

set -e  # 遇到错误立即停止

echo "Step 1: Install Python package to USER environment (No Root needed)..."
# 修改点 1: 添加 --user 参数
python -m pip install --user .

echo "Step 2: Detect USER site-packages path..."
# 修改点 2: 使用 getusersitepackages() 获取 ~/.local 下的路径
SITE_PACKAGES=$(python3 -c "import site; print(site.getusersitepackages())")
TARGET_DIR="$SITE_PACKAGES/diana_robot"

echo "Detected installation path: $TARGET_DIR"

echo "Step 3: Check and set LD_LIBRARY_PATH in ~/.bashrc ..."
LD_PATH_LINE="export LD_LIBRARY_PATH=$TARGET_DIR:\$LD_LIBRARY_PATH"

# 检查是否已经存在，避免重复添加
if ! grep -Fxq "$LD_PATH_LINE" ~/.bashrc; then
    echo "$LD_PATH_LINE" >> ~/.bashrc
    echo "LD_LIBRARY_PATH added to ~/.bashrc"
else
    echo "LD_LIBRARY_PATH already exists in ~/.bashrc"
fi

echo "Step 4: Make LD_LIBRARY_PATH effective for current shell..."
export LD_LIBRARY_PATH=$TARGET_DIR:$LD_LIBRARY_PATH

echo "Installation finished! Please run 'source ~/.bashrc' manually."