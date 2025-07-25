# ceph block storage 설치

Ceph Block Storage란?

Ceph Block Storage는 Ceph 클러스터의 RADOS (Reliable Autonomic Distributed Object Store) 위에서 동작하는 블록 저장소입니다.
VM, 컨테이너, 데이터베이스, OpenStack 등에서 디스크처럼 사용할 수 있습니다.

---

## Ceph Node 구성

- cpu : 4core
- memory : 8GB
- Disk : OS 디스크와는 별도록 OSD 용도의 추가 디스크가 필요합니다.
  - 50GB (OS disk)
  - 500GB (OSD disk)

(표1) 시스템 구성

| node-name          | node-type | cluster-name                | node-ip        |
|--------------------|-----------|-----------------------------|----------------|
| ceph-node1         | mon-node  | platform, user1, user2 공용 | 10.120.105.230 |
| ceph-node2         | osd-node1 | platform, user1, user2 공용 | 10.120.105.231 |
| ceph-node3         | osd-node2 | platform, user1, user2 공용 | 10.120.105.232 |
| dev-cluster-ceph01 | mon-node  | dev-cluster-cicd            | 10.120.105.241 |
| dev-cluster-ceph02 | osd-node1 | dev-cluster-cicd            | 10.120.105.242 |
| dev-cluster-ceph03 | osd-node2 | dev-cluster-cicd            | 10.120.105.243 |


## 1. 공통 설정

1.1 OS 보안 설정 해제 : Selinux & Firewalld Disable

모든 노드에 대해서 설정합니다.

```
systemctl disable firewalld --now

sed -i -e s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config
sed -i -e s/SELINUX=permissive/SELINUX=disabled/g /etc/selinux/config
```

1.2 SSH 키 생성 후 모든 노드에 복사

- ssh 키 생성

```
ssh-keygen
```

>```
>Generating public/private rsa key pair.
>Enter file in which to save the key (/root/.ssh/id_rsa):
>Enter passphrase (empty for no passphrase):
>Enter same passphrase again:
>Your identification has been saved in /root/.ssh/id_rsa
>Your public key has been saved in /root/.ssh/id_rsa.pub
>The key fingerprint is:
>SHA256:AyAITvGpYUA/9inxTzwpw8buLdH37A1ceXpoXMKyTeM root@bastion
>The key's randomart image is:
>+---[RSA 3072]----+
>|==o .            |
>|= o...             |
>| + B  .           |
>|. + B o..   . .     |
>| . . X.=S  . B o    |
>|    +.=..o. O B   |
>|     .... o+ E .    |
>|    ...    o+ .    |
>|     ...  .. .       |
>+----[SHA256]-----+
>```