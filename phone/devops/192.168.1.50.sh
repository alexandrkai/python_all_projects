# копирвоание на телефон
ssh-copy-id -p 8022 -i ~/.ssh/id_rsa.pub u0_a108@192.168.1.50
# копирование на VPS
ssh-copy-id -p 443 -i ~/.ssh/id_ed25519.pub kai@159.200.241.127
ssh -p 8022 u0_a108@192.168.1.50

mkdir -p /data/data/com.termux/files/home/storage/shared/myfolder/projects/rest-api/app
cd  /data/data/com.termux/files/home/storage/shared/myfolder/projects/rest-api/app
sh run.sh HONOR8X
rsync -av -i -e 'ssh -p 8022' \
  --exclude=".venv" \
  --exclude="node_modules" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude=".git" \
  --exclude="logs/" \
  ./ u0_a108@192.168.1.50:/data/data/com.termux/files/home/storage/shared/myfolder/projects/rest-api




  pkg install rust binutils build-essential
  pip install maturin
  pip install fastapi --no-build-isolation