cicd-cluster는 단일 노드를 구성하여 설치한다. → cicd-single-node-cluster


|       cluster-name       | cluster.domain |     node.ip    | cluster.lb.ip | lb.port | 구분 |       설치 방법       |       설치 방법       |
|:------------------------:|:--------------:|:--------------:|:-------------:|:-------:|:----:|:---------------------:|:---------------------:|
| cicd-single-node-cluster | singlecluster  | 10.120.105.229 | 10.120.105.2  | 9443    | 운영 | bastion에서 원격 설치 | bastion에서 원격 설치 |
| dev-cluster-cicd         | dev-cicd       | 10.120.105.240 | 10.120.105.2  | 11443   | 개발 | bastion에서 원격 설치 | bastion에서 원격 설치 |

bastion에서 kubespray를 이용해서 원격 실행 형태로 설치한다.

설치 구성은 다음 문서를 참조 

[bastion 구성](bastion_config.md)  

# Kubespray 구성

## 1. 공통 작업

### 1.1 설치 파일 다운로드 및  inventory 구성

| 변수               | 설정값                          |
|--------------------|---------------------------------|
| {{cluster.domain}} | 상단표의 cluster-domain항목 값  |
| {{cluster.lb.ip}}  | 상단표의 cluster-LB-ip 항목 값  |
| {{host.ip}}        | 상단표의 node-ip 항목 값        |
| {{lb.port}}        | 상단표의 lb-port 항목 값        |

```
# kubespray repo clone
git clone https://github.com/kubernetes-sigs/kubespray.git -b release-2.24 

# inventory 디렉토리 이동
cd /root/kubespray/inventory

# sample 디렉토리 복사
cp -rp sample {{cluster.domain}} 

# {{cluster.domain}} 디렉토리 이동
cd {{cluster.domain}}

# hosts 파일 작성
vi hosts.yaml
```

### 1.2 hosts.yaml 작성 (예시) 

```
all:
  hosts:
    dev-cluster-cicd:
      ansible_host: {{host.ip}} 
      ip: {{host.ip}}
      access_ip: {{host.ip}}
  children:
    kube_control_plane:
      hosts:
        dev-cluster-cicd:
    kube_node:
      hosts:
        dev-cluster-cicd:
    etcd:
      hosts:
        dev-cluster-cicd:
    k8s_cluster:
      children:
        kube_control_plane:
        kube_node:
    calico_rr:
      hosts: {}
  vars:
    override_system_hostname: false
```

### 1.3 variable 수정

- all.yaml

```
vi ~/kubespray/inventory/{{cluster.domain}}/group_vars/all/all.yml
…

## External LB example config
apiserver_loadbalancer_domain_name: "lb.{{cluster.domain}}.io"
loadbalancer_apiserver:
  address: {{cluster.lb.ip}}
  port: {{lb.port}}
loadbalancer_apiserver_port: {{lb.port}}
```

- k8s-cluster.yml 수정

```
vi ~/kubespray/inventory/{{cluster.domain}}/group_vars/k8s_cluster/k8s-cluster.yml

kube_version: v1.28.10   ### 설치할 버전 확인
cluster_name: {{cluster.domain}}.io
kube_proxy_mode: ipvs
kube_proxy_strict_arp: true
container_manager: containerd
# kube_service_subnets 값을 kube_service_addresses로 변경해야 함. kube_service_subnets값이 정의되어 있지 않아 undefined 에러 발생
```

- addons.yml 수정 

```
vi ~/kubespray/inventory/{{cluster.domain}}/group_vars/k8s_cluster/addons.yml

cert_manager_enabled: false #??
metallb_enabled: true
metallb_ip_range:
- "{{node.ip}}-{{node.ip}}"
#metallb_version: v0.13.9
metallb_speaker_enabled: "{{ metallb_enabled }}"
metallb_controller_tolerations:
  - key: "node-role.kubernetes.io/master"
    operator: "Equal"
    value: ""
    effect: "NoSchedule"
  - key: "node-role.kubernetes.io/control-plane"
    operator: "Equal"
    value: ""

# Metrics Server deployment
metrics_server_enabled: true
metrics_server_container_port: 4443
metrics_server_kubelet_insecure_tls: true
metrics_server_metric_resolution: 15s
metrics_server_kubelet_preferred_address_types: "InternalIP,ExternalIP,Hostname"
------------------------------------------
```
 

