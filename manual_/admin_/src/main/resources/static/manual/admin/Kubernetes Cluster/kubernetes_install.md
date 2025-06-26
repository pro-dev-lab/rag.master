# Kubernetes 설치

Bastion에서 진행합니다.



### 1. bastion server에 설정해 둔 dns 설정 복사 (컨테이너 올라간 후 마운트한 경로의 hosts.yaml 로 복사)

```
ansible k8s_cluster -i /root/kubespray/inventory/{{cluster.domain}}/hosts.yaml -m copy -a "src=/tmp/resolv.conf.{{cluster.domain}}.io dest=/etc/resolv.conf"  
```



### 2. 설치를 위한 kubespray container 기동

kubespray 를 도커 컨테이너로 올려 사용하면 버전별로 따로 쓸 일이 있을 경우 따로 설치안하고 이미지만 받아서 사용 가능

```
docker pull quay.io/kubespray/kubespray:v2.24.2 

cd ~/kubespray

# $cluster -> 배포대상 cluster명으로치환  (ex: devclu0)

docker run --name kubespray-v2.24.2 -it --mount type=bind,src="$(pwd)"/inventory/$cluster,dst=/inventory \
--mount type=bind,src="${HOME}"/.ssh/id_rsa,dst=/root/.ssh/id_rsa \
quay.io/kubespray/kubespray:v2.24.2  bash
```



3. Kubernetes 설치

컨테이너 쉘 안에서 실행

```
# root@14687be176d1:/# cd kubespray  
# root@14687be176d1:/kubespray# ansible-playbook -i /inventory/hosts.yaml  --private-key /root/.ssh/id_rsa cluster.yml -b
```


4. kubernetes 설치 검증 

4.1 Bastion에서 kubectl 명령어 사용

kubectl 설치

```
# 최신 안정 버전 바이너리 다운로드
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# 실행 파일을 /usr/local/bin 으로 배치(루트 소유, 755 권한)
install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```


4.2 Kubeconfig 복사

4.2.1 .kube 디렉토리 생성

```
# .kube 생성
mkdir -p ~/.kube
```


4.2.2 Kubeconfig 정보 복사 및 수정

```
# Kubeconfig 정보 복사
scp {{master.node.ip}}:/etc/kubernetes/admin.conf /root/.kube/config-{{cluster.domain}}

# Kubeconfig 정보 수정 - 여러 config가 등록되는 경우 context를 구분하기 위함
sed -i -e "s/user: kubernetes-admin/user: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
sed -i -e "s/- name: kubernetes-admin/- name: kubernetes-admin-{{cluster.domain}}/g" /root/.kube/config-{{cluster.domain}}
```
- admin.conf 파일에는 클러스터 CA 인증서·API Server 주소·토큰이 포함돼 있습니다.

- IP 대신 노드의 SSH 별칭(master)을 썼다면 각자 환경에 맞춰 수정하세요.



4.2.3 KUBECONFIG 환경 변수 설정 및 편의 기능 추가

```
# KUBECONFIG 환경 변수 설정 및 편의 기능 추가
vi ~/.bashrc

-----입력 예시-----
alias k=kubectl                           # 짧은 별칭
source <(kubectl completion bash)         # 명령어 자동완성 로드
complete -F __start_kubectl k             # 별칭에도 자동완성 적용
export KUBECONFIG="$HOME/.kube/config-{{cluster.domain}}"   # KUBECONFIG 환경 변수 설정, kubectl이 기본적으로 참조

# .bashrc 변경 사항 적용
source ~/.bashrc
```

- bash 변경 사항 적용

```
# .bashrc 변경 사항 즉시 적용
source ~/.bashrc
```

- user 권한 사용자용 kubeconfig 설정 

```
# user 사용자로 접속
ssh u@{{bastion.ip}}

# kube config 복사
sudo cp /root/.kube/config-{{cluster.domain}} ~/.kube/config-{{cluster.domain}}

# .kube 디렉토리 이동
cd ~/.kube

# config 사용자 및 그룹 변경
sudo chown u:u config-{{cluster.domain}}

# KUBECONFIG 환경 변수 설정 및 편의 기능 추가
vi ~/.bashrc

-----입력 예시-----
alias k=kubectl
source <(kubectl completion bash)
complete -F __start_kubectl k
export KUBECONFIG="$HOME/.kube/config-{{cluster.domain}}"

# .bashrc 변경 사항 적용
source ~/.bashrc
```

- cluster manster 노드에서 u 사용자 config 설정 

```
# user 사용자로 접속
ssh u@{{cluster.master.ip}}

# kube config 복사
sudo cp /etc/kubernetes/admin.conf ~/.kube/config

# .kube 디렉토리 이동
cd ~/.kube

# config 사용자 및 그룹 변경
sudo chown u:u config
```




4.3 Cluster 동작 확인

# node 조회
```
kubectl get no
NAME    STATUS    ROLES         AGE     VERSION
master   Ready    control-plane    7m24s   v1.28.10
worker   Ready    worker          6m55s   v1.28.10

# pod 조회
kubectl get pod -A
NAMESPACE     NAME                                       READY   STATUS    RESTARTS   AGE
kube-system   calico-kube-controllers-5fbd759bf4-dxz2l   1/1     Running   0          6m45s
kube-system   calico-node-llvdh                          1/1     Running   0          6m54s
kube-system   calico-node-zlb8d                          1/1     Running   0          6m54s
kube-system   coredns-5f9fbd49d-54n8c                    1/1     Running   0          6m39s
kube-system   coredns-5f9fbd49d-csfll                    1/1     Running   0          6m36s
kube-system   dns-autoscaler-7df9848888-gsf9z            1/1     Running   0          6m37s
kube-system   kube-apiserver-master                      1/1     Running   1          7m35s
kube-system   kube-controller-manager-master             1/1     Running   2          7m36s
kube-system   kube-proxy-6zx5k                           1/1     Running   0          7m6s
kube-system   kube-proxy-h2jxw                           1/1     Running   0          7m6s
kube-system   kube-scheduler-master                      1/1     Running   1          7m36s
kube-system   nodelocaldns-nqbh7                         1/1     Running   0          6m37s
kube-system   nodelocaldns-v8pt9                         1/1     Running   0          6m37s
```

4.3.1 환경에 맞는 context 로 변경하여 조회

- 현재 context 확인 

```
kubectl config current-context
```

- 등록되어 있는 context 목록 확인 

```
kubectl config get-contexts
```

- 현재 kubectl이 사용할 Kubernetes 클러스터(컨텍스트) 변경 

```
kubectl config use-context {{context.name}}         # ex: kubernetes-admin@devclu0.io
```


---

kubeconfig 의 api server 도메인 및 포트(https://lb.devclu0.io:10443)는 배포된 cluster에서는 정상 동작.

bastion에서 사용시 다음과 같이 변경  → 참고 : [bastion 구성](bastion_config.md)

```
echo "10.120.105.2  lb.devclu0.io" >> /etc/hosts
```

하지만 bastion또는 배포된 cluster에 있지 않은 시스템(로컬)에서 연결시(LB 서버 용도로도 사용하기 위해 dns 구성을 해뒀으므로)  클러스터의 마스터 노드 ip, 6443 포트로 변경해줘야 함.
또한 user 명(kubernetes-admin) 도 다른 클러스터의 user 명과 충돌날 수 있으므로 user 명 및 context 의 user 명도 변경해줘야 함.

