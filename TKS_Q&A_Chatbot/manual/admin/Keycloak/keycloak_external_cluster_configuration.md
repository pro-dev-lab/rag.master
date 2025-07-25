# 외부 kubernetes cluster의 keycloak 접속 설정

> 외부 클러스터에서 키클락에 HTTPS로 통신하기 위한 인증서 설치와 키클락 도메인에 접근하기 위한 DNS, host 설정 방법을 설명합니다.



## 목차

1. [Keycloak HTTPS 통신을 위한 루트 인증서 설치](#1-keycloak-https-통신을-위한-루트-인증서-설치)
2. [외부 클러스터에서 Keycloak 도메인 인식 설정](#2-외부-클러스터에서-keycloak-도메인-인식-설정)
3. [외부 클러스터에서 Keycloak 접근 테스트](#3-외부-클러스터에서-keycloak-접근-테스트)




## 1. Keycloak HTTPS 통신을 위한 루트 인증서 설치

> 멀티 클러스터 환경에서 Keycloak이 설치된 클러스터 외부의 Kubernetes 클러스터가 HTTPS를 통해 Keycloak에 접근할 수 있도록, Keycloak에서 사용하는 루트 인증서(rootca-kc.crt)를 설치하여 TLS 신뢰 체계를 구성합니다.

  1. Linux 운영체제, 파일 기반
    ```bash
    sudo su -
    scp root@{{keycloak이 설치된 마스터노드 IP}}:/etc/kubernetes/pki/rootca-kc.crt /tmp/
    cp -f /tmp/rootca-kc.crt  /etc/pki/ca-trust/source/anchors
    cp -f /tmp/rootca-kc.crt  /etc/kubernetes/ssl/rootca-kc.crt
    update-ca-trust
    ```

    연동할 시스템  linux에서 keycloak이 설치된  userclu1 master에 접속하여 인증서를 가져오고 CA로 설치 

    line 1. 루트 권한으로 전환

    line 2. Keycloak이 설치된 Master 노드에서 인증서 파일(rootca-kc.crt, rootca-kc.key 등)을 로컬 /tmp 디렉터리로 복사

    line 3. 복사한 루트 인증서를 시스템이 신뢰할 CA 디렉터리로 이동
    
    line 4. 복사한 루트 인증서를 kube-apiserver가 접근 가능한 인증서 볼륨의 마운트 디렉터리로 이동 (OIDC 구성 시 필요)

    line 5. 인증서를 시스템 신뢰 저장소에 등록
   



  2. Linux 운영체제, 시크릿 리소스 기반
    ```bash
    sudo su -
    kubectl get secret -n keycloak -o json | jq -r '.items[] | select(.metadata.annotations["cert-manager.io/issuer-kind"] == "Issuer") | .metadata.name'
    kubectl get secret {{keycloak-domain}}-tls -n keycloak -o jsonpath='{.data.ca\.crt}' | base64 -d > rootca-kc.crt 
    cp rootca-kc.crt  /etc/pki/ca-trust/source/anchors
    cp rootca-kc.crt  /etc/kubernetes/ssl/rootca-kc.crt
    update-ca-trust extract
    ```

    연동할 시스템  linux에서 keycloak이 설치된  userclu1 master에 접속하여 인증서를 가져오고 CA로 설치 

    line 1. 루트 권한으로 전환

    line 2. keycloak 네임스페이스의 Secret 목록에서 'cert-manager.io/issuer-kind' 어노테이션이 Issuer인 시크릿을 확인

    line 3. cert-manager로 생성된 keycloak 서버 인증서의 Root CA 시크릿 추출
    
    line 4. 복사한 루트 인증서를 시스템이 신뢰할 CA 디렉터리로 이동

    line 5. 복사한 루트 인증서를 kube-apiserver가 접근 가능한 인증서 볼륨의 마운트 디렉터리로 이동 (OIDC 구성 시 필요)   

    line 6. 인증서를 시스템 신뢰 저장소에 등록




## 2. 외부 클러스터에서 Keycloak 도메인 인식 설정

> 외부 클러스터에서 Keycloak 도메인(keycloak.tg-cloud.co.kr)으로 접근 가능하도록 DNS 또는 hosts 기반 이름 해석 설정을 구성합니다.

  1. NodeLocalDNS ConfigMap 수정 (사용 시)

    ```bash
    kubectl edit cm -n kube-system nodelocaldns
    ```
    
    NodeLocal DNSCache를 사용하는 환경이므로 nodelocaldns 설정 파일을 편집

    ```bash
    tg-cloud.co.kr:53 {
      errors
      cache 30
      log
      debug
      bind 169.254.25.10
      hosts {
        {{Keycloak 서버 또는 Ingress 컨트롤러의 주소}} keycloak.tg-cloud.co.kr
        fallthrough
      }
      forward . {{사내 DNS 서버 주소}}
    }
    ```

    내부 IP를 통해 Keycloak 도메인을 DNS 해석할 수 있도록 설정

    ```bash
    kubectl rollout restart -n kube-system daemonset/nodelocaldns
    ```

    NodeLocalDNS 설정 변경 사항을 반영하기 위해 nodelocaldns daemonset 재시작 




  2. CoreDNS ConfigMap을 수정하여 DNS 질의 및 호스트 매핑 설정 (NodeLocalDNS를 사용하지 않는 환경인 경우)

    ```bash
    kubectl edit cm -n kube-system coredns
    ```

    CoreDNS 설정을 수정하기 위해 ConfigMap을 편집

    ```bash
    tg-cloud.co.kr:53 {
      errors
      cache 30
      log
      debug
      prometheus :9153
      hosts {
        {{Keycloak 서버 또는 Ingress 컨트롤러의 주소}} keycloak.tg-cloud.co.kr
        fallthrough
      }
      forward . {{사내 DNS 서버 주소}}
    }
    ```
  
    keycloak.tg-cloud.co.kr 도메인에 대해 IP를 직접 반환하도록 설정

    ```bash
    kubectl rollout restart -n kube-system deployment/coredns
    ```

    CoreDNS 설정 변경 사항을 반영하기 위해 coredns deployment 재시작




## 3. 외부 클러스터에서 Keycloak 접근 테스트

> 루트 인증서 및 도메인 설정이 올바르게 적용되었는지 확인하기 위해 외부 클러스터에서 Keycloak에 HTTPS로 접근 가능한지 테스트하는 방법을 설명합니다, 

  ```bash
  kubectl run -it --rm -n default curl-test --image=alpine/curl sh
  ```

  테스트용 Pod를 실행 (Pod는 실행 후 종료됨)

  ```bash
  curl -v keycloak.tg-cloud.co.kr
  ```

  Keycloak 도메인으로 접속을 시도하고, IP가 올바르게 해석되며 TLS 통신이 성공하는지 확인

  ```bash
  * Host keycloak.tg-cloud.co.kr:80 was resolved.
  * IPv4: {{Keycloak 서버 또는 Ingress 컨트롤러의 주소}}
  ...
  ```