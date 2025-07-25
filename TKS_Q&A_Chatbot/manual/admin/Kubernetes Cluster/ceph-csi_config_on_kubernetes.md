# ceph-csi 구성 on kubernetes

ceph-csi 란 Ceph(분산 스토리지 시스템)을 Kubernetes 클러스터에서 사용할 수 있도록 해주는 CSI(Container Storage Interface) 드라이버입니다.

---

## 1. ceph-csi 구성 on kubernetes

bastion server에서 각 kubernetes cluster에 ceph-csi driver를 설치한다.

### 1.1 설치 파일 다운로드 및 values.yaml 작성

mon-node의 ID, Key 변수 값 확인

1.1.1 Ceph 클러스터 status 조회

```
ceph -s
```

>```
>cluster:
>    id:     {{cluster.id}}
>    health: HEALTH_OK
>```

1.1.2 Ceph 클러스터에 존재하는 모든 RADOS Pool 목록 조회

```
ceph osd lspools
```

>```
>1 .mgr
>2 cephfs.{{fs.name}}.meta
>3 cephfs.{{fs.name}}.data
>```

1.1.3 Ceph 클러스터에 등록된 모든 인증 키 목록 조회

```
ceph auth list
```

>```
>client.admin
>        key: {{adminKey}}
>        caps: [mds] allow *
>        caps: [mgr] allow *
>        caps: [mon] allow *
>        caps: [osd] allow *
>```

1.1.4 Values 파일 작성 

**k8s bastion 에서 실행**

```
# _w 디렉토리 생성 및 이동
mkdir ~/_w && cd ~/_w

# ceph-csi 레포 복사
git clone https://github.com/ceph/ceph-csi.git  --branch release-v3.11

# ceph-csi 디렉토리 이동
cd ./ceph-csi/

# values 파일 백업
cp -f ./charts/ceph-csi-cephfs/values.yaml ./charts/ceph-csi-cephfs/values.yaml.bak
```

- node 환경에 맞게 values.yaml 파일 수정

```
vi ./charts/ceph-csi-cephfs/values.yaml
```

- 수정 예시

```
# 위에서 확인한 Ceph 클러스터 ID, Key 값으로 수정
...
csiConfig:
clusterID: "{{cluster.id}}"
"{{mon-node.node-ip}}:6789"
...
storageClass:
  create: true
  name: csi-cephfs-sc
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
  clusterID: "{{cluster.id}}"
  fsName: myfs
  pool: cephfs.myfs.data

...
secret:
  create: true
  name: csi-cephfs-secret
  annotations: {}
  adminID: admin
  adminKey: {{adminKey}}
```

- offline 설치시 추가 작업

```
### mon node에서 "ceph auth list" 명령어로 ID/Key 값 확인 가능
# 본 테스트에서 k8s node는 폐쇄망으로 구성되어 있어 image는 local repository로 pull 한다.

# CSI 구성 요소들이 기본적으로 외부 퍼블릭 레지스트리에서 이미지를 가져오게 되어있다.
cat values.yaml | grep "repository"  ## AS-IS

-----출력 예시-----
      repository: registry.k8s.io/sig-storage/csi-node-driver-registrar
      repository: http://quay.io/cephcsi/cephcsi 
      repository: registry.k8s.io/sig-storage/csi-provisioner
      repository: registry.k8s.io/sig-storage/csi-resizer
      repository: registry.k8s.io/sig-storage/csi-snapshotter

# 내부 프라이빗 레지스트리 경로로 변경 `registry.timegate.io:8000/kubespray/...` 형식
cat values.yaml | grep "repository"  # TO-BE

-----출력 예시-----
      repository: registry.timegate.io:8000/kubespray/csi-node-driver-registrar
      repository: registry.timegate.io:8000/kubespray/cephcsi
      repository: registry.timegate.io:8000/kubespray/csi-provisioner
      repository: registry.timegate.io:8000/kubespray/csi-resizer
      repository: registry.timegate.io:8000/kubespray/csi-snapshotter

# skopeop 명령어로 이미지를 미리 복사
skopeo copy docker://registry.k8s.io/sig-storage/csi-node-driver-registrar:v2.10.1 docker://registry.timegate.io:8000/kubespray/csi-node-driver-registrar:v2.10.1
skopeo copy docker://quay.io/cephcsi/cephcsi:v3.11-canary docker://registry.timegate.io:8000/kubespray/cephcsi:v3.11-canary
skopeo copy docker://registry.k8s.io/sig-storage/csi-provisioner:v4.0.1 docker://registry.timegate.io:8000/kubespray/csi-provisioner:v4.0.1
skopeo copy docker://registry.k8s.io/sig-storage/csi-resizer:v1.10.1 docker://registry.timegate.io:8000/kubespray/csi-resizer:v1.10.1
skopeo copy docker://registry.k8s.io/sig-storage/csi-snapshotter:v7.0.2 docker://registry.timegate.io:8000/kubespray/csi-snapshotter:v7.0.2
```

