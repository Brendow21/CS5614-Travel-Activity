#!/bin/bash
#SBATCH --nodes=1                   # Request a single node
#SBATCH --ntasks-per-node=2         # Request 2 CPU cores
#SBATCH --time=15:00:00              # Set a 1-hour time limit
#SBATCH --partition=a30_normal_q   # Specify the GPU partition: h200_normal_q, a100_normal_q on Tinkercliffs | a30_normal_q on Falcon
#SBATCH --account=ece_6514          # Your class-specific account
#SBATCH --gres=gpu:1                # Request 1 GPU
#SBATCH -o logs/%x-%j.out          # output logs/
#SBATCH -e logs/%x-%j.err          # error logs/

source ~/.bashrc
eval "$(conda shell.bash hook)"
module load Miniforge3/24.11.3-0
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate /home/chuanl/.conda/envs/dtf

#set -euo pipefail
set +e   # 不要在第一错误时退出
mkdir -p logs

echo "Starting Optuna Tuning Script..."
# 运行主程序
python main.py

# 运行测试
pytest tests/test_system.py -v