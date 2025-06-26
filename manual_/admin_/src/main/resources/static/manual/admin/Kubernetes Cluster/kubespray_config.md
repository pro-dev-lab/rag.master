# Kubespray 구성

> kubespray란?
> kubernetes를 쉽게 설치하게 도와주는 자동화 도구로 ansible을 통해 구축하고자  하는 설정 값만 맞게 변경해주어 실행하면 
> kubernetes cluster 구축을 자동으로 해주는 편리한 도구입니다. Github에 오픈소스로서 공개되어있어 누구나 쉽게 구축할 수 있다는 장점이 있습니다.



## 1. 공통 작업 

### 1.1 Kubespray 설치 및 inventory 구성 

** 클러스터명 및 IP 주소는 환경에 맞게 변경 필요 **  
** override_system_hostname : false 설정은 마스터 노드에서 설치시에는 제거해야 함. 베스천에서 설치시에만 필요 **

```
# GitHub에서 Kubespray 다운로드 
git clone https://github.com/kubernetes-sigs/kubespray.git -b release-2.24 
cd /root/kubespray/inventory

# 샘플 인벤토리 복사
cp -rf sample {cluster-name} 
cd {cluster-name}

# hosts.yaml 파일 수정 (ip주소는 환경에 맞게 변경)
vi hosts.yaml

all:
  hosts:
    master:
      ansible_host: 192.168.100.101
      ip: 192.168.100.101
      access_ip: 192.168.100.101
    worker:
      ansible_host: 192.168.100.102
      ip: 192.168.100.102
      access_ip: 192.168.100.102

  children:
    kube_control_plane:       # 마스터 노드 그룹
      hosts:
        master:
    kube_node:                # 쿠버네티스 워커 노드 그룹
      hosts:
        worker:
    etcd:                     # ETCD 클러스터 멤버 ( 단일 마스터인 경우 마스터 노드와 동일 ) 
      hosts:
        master:
    k8s_cluster:              # 전체 쿠버네티스 클러스터를 정의하는 그룹
      children:
        kube_control_plane:
        kube_node:
    calico_rr:                # Calico CNI를 BGP 모드와 함께 사용하는 경우 (선택 사항)
      hosts: {}
  vars:
    override_system_hostname: false   # hosts에서 정의한 node 이름을 override 여부 설정 (선택 사항)
```

파일 설명 : 

hosts.yaml : 클러스터를 구성할 노드들의 역할과 정보를 정의하는 설정 파일입니다.



### all

Ansible의 최상위 그룹입니다. 여기에는 전체 노드에 대한 공통 변수(vars)와 호스트 정보(hosts), 그리고 역할별로 나뉜 하위 그룹(children)이 정의됩니다.

- hosts

```
hosts:
  master:
    ansible_host: 192.168.100.101
    ip: 192.168.100.101
    access_ip: 192.168.100.101
  worker:
    ansible_host: 192.168.100.102
    ip: 192.168.100.102
    access_ip: 192.168.100.102
```

각 노드의 이름(master, worker)과 함꼐, 다음과 같은 필드를 정의합니다.

- ansible_host : Ansible이 해당 호스트에 접속할 때 사용할 IP 주소입니다.

- ip : 내부 통신 또는 노드 식별에 사용되는 기본 IP 주소입니다.

- access_ip : 외부에서 해당 노드에 접근할 때 사용하는 IP 주소입니다. 클러스터 통신용 IP와 분리해서 설정할 수 있습니다.



### children

역할 기반 그룹 정의

```
kube_control_plane:
  hosts:
    master:
kube_node:
  hosts:
    worker:
etcd:
  hosts:
    master:
k8s_cluster:
  children:
    kube_control_plane:
    kube_node:
calico_rr:
  hosts: {}
vars:
  override_system_hostname: false
```

- kube_control_plane

  - kubernetes의 control-plane ( 마스터 ) 역할을 하는 노드입니다.

  - etcd 서버, API 서버, 스케줄러, 컨트롤러 매니저가 설치됩니다.

- kube_node

  - 실제로 Pod를 실행하는 worker 노드들입니다.

  - kubelet, kube-proxy 등이 설치됩니다.

- etcd

  - 분산 key-value 저장소로, kubernetes 상태 정보를 저장하는 핵심 컴포넌트입니다.

  - 단일 마스터 환경에서는 보통 마스터 노드에서 etcd도 함께 싱행합니다.

- k8s_cluster

  - kube_control_plane 과 kube_node 두 그룹을 포함하여 전체 Kubernetes 클러스터를 나타냅니다.

- calico_rr

  - BGP 모드의 Calico 네트워크 플러그인을 사용하는 경우, Route Reflector로 사용할 노드를 정의합니다.

  - Calico 의 고급 설정을 사용하는 경우에만 필요하며, 지금은 비어 있습니다.

- vars

  - 공통 변수 설정

  - override_system_hostname

    - hosts 섹션에서 정의한 노드 이름(master,worker) 을 시스템 호스트 네임으로 덮어쓸지 여부를 설정합니다.

참고:

- master1, worker1 등은 Ansible 인벤토리에서 사용될 논리적인 호스트 이름입니다. 실제 서버의 호스트 이름과 달라도 괜찮습니다.

- Ansible을 실행하는 노드에서 각 클러스터 노드로 비밀번호 없이 SSH 접속 및 sudo 권한 실행이 가능해야 합니다.

- 단일 마스터 구성이므로, 마스터 노드에 장애가 발생하면 클러스터 전체를 사용할 수 없게 됩니다. 프로덕션 환경에서는 고가용성(HA)을 위해 여러 대의 마스터 노드를 구성하는 것이 좋습니다.




### 1.2 변수 파일 수정 

#### * all.yaml

전체 클러스터에 공통적으로 적용되는 전역 설정 파일입니다. 즉, 모든 노드 그룹(kube_control_plane, kube_node, etcd 등)에 공통으로 적용되는 기본값을 정의합니다.

all.yml 파일 수정

```
vi kubespray/inventory/{{cluster.name}}/group_vars/all/all.yml
```

수정 내용 : 

- Kubernetes 클러스터 구성에서 외부 Load Balancer ( External Load Balancer ) 를 사용하는 예시 설정입니다.

```
…

#External LB example config
apiserver_loadbalancer_domain_name: "lb.timegate.io"  # DNS 또는 호스트명
loadbalancer_apiserver:
  address: 192.168.100.100     # Bastion IP
port: 6443                  # port 번호 변경 필요
cluster_name: timegate.io   # 클러스터 이름 마지막 줄에 추가
```


* k8s-cluster.yml 수정

Kubespray를 사용하여 Kubernetes 클러스터를 구성할 때 사용하는 클러스터 전체 설정 파일입니다. 이 파일은 클러스터의 이름, 네트워크 구성, 인증 방식, DNS 설정, 컨테이너 런타임 등 클러스터 설치 시 필요한 핵심 파라미터들을 정의합니다.

k8s-cluster.yml 파일 수정

```
vi /root/kubespray/inventory/{{cluster.name}}/group_vars/k8s_cluster/k8s-cluster.yml
```

수정 내용 :

```
## Change this to use another Kubernetes version, e.g. a current beta release
kube_version: v1.28.10   # 설치할 쿠버네티스 버전 지정
…
# DNS configuration.
# Kubernetes cluster name, also will be used as DNS domain
# cluster_name: cluster.local
cluster_name: timegate.io  # 클러스터 이름 마지막 줄에 추가
```