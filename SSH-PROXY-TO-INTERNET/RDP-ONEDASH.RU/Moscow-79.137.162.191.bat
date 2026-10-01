::type "%USERPROFILE%\.ssh\id_ed25519.pub" | ssh -p 443 kai@79.137.162.191 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
ssh -p 443 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -D 9090 -N kai@79.137.162.191

ssh -p 443 kai@79.137.162.191

sudo nano /etc/ssh/sshd_config
AllowTcpForwarding yes