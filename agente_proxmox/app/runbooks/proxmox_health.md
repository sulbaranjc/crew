# Runbook: Proxmox Health Check

1. Verificar estado del cluster (`/api2/json/cluster/status`)
2. Listar nodos y revisar estado (`/api2/json/nodes`)
3. Revisar recursos del cluster (`/api2/json/cluster/resources`)
4. Revisar estado de VMs/CTs (`/api2/json/nodes/{node}/qemu` y `/api2/json/nodes/{node}/lxc`)
5. Alertar por nodos caídos, quorum bajo, recursos críticos
