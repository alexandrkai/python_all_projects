ssh -p 443 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -D 9090 -N kai@179.255.186.215
:: type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh -p 443 kai@179.255.186.215 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

::ssh -p 443 kai@179.255.186.215
::sudo nano /etc/ssh/sshd_config
::AllowTcpForwarding yes