## 1.3 kubernetes 설치 

### 1.3.1 보안 설정 해제 : Selinux & Firewalld Disable

- dev-cluster-cicd node에서 실행

```
## CICD Server

# OS 보안 설정 해제 : Selinux & Firewalld Disable
systemctl disable firewalld --now
sed -i -e s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config
sed -i -e s/SELINUX=permissive/SELINUX=disabled/g /etc/selinux/config

# conntrack-tools install
yum update
yum install -y conntrack-tools.x86_64
```

- bastion : dns 구성 

```
## Bastion Server

echo "search {{cluster.domain}}.io
nameserver 10.120.105.2 " > /tmp/resolv.conf.dev-cicd.io 
```

- bastion : bastion → dev-cluster-cicd node로 복사 

```
## Bastion Server

ssh-copy-id {{node.ip}}
ansible k8s_cluster -i /root/kubespray/inventory/{{cluster.domain}}/hosts.yaml -m copy -a "src=/tmp/resolv.conf.{{cluster.domain}}.io dest=/etc/resolv.conf"   
```

### 1.3.2 설치를 위한 kubespray container 기동

```
# kubespray image pull
docker pull quay.io/kubespray/kubespray:v2.24.2 

# kubespray 디렉토리 이동
cd ~/kubespray

# kubespray 배포
docker run --name kubespray-v2.24.2 -it \
  --mount type=bind,src="$(pwd)"/inventory/{{cluster.domain}},dst=/inventory \
  --mount type=bind,src="${HOME}"/.ssh/id_rsa,dst=/root/.ssh/id_rsa \
  quay.io/kubespray/kubespray:v2.24.2  bash
```

### 1.3.3 Kubernetes 설치

- kubespray container bash 에서 진행

```
# 모듈명 치환
root@container:/kubespray# sed -i -e "s/nf_conntrack_ipv4/nf_conntrack/g" roles/kubernetes/node/tasks/main.yml

# ansible-playbook 실행
root@container:/kubespray# ansible-playbook -i /inventory/hosts.yaml  --private-key /root/.ssh/id_rsa cluster.yml -b
```


### 1.3.4 node에서 설치 확인


```
kubectl get node
```

>```
>NAME    STATUS   ROLES           AGE   VERSION
>node1   Ready    control-plane   33m   v1.29.5
>```

### 1.3.5 .kube/config 복사 

cluster → bastion으로 .kube/config 복사 

- bastion server

```
# .kube/config 복사
scp root@{{node.ip}}:/etc/kubernetes/admin.conf /root/.kube/config-{{cluster.domain}}
```


- Node 환경에 맞게 구성 요소 치환

  - Master Node가 여러개인 경우 ( Bastion server HAProxy 구성이 되어 있는 경우 )

```
# CICD Cluster 가 DNS 등록되어 있는 경우
sed -i -e "s/user: kubernetes-admin/user: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
sed -i -e "s/name: kubernetes-admin/name: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}

or 

sed -i -e "s/lb.{{cluster.domain}}.io/{{bastion.ip}}/g" /root/.kube/config-{{cluster.domain}}
sed -i -e "s/user: kubernetes-admin/user: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
sed -i -e "s/name: kubernetes-admin/name: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
```

- Master Node가 하나인 경우 ( Bastion server HAProxy 구성이 안되어 있는 경우 ) 

```
sed -i -e "s/lb.{{cluster.domain}}.io:{{lb.port}}/{{node.ip}}:6443/g" /root/.kube/config-{{cluster.domain}}
sed -i -e "s/user: kubernetes-admin/user: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
sed -i -e "s/name: kubernetes-admin/name: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
```


- KUBECONFIG 환경 변수 설정 

```
# KUBECONFIG 에 새로운 경로 추가
vi ~/.bashrc
export KUBECONFIG="기존값:$HOME/.kube/config-{{cluster.domain}}"

# .bashrc 파일 변경 내용 적용
source ~/.bashrc
```
