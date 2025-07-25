# NFS Storage 설치

NFS (Network File System) 스토리지는 **네트워크를 통해 파일 시스템을 공유하는 방식의 스토리지 시스템**입니다.

---

## NFS Server 설치

### 1. NFS Server 구성

1.1 OS 보안 설정 해제 : Selinux & Firewalld Disable

```
systemctl disable firewalld --now
sed -i -e s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config
sed -i -e s/SELINUX=permissive/SELINUX=disabled/g /etc/selinux/config
```

1.2 ``nfs-utils`` 설치

모든 kubernetes node에서 실행

```
yum install -y nfs-utils 
```

1.3 NFS 공유 디렉토리 정보 추가

```
echo '/storage        10.120.105.0/24(rw,no_root_squash)' >>  /etc/exports
```

1.4 디렉토리 생성 및 권한 부여

```
# 디렉토리 생성
mkdir -p /storage

# 디렉토리 권한 부여
chmod -R 777 /storage
```

1.5 NFS 설정 확인 및 반영

```
# 공유 디렉터리 설정을 확인
exportfs -v

# 공유 디렉터리 설정을 갱신
exportfs -ra

# 공유 디렉터리 설정을 확인
exportfs -v
```

1.6 NFS Service 구동

```
systemctl start nfs-server && systemctl enable nfs-server
systemctl start rpcbind && systemctl enable rpcbind
```

또는

```
systemctl status nfs*.service
systemctl restart nfsdcld.service
systemctl restart nfs-mountd.service
systemctl restart nfs-server.service
systemctl restart nfs-idmapd.service
systemctl status nfs*.service
```


### 2. Kubernetes NFS CSI 구성

1. NFS subdir external provisioner 설치

참고자료 : kubernetes-sigs/nfs-subdir-external-provisioner: Dynamic sub-dir volume provisioner on a remote NFS server.

- helm 을 이용한 배포

```
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
    --set nfs.server=x.x.x.x \              # nfs storage node ip
    --set nfs.path=/exported/path           # nfs storage path
    --set storageClass.defaultClass=true
```
_--set storageClass.defaultClass=true : 생략 가능_

- kustomize 이용 → 참고자료 


### 3. PVC 배포 테스트

1. PVC 배포 구성 파일 작성

```
echo 'kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: pvc-test
spec:
  storageClassName: nfs-client
  accessModes:
  - ReadWriteMany
  resources:
   requests:
    storage: 1G' > ./pvc_test.yaml
```

2. PVC 배포 

```
kubectl apply -f ./pvc_test.yaml
```

3. PVC 조회

```
kubectl get pvc -A
```

>```
>NAMESPACE   NAME       STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS    AGE
>default     pvc-test   Bound    pvc-afbbd8a9-bc6d-49ee-8700-4afa33fa657e   1G         RWO            nfs-client      6s
>```
