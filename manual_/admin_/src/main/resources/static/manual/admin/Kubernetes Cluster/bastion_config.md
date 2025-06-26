# Bastion 구성

> Bastion  서버란? 
> Bastion은 외부 클러스터에 직접 접근할 수 없게 막고,
> 중간 지점인 Bastion 서버를 통해서만 접근할 수 있는 구조입니다.


## 1. 공통 구성 

### 1.1 OS 보안 설정 해제 : Selinux & Firewalld Disable

모든 노드에서 실행

```
# firewalld 비활성화
systemctl disable firewalld --now

# SELinux 비활성화
sed -i -e s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config
sed -i -e s/SELINUX=permissive/SELINUX=disabled/g /etc/selinux/config

# SELinux 적용
reboot
```


### 1.2 SSH 키 생성 및 배포 : 

Bastion 서버에서 각 노드로 비밀번호 없이 SSH 접할 수 있도록 설정합니다.

```
# SSH 키 생성(최초 1회만 필요)
ssh-keygen
```

출력 예시

```
Generating public/private rsa key pair.
Enter file in which to save the key (/root/.ssh/id_rsa):
Enter passphrase (empty for no passphrase):
Enter same passphrase again:
```

```
# SSH 키를 각 노드로 복사 (예: 192.168.100.101, 102)
ssh-copy-id 192.168.100.101
ssh-copy-id 192.168.100.102
```
> 설명: ssh-copy-id는 공개 키를 대상 서버의 ~/.ssh/authorized_keys에 추가해줍니다.



### 1.3 docker-ce repo 구성 & OS 추가 모듈 패키지 설치

```
# Docker 저장소 구성
echo '
[docker-ce-stable]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/centos/$releasever/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg' > /etc/yum.repos.d/docker-ce.repo
```

```
# 패키지 다운로드 및 설치
mkdir -p /repo && cd /repo
yum update -y 
yum install -y createrepo docker-ce
yum install bind bind-utils haproxy git bash-completion net-tools httpd wget ansible-core skopeo yum-utils chrony
```


### 1.4 DNS 구성 예시 : timegate.io 구성

- 파일  /etc/named.db 용도 : DNS 영역 파일로 쿠버네티스 클러스터에 필요한 도메인 영역을 설정합니다.

```
vi /etc/named.db

----------
zone "timegate.io" IN {
        type master;
        file "timegate.io.zone";
        allow-update { none; };
};

zone "100.168.192.in-addr1.arpa" IN {
        type master;
        file "100.168.192.in-addr.arpa.zone";
        allow-update { none; };
};
```

- 파일 /var/named/timegate.io.zone 용도 : 도메인 이름으로 IP 주소를 찾을 수 있도록 설정합니다.

```
vi /var/named/timegate.io.zone

$TTL 1W
@       IN      SOA     ns1.timegate.io.  root (
                        2019070700      ; serial
                        3H              ; refresh (3 hours)
                        30M             ; retry (30 minutes)
                        2W              ; expiry (2 weeks)
                        1W )            ; minimum (1 week)
        IN      NS      ns1.timegate.io.
        IN      MX 10   smtp.timegate.io.
;
;

ns1     IN      A       192.168.100.100
smtp    IN      A       192.168.100.100
;

; The api identifies the IP of your load balancer.
lb                IN      A       192.168.100.100
bastion           IN      A       192.168.100.100
registry          IN      A       192.168.100.100
api               IN      A       192.168.100.100
;

; The wildcard also identifies the load balancer.
*.apps            IN      A       192.168.100.100
;

; Create entries for the master hosts.
master           IN      A       192.168.100.101
;

; Create entries for the worker hosts.
worker           IN      A       192.168.100.102
;
```

- 파일 /var/named/100.168.192.in-addr.arpa.zone 용도 : IP 주소로 도메인 이름을 찾을 수 있게 설정합니다.

```
vi /var/named/100.168.192.in-addr.arpa.zone

$TTL 1W
@       IN      SOA     ns1.timegate.io.  root (
                        2019070700      ; serial
                        3H              ; refresh (3 hours)
                        30M             ; retry (30 minutes)
                        2W              ; expiry (2 weeks)
                        1W )            ; minimum (1 week)
        IN      NS      ns1.timegate.io.
;

; The syntax is "last octet" and the host must have an FQDN
; with a trailing dot.
20     IN      PTR     bastion.timegate.io.
20     IN      PTR     registry.timegate.io.
20     IN      PTR     api.timegate.io.
;

21     IN      PTR     master.timegate.io.
;

22     IN      PTR     worker.timegate.io.
;
```

- 파일 /etc/named.conf 용도 :  DNS 서비스 전체 설정입니다.

```
vi /etc/named.conf  # 해당 파일 없을 경우엔 생성 (최초 구성시)

options {
        listen-on port 53 { 192.168.100.100; };
        listen-on-v6 port 53 { ::1; };
        directory       "/var/named";
        dump-file       "/var/named/data/cache_dump.db";
        statistics-file "/var/named/data/named_stats.txt";
        memstatistics-file "/var/named/data/named_mem_stats.txt";
        secroots-file   "/var/named/data/named.secroots";
        recursing-file  "/var/named/data/named.recursing";
        allow-query     { 192.168.100.0/24; }; # 이 네트워크에서만 쿼리 허용
        forwarders      { 8.8.8.8; }; # 외부 도메인 조회 시 사용할 DNS 서버
...

include "/etc/named.rfc1912.zones";
include "/etc/named.root.key";
include "/etc/named.db"; # 위에서 생성한 zone 파일 포함
```