---

### 1.2 Ceph-CSI 배포

1.2.1 ceph 네임스페이스 생성

```
kubectl create ns ceph
```

1.2.2 ceph-csi-cephfs 드라이버 배포

```
helm install -n ceph ceph-csi-cephfs ./charts/ceph-csi-cephfs/
```

1.2.3 ceph 네임스페이스 Pod 목록 조회

```
kubectl get pod -n ceph
```

>```
>NAME                                       READY  STATUS    RESTARTS   AGE
>ceph-csi-cephfs-nodeplugin-zw6k7               3/3     Running    0      2m32s
>ceph-csi-cephfs-provisioner-5b9cdb4984-57ljn   5/5     Running     0         12s
>```

1.2.4 StorageClass 목록 조회

```
kubectl get sc
```

>```
>NAME : csi-cephfs-sc(default)
>PROVISIONER : cephfs.csi.ceph.com
>RECLAIMPOLICY : Delete
>VOLUMEBINDINGMODE : Immediate
>ALLOWVOLUMEEXPANSION : true
>AGE : 72m
>```

---

### 1.3 PV Bound 검증

1.3.1 테스트용 pvc 생성 ``test-pvc.yaml`` 파일 작성

```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: csi-cephfs-sc
```

1.3.2 ``test-pvc.yaml`` 사용하여 ceph 네임스페이스에 pvc 생성

```
kubectl create -f test-pvc.yaml -n ceph
```

1.3.3 ceph 네임스페이스 PVC 목록 조회

```
kubectl get pvc -n ceph
```

>```
>NAME : test-pvc
>STATUS : Bound
>VOLUME : pvc-3dce2e69-4bc7-4228-9722-2b249d139358
>CAPACITY : 5Gi
>ACCESS MODES : RWO
>STORAGECLASS : csi-cephfs-sc
>AGE : 66s
>```

1.3.4 테스트용 pod 생성 ``test-pod.yaml`` 파일 작성

```
apiVersion: v1
kind: Pod
metadata:
  name: csi-cephfs-demo-pod
spec:
  containers:
    - name: web-server
      image: registry.timegate.io:8000/kubespray/nginx:latest
      volumeMounts:
        - name: mypvc
          mountPath: /var/lib/www
  volumes:
    - name: mypvc
      persistentVolumeClaim:
        claimName: test-pvc
        readOnly: false
```

1.3.5 ``test-pod.yaml`` 을 사용하여 ceph 네임스페이스에 pod 생성

```
kubectl create -f test-pod.yaml -n ceph
```

1.3.6 Pod 내부의 파일시스템이 CephFS를 통해 마운트되었는지 확인

```
kubectl exec -it csi-cephfs-demo-pod -n ceph -- df -h |grep 6789
```

>```
>192.168.100.117:6789:/volumes/csi/csi-vol-93859195-1299-49a9-8578-0fabb2120a9a/60a3c32d-f27b-4d5f-8d1d-ff431b646cc1  5.0G     0  5.0G   0% /var/lib/www
>```