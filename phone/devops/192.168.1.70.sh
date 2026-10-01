ssh-copy-id -p 8022 -i ~/.ssh/id_rsa.pub u0_a199@192.168.1.70

cd  /data/data/com.termux/files/home/storage/shared/myfolder/projects/rest-api/app
sh run.sh HONOR20PRO
rsync -av -i -e 'ssh -p 8022' \
  --exclude=".venv" \
  --exclude="node_modules" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude=".git" \
  --exclude="logs/" \
  ./ u0_a199@192.168.1.70:/data/data/com.termux/files/home/storage/shared/myfolder/projects/rest-api/app