- DNS 서비스 활성화 및 시작

```
systemctl enable named --now
```

- Bastion 서버에서 DNS 등록 확인

```
# bastion server ip를 배포될 cluster dns 서버로 등록

# hosts 등록 
echo "10.120.105.2  lb.timegate.io" >> /etc/hosts

# DNS 해석을 위한 resolv.conf 설정
echo "search timegate.io
nameserver 192.168.100.100 " > /tmp/resolv.conf.timegate.io  # tmp 폴더에 만들어두고 클러스터 설치시 복사해서 사용
```

### 추가 예시 : devclu0 DNS 구성 

```
vi /etc/named.db

...
zone "devclu0.io" IN {
        type master;
        file "devclu0.io.zone";
        allow-update { none; };
};
zone "105.120.10.in-addr6.arpa" IN {
        type master;
        file "105.120.10.in-addr5.arpa.zone";
        allow-update { none; };
};
...
```

```
vi /var/named/devclu0.io.zone

TTL 1W
@       IN      SOA     ns1.devclu0.io.  root (
                        2019070700      ; serial
                        3H              ; refresh (3 hours)
                        30M             ; retry (30 minutes)
                        2W              ; expiry (2 weeks)
                        1W )            ; minimum (1 week)
        IN      NS      ns1.devclu0.io.
        IN      MX 10   smtp.devclu0.io.
;
;
ns1     IN      A       10.120.105.2
smtp    IN      A       10.120.105.2
;
; The api identifies the IP of your load balancer.
lb                IN      A       10.120.105.2
bastion           IN      A       10.120.105.2
;registry          IN      A       10.120.105.2
api               IN      A       10.120.105.2
;
; The wildcard also identifies the load balancer.
*.apps            IN      A       10.120.105.2
;
; Create entries for the master hosts.
dev-cluster-m01           IN      A       10.120.105.91
;
; Create entries for the worker hosts.
dev-cluster-w01           IN      A       10.120.105.92
dev-cluster-w02           IN      A       10.120.105.93
dev-cluster-w03           IN      A       10.120.105.94

vi /var/named/105.120.10.in-addr6.arpa.zone

TTL 1W
@       IN      SOA     ns1.cephstorage.io.  root (
                        2019070700      ; serial
                        3H              ; refresh (3 hours)
                        30M             ; retry (30 minutes)
                        2W              ; expiry (2 weeks)
                        1W )            ; minimum (1 week)
        IN      NS      ns1.cephstorage.io.
;
; The syntax is "last octet" and the host must have an FQDN
; with a trailing dot.
20     IN      PTR     dev-cluster-m01.devclu0.io
;20     IN      PTR    registry.userclu2.io.
;
21     IN      PTR     dev-cluster-w01.devclu0.io
22     IN      PTR     dev-cluster-w02.devclu0.io.
23     IN      PTR     dev-cluster-w03.devclu0.io
;
```

```
# bastion server ip를 배포될 cluster dns 서버로 등록
echo "10.120.105.2  lb.devclu0.io" >> /etc/hosts
echo "search devclu0.io
nameserver 10.120.105.2 " > /tmp/resolv.conf.devclu0.io
```

### 1.5 haproxy 구성

master node가 1개일 경우 haproxy구성 필요 없으나, 본 테스트에서는 구성하여 진행

```
vi /etc/haproxy/haproxy.cfg
### 다음 블록 전체 삭제 <Frontend main, backend static, backend app>
### 아래 내용 추가
#---------------------------------------------------------------------
# main frontend which proxys to the backends
#---------------------------------------------------------------------
frontend k8s-api
  bind 0.0.0.0:6443
  mode tcp
  option tcplog
  default_backend k8s-api

#---------------------------------------------------------------------
# static backend for serving up images, stylesheets and such
#---------------------------------------------------------------------
backend k8s-api
  mode tcp
  option tcplog
  option tcp-check
  balance roundrobin

  server master.timegate.io 192.168.100.101:6443 check fall 3 rise 2

#HAProxy 서비스 활성화 시작
systemctl enable haproxy --now
systemctl restart haproxy

#포트 리스닝 확인 
netstat -antp |grep 6443
tcp     0    0 0.0.0.0:6443         0.0.0.0:*           LISTEN      13618/hapro가
```

추가 예시 : devclu0 HAProxy 구성 

```
vi /etc/haproxy/haproxy.cfg
---------------
backend k8s4-api
  mode tcp
  option tcplog
  option tcp-check
  balance roundrobin
  server dev-cluster-m01.devclu0.io 10.120.105.91:6443 check fall 3 rise 2

frontend k8s4-http
  bind *:8100
  mode tcp
  option tcplog
  default_backend k8s4-http

backend k8s4-http
  mode tcp
  balance roundrobin
  server dev-cluster-m01 10.120.105.91:80 check fall 3 rise 2
  server dev-cluster-w01 10.120.105.92:80 check fall 3 rise 2
  server dev-cluster-w02 10.120.105.93:80 check fall 3 rise 2
  server dev-cluster-w03 10.120.105.94:80 check fall 3 rise 2
```