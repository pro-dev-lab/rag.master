# Keycloak 설치 - Self-Sigend CA 기반

> CentOS 기반 CICD 마스터 노드에 ArgoCD v2.9.3을 설치하고, 폐쇄망 환경에 맞춰 Harbor 레지스트리 이미지를 사용하는 방법과 Kubernetes 연동 및 CLI 사용법을 설명합니다.



## 목차

1. [Master Node에 쉘 접속 및 환경변수 설정](#1-master-node에-쉘-접속-및-환경변수-설정)  
2. [자체 서명 인증서 생성](#2-자체-서명-인증서-생성)  
3. [Self-Signed CA 기반 keycloak TLS 구성](#3-self-signed-ca-기반-keycloak-tls-구성)  
4. [Keycloak Helm Chart 다운로드, Values-override 생성 및 Values 수정](#4-keycloak-helm-chart-다운로드-values-override-생성-및-values-수정)  
5. [NFS Storage 설치 (미설치의 경우)](#5-nfs-storage-설치-미설치의-경우)  
6. [Keycloak 배포](#6-keycloak-배포)  
7. [Keycloak Domain 접근을 위한 네임 리졸루션 설정](#7-keycloak-domain-접근을-위한-네임-리졸루션-설정)  
8. [Keycloak Domain 접속 정보](#8-keycloak-domain-접속-정보)  
9. [Keycloak 관리자 계정 ID, Password 변경](#9-keycloak-관리자-계정-id-password-변경)  
10. [Keycloak 삭제](#10-keycloak-삭제)




## 1. Master Node에 쉘 접속 및 환경변수 설정

> keycloak이 설치될 클러스터의 마스터 노드에 접속하고 설치 및 구성에 필요한 환경변수를 설정합니다.

1. keycloak이 설치될 클러스터의 마스터 노드의 내부 IP 주소로 ssh 접속

  ```bash
  ssh u@<master node InternalIP>
  ```




2. 루트 사용자로 전환

  ```bash
  su -
  ```




3. UID가 1000인 사용자의 홈 디렉터리를 HOMEU 변수에 저장

  ```bash
  export HOMEU=$(cat /etc/passwd | grep 1000 | awk '{ split($1,a, ":"); print a[6] }')
  ```




4. 인증서 생성 시 사용할 암호를 환경 변수로 설정

  ```bash
  export PASSPHRASE="Sowoghk12!"
  ``




5. 인증서 저장 경로 및 관련 변수 설정 후 디렉터리 생성

  ```bash
  CERTS_DIR="/etc/kubernetes/pki"
  cert_domain="keycloak.tg-cloud.co.kr"
  kc_cert_prefix="tls-kc"
  kc_rootca_prefix="rootca-kc"
  oidc_prefix="dev.oidc"
  mkdir -p $CERTS_DIR
  ``




## 2. 자체 서명 인증서 생성

> Keycloak Server, keycloak client 및 Ingress에 사용할 자체 서명 인증서를 생성하여 인증서 체계를 구축합니다.

1. OpenSSL 기반 자체 서명 인증서 생성

  ```bash
  mkdir -p keycloak && cd keycloak
  ```

  keycloak 디렉토리 생성 및 이동

  ```bash
  openssl genrsa -aes256 -out $CERTS_DIR/$kc_rootca_prefix.key -passout env:PASSPHRASE 2048 
  ```

  패스프레이즈로 보호되는 Root CA 개인키 생성

  ```bash
  openssl req -x509 -new -nodes -key $CERTS_DIR/$kc_rootca_prefix.key -sha256 -days 1024 -out $CERTS_DIR/$kc_rootca_prefix.crt -subj "/C=KR/ST=st/L=loc/O=org/OU=org/CN=$cert_domain" -passin env:PASSPHRASE
  ```

  위에서 생성한 키로 Root CA 인증서 생성

  ```bash
  openssl genrsa -out  $CERTS_DIR/$kc_cert_prefix.key 2048
  ```

  Keycloak 서버용 개인키 생성

  ```bash
  chmod 644 $CERTS_DIR/$kc_cert_prefix.key
  ```

  생성된 키의 권한 설정

  ```bash
  openssl req -new -key  $CERTS_DIR/$kc_cert_prefix.key -out  $CERTS_DIR/$cert_domain.csr -subj "/C=KR/ST=st/L=loc/O=org/OU=org/CN=$cert_domain"
  ```

  서버 인증서 서명 요청(CSR) 생성

  ```bash
  openssl x509 -req -extfile <(printf "subjectAltName=DNS:$cert_domain") -in $CERTS_DIR/$cert_domain.csr -CA $CERTS_DIR/$kc_rootca_prefix.crt -CAkey $CERTS_DIR/$kc_rootca_prefix.key -CAcreateserial -out $CERTS_DIR/$kc_cert_prefix.crt -days 500 -sha256 -passin env:PASSPHRASE
  ```

  Root CA로 Keycloak 서버 인증서를 서명

  ```bash
  openssl x509 -inform PEM -in $CERTS_DIR/$kc_cert_prefix.crt -text
  ```

  생성된 인증서 내용을 확인

  ```bash
  openssl genrsa -out "$CERTS_DIR/$oidc_prefix.client.key" 2048 && \
  openssl req -new -sha256 -key "$CERTS_DIR/$oidc_prefix.client.key" -out "$CERTS_DIR/$oidc_prefix.client.req" -subj "/CN=oidc" && \
  openssl x509 -req -sha256 -in "$CERTS_DIR/$oidc_prefix.client.req" -CA "$CERTS_DIR/$kc_rootca_prefix.crt" -CAkey "$CERTS_DIR/$kc_rootca_prefix.key" -extensions client -days 365 -outform PEM -out "$CERTS_DIR/$oidc_prefix.client.cer" -passin env:PASSPHRASE
  ```

  OIDC용 클라이언트 인증서 생성

  ```bash
  kubectl create ns keycloak
  ```

  keycloak namespace 생성
  
  ```bash
  kubectl create secret generic x509-secret -n keycloak  --from-file=ca.crt=$CERTS_DIR/$kc_rootca_prefix.crt --from-file=tls.crt=$CERTS_DIR/$kc_cert_prefix.crt --from-file=tls.key=$CERTS_DIR/$kc_cert_prefix.key
  kubectl create secret generic $cert_domain-tls -n keycloak  --from-file=ca.crt=$CERTS_DIR/$kc_rootca_prefix.crt --from-file=tls.crt=$CERTS_DIR/$kc_cert_prefix.crt --from-file=tls.key=$CERTS_DIR/$kc_cert_prefix.key
  ```

  keycloak server 인증서를 keycloak namespace에 secret 리소스로 저장

 


2. CertManager 기반 자체 서명 인증서 생성

  ```bash
  ssh u@{{keycloak이 설치될 마스터노드 IP}}
  su -
  ```

  마스터 노드 접속 및 루트 사용자로 전환

  ```bash
  mkdir -p ~/keycloak && cd ~/keycloak
  ```

  keycloak 디렉토리 생성 및 이동

  ```bash
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  ```

  Helm 설치 (설치되어 있지 않은 경우)
 
  ```bash
  # CertManager Helm 차트 리포지토리 추가
  helm repo add jetstack https://charts.jetstack.io
  # Helm 차트 업데이트
  helm repo update
  # cert-manager의 CRDs는 Helm chart에 포함되어 있지 않기 때문에, 별도로 설치
  kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.8.0/cert-manager.crds.yaml
  # CertManager 배포
  helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --version v1.8.0
  ```

  CertManager 설치가 완료되면 cert-manager 네임스페이스에 관련 리소스가 배포됨

  ```bash
  kubectl create ns keycloak
  ```

  keycloak namespace 생성

  ```bash
  cat <<EOF > ~/keycloak/issuer.yaml
  ---
  apiVersion: cert-manager.io/v1
  kind: Issuer
  metadata:
    name: root-ca-issuer
    namespace: keycloak            
  spec:
    selfSigned: {}
  EOF
  ```

  Root CA 인증서를 생성하고 이를 CertManager로 관리하기위해 Issuer 리소스를 정의, Issuer 리소스는 인증서를 발급할 인증기관(CA)을 정의하는 것이며 CertManager에서 self-signed Issuer를 사용하여 Root CA 인증서를 생성

  ```bash
  kubectl apply -f issuer.yaml
  ```

  위의 YAML 파일을 사용해 Issuer를 생성

  ```bash
  cat <<EOF > ~/keycloak/keycloak-server-cert.yaml
  apiVersion: cert-manager.io/v1
  kind: Certificate
  metadata:
    name: keycloak-server-cert
    namespace: keycloak
  spec:
    secretName: keycloak.tg-cloud.co.kr-tls
    issuerRef:
      name: root-ca-issuer
      kind: Issuer
    commonName: "keycloak.tg-cloud.co.kr"
    dnsNames:
      - "keycloak.tg-cloud.co.kr"
    duration: 8760h # 1년
    renewBefore: 360h # 만료 15일 전에 갱신
  EOF
  ```

  Keycloak 서버 인증서를 발급하기 위해 Keycloak 서버의 도메인에 대한 인증서를 자동으로 발급하도록 Certificate 리소스를 정의

  ```bash
  kubectl apply -f keycloak-server-cert.yaml
  ```

  keycloak-server-cert.yaml 파일을 사용하여 Keycloak 서버용 인증서를 배포

  ```bash
  cat <<EOF > ~/keycloak/keycloak-oidc-client-cert.yaml
  apiVersion: cert-manager.io/v1
  kind: Certificate
  metadata:
    name: keycloak-oidc-client-cert
    namespace: keycloak            # cert-manager -> keycloak 으로 변경
  spec:
    secretName: keycloak-oidc-client-tls
    issuerRef:
      name: root-ca-issuer
      kind: Issuer
    commonName: "keycloak.tg-cloud.co.kr"
    dnsNames:
      - "keycloak.tg-cloud.co.kr"
    duration: 8760h # 1년
    renewBefore: 360h # 만료 15일 전에 갱신
  EOF
  ```

  OIDC 연동을 위한 Keycloak Client 인증서는 아래와 같이 정의하여 자동으로 발급, 이 인증서는 Keycloak과 OIDC 연동을 위한 클라이언트 인증서로 사용 됨

  ```bash
  kubectl apply -f keycloak-oidc-client-cert.yaml
  ```

  keycloak-oidc-client-cert.yaml 파일을 사용하여 OIDC 클라이언트 인증서를 배포

  인증서 자동 갱신 설정: CertManager는 생성된 인증서에 대해 자동으로 갱신을 수행합니다. 인증서의 duration 및 renewBefore 필드를 설정하여 만료 15일 전에 자동으로 갱신하도록 구성할 수 있습니다. CertManager는 Kubernetes 내에서 인증서를 관리하고, 갱신된 인증서는 자동으로 Keycloak과 Ingress에 배포됩니다.




## 3. Self-Sigend CA 기반 keycloak TLS 구성

> Keycloak의 TLS 통신을 위해 자체 서명한 Root CA를 기반으로 Ingress, Keycloak Server 및 Keycloak Client에 TLS 인증 구성을 설정하는 절차를 설명합니다.

  주요 작업:
  - ingress (nginx) TLS 구성
  - keycloak server HTTPS 구성
  - keycloak client용 Truststore 구성

  3.1. ingress (nginx) TLS 구성 방법: 
    - Ingress에서 TLS를 설정하기 위해 자체 서명한 인증서를 사용한 secret(keycloak/keycloak.tg-cloud.co.kr-tls)을 생성하여 Helm chart에 설정
    - 5번 value 생성 단계에서 values-override.yaml 파일에 해당 내용 구성

  3.2. keycloak server HTTPS 구성 방법:
    - Keycloak 서버 자체의 HTTPS 설정을 위해 인증서(cert), 개인키(key), 그리고 Root CA를 포함한 secret(x509-secret)을 생성하여 /etc/x509/https에 mount
    - Java 기반의 Keycloak 서버가 HTTPS를 통해 통신할 수 있도록 구성
    - 5번 value 생성 단계에서 values-override.yaml 파일에 해당 내용 구성

  3.3. keycloak client용 Truststore 구성 방법:
    - Keycloak 서버에서 OIDC 클라이언트의 인증서 유효성을 검증하기 위해 자체 서명한 Root CA로 생성된 클라이언트 인증서를 신뢰할 수 있도록 Java truststore를 생성하고 secret(keycloak-truststore)으로 등록
    - Helm chart의 tls.truststore 관련 설정을 통해 Keycloak 내부에서 이 truststore를 참조하도록 구성

    ```bash
    ssh u@{{keycloak이 설치될 마스터노드 IP}}
    su -
    ```

    키클락이 설치된 클러스터의 마스터노드에 ssh 접속하여 root 계정으로 이동

    ```bash
    usermod -aG wheel u
    logout
    exit
    ```

    u 계정에 sudo 권한 부여 후 사용자 계정으로 이동, 사용자 계정 로그아웃

    ```bash
    ssh u@{{keycloak이 설치될 마스터노드 IP}}
    groups
    # 결과에 wheel 포함돼야 함
    sudo whoami
    # → root 나오면 성공
    ```

    사용자 계정으로 재접속 후 위 명령어로 u 계정에 sudo 권한이 부여되었는 지 확인

    ```bash
    su - $(id -un 1000)
    sudo dnf update -y
    sudo dnf install -y java-21-openjdk-devel
    echo "JAVA_HOME=/usr/lib/jvm/java-21-openjdk" | sudo tee -a /etc/environment
    sudo cat /etc/environment
    source /etc/environment
    ```

    일반 사용자로 전환 후 Java 설치 및 환경변수 등록

    ```bash
    cat /etc/pki/ca-trust/extracted/java/cacerts
    ```

    truststore 파일에 내용이 있는지 확인

    ```bash
    # 환경변수 등록
    CERTS_DIR="/etc/kubernetes/pki"
    PASSPHRASE="Sowoghk12!"
    cert_domain="keycloak.tg-cloud.co.kr" #"keycloak.tg-cloud.co.kr"
    kc_rootca_prefix="rootca-kc"        #"rootca-kc"
    kc_cert_prefix="tls-kc"             #"tls-kc"
    trust_store_ca="kc-ca-cert"         #"kc-ca-cert"

    # 사용자의 홈 디렉토리 아래 .keystore 디렉토리를 생성하고, 그곳으로 이동
    mkdir -p ~/.keystore && cd ~/.keystore/ 

    3.3.1 PEM 방식으로 client용 Truststore 구성
    > OpenSSL 기반으로 자체 서명 인증서를 생성한 경우 PEM 방식으로 구성

      # 자체 서명된 Root CA 인증서를 Java Keystore (JKS) 형식으로 저장
      keytool -importcert -alias kc-ca-cert -file $CERTS_DIR/$kc_rootca_prefix.crt -keystore ~/.keystore/$kc_cert_prefix.cert.jks
      Enter keystore password: Sowoghk12! 
      Re-enter new password: Sowoghk12! 
      Trust this certificate? [no]: yes

      # Keycloak 서버용 서버 인증서와 개인키를 하나의 PKCS#12 형식 파일 (.p12)로 묶음
      openssl pkcs12 -export -in $CERTS_DIR/$kc_cert_prefix.crt -inkey $CERTS_DIR/$kc_cert_prefix.key -out ~/.keystore/$kc_cert_prefix.cert.p12
      Enter Export Password: Sowoghk12! 
      Verifying - Enter Export Password: Sowoghk12! 

      # 방금 만든 PKCS#12 파일 내용(인증서, 키 등)을 자세히 확인하는 명령어
      keytool -list -v -storetype pkcs12 -keystore ~/.keystore/$kc_cert_prefix.cert.p12

      # .p12 파일을 Java Keystore(JKS) 형식으로 변환하여 인증서와 개인키를 포함한 jks 파일을 생성
      keytool -importkeystore -deststorepass $PASSPHRASE -destkeypass $PASSPHRASE -destkeystore ~/.keystore/$kc_cert_prefix.cert.jks -srckeystore ~/.keystore/$kc_cert_prefix.cert.p12 -srcstoretype PKCS12 -alias 1

      # 위에서 만든 .jks를 다시 PKCS#12 포맷으로 변환
      # Keycloak 설정에서는 .jks 또는 .p12 포맷 모두 사용 가능하므로 환경에 따라 재가공하는 작업
      # 이름은 keystore.jks로 명명하여 Keycloak Helm chart에서 참조 가능하게 함
      keytool -importkeystore -srckeystore ~/.keystore/$kc_cert_prefix.cert.jks -destkeystore ~/.keystore/$kc_cert_prefix.keystore.jks -deststoretype pkcs12
      대상 키 저장소 비밀번호 입력: Sowoghk12! 
      새 비밀번호 다시 입력: Sowoghk12!
      소스 키 저장소 비밀번호 입력: Sowoghk12!
      ```

      Root CA를 truststore에 등록, 서버 인증서를 keystore로 변환

      ```bash
      # root 권한으로 로그인하여 명령들을 root 사용자로 실행
      su -

      # UID가 1000인 사용자(첫 번째 일반 사용자 계정)의 홈 디렉토리를 추출하여 HOMEU 환경변수에 저장
      export HOMEU=$(cat /etc/passwd | grep 1000 | awk '{ split($1,a, ":"); print a[6] }')
      echo $HOMEU

      # root계정에서 keystore, secret을 생성할 때 사용할 환경변수를 설정
      kc_cert_prefix="tls-kc"             #"tls-kc"
      kc_rootca_prefix="rootca-kc"        #"rootca-kc"\
      CERTS_DIR="/etc/kubernetes/pki"
      cd $HOMEU/.keystore

      # 위에서 생성한 .jks 파일들을 Kubernetes Secret으로 생성
      # 이 secret은 Helm chart 또는 Keycloak Pod에 mount되어 서버 인증서(TLS) 및 클라이언트 인증서 검증(Truststore) 등에 사용
      kubectl create secret generic keycloak-truststore --from-file=$HOMEU/.keystore/$kc_cert_prefix.cert.jks --from-file=$HOMEU/.keystore/$kc_cert_prefix.keystore.jks -n keycloak
      ```

      Truststore를 Kubernetes secret으로 저장

      ```bash
      cp -f $CERTS_DIR/$kc_rootca_prefix.crt /etc/pki/ca-trust/source/anchors/
      update-ca-trust extract
      ```

      시스템 truststore에 Root CA 추가

    3.3.2 JKS 방식으로 client용 Truststore 구성
    > CertManager 기반으로 자체 서명 인증서를 생성한 경우 JKS 방식으로 구성
      CertManger 기반으로 자체 서명 인증서를 생성한 경우, client용 Truststore 구성

      ```bash
      kubectl get secret keycloak.tg-cloud.co.kr-tls -n keycloak -o jsonpath='{.data.tls\.crt}' | base64 -d > ~/.keystore/tls-kcdev.crt
      kubectl get secret keycloak.tg-cloud.co.kr-tls -n keycloak -o jsonpath='{.data.tls\.key}' | base64 -d > ~/.keystore/tls-kcdev.key
      kubectl get secret keycloak.tg-cloud.co.kr-tls -n keycloak -o jsonpath='{.data.ca\.crt}' | base64 -d > ~/.keystore/rootca-kcdev.crt
      ```
      Secret에서 Keycloak 서버 인증서 및 키 추출
      ⚠️ ca.crt가 없는 경우: ClusterIssuer가 ca.crt를 제공하지 않는 self-signed 방식이므로 Root CA 생성이 필요하거나, 자체 CA Issuer를 사용해야 함.


      ```bash
      keytool -importcert \
        -alias kc-ca-cert \
        -file ~/.keystore/rootca-kcdev.crt \
        -keystore ~/.keystore/keycloak.truststore.jks
      # 입력값:
      # Enter keystore password: Sowoghk12!
      # Re-enter new password: Sowoghk12!
      # Trust this certificate? [no]: yes
      ```
      Root CA 인증서를 Java Truststore(JKS)로 등록


      ```bash
      # .p12 파일 생성: Keycloak 서버용 인증서 + 개인키를 PKCS#12(.p12) 파일로 묶음
      openssl pkcs12 -export \
        -in ~/.keystore/tls-kcdev.crt \
        -inkey ~/.keystore/tls-kcdev.key \
        -out ~/.keystore/keycloak.keystore.p12 \
        -name keycloak \
        -passout pass:Sowoghk12!
      # .p12 → JKS 변환
      keytool -importkeystore \
        -deststorepass Sowoghk12! \
        -destkeypass Sowoghk12! \
        -destkeystore ~/.keystore/keycloak.keystore.jks \
        -srckeystore ~/.keystore/keycloak.keystore.p12 \
        -srcstoretype PKCS12 \
        -srcstorepass Sowoghk12! \
        -alias keycloak \
        -noprompt
      ```
      Keycloak 서버용 인증서 + 키를 PKCS#12(.p12)로 변환 후 JKS로 변환


      ```bash
      kubectl create secret generic keycloak-truststore \
        --from-file=keycloak.truststore.jks=/root/.keystore/keycloak.truststore.jks \
        --from-file=keycloak.keystore.jks=/root/.keystore/keycloak.keystore.jks \
        -n keycloak
      ```
      Kubernetes Secret으로 truststore 및 keystore 저장


      ```bash
      cp -f ~/.keystore/rootca-kcdev.crt /etc/pki/ca-trust/source/anchors/
      update-ca-trust extract
      ```
      시스템 truststore에 Root CA 추가




## 4. Keycloak Helm Chart 다운로드, Values-override 생성 및 Values 수정

> Helm Chart를 내려받고 Keycloak이 자체 서명된 TLS 인증서를 인식하고 HTTPS로 통신하도록 Helm 설치값을 구성합니다.

1. Helm 설치 (설치되어 있지 않은 경우)
  ```bash
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  ```




2. Keycloak을 배포하는 Helm Chart 준비
  ```bash
  su -
  export HOMEU=$(cat /etc/passwd | grep 1000 | awk '{ split($1,a, ":"); print a[6] }')
  mkdir -p $HOMEU/_w
  #keycloak version: 25.0.2
  helm pull oci://registry-1.docker.io/bitnamicharts/keycloak --version 22.1.1 -d $HOMEU/_w
  mkdir $HOMEU/_w/chart-keycloak
  tar xzvf $HOMEU/_w/keycloak-22.1.1.tgz  -C $HOMEU/_w/chart-keycloak --strip-components 1
  ```

  root 계정으로 이동하여 Helm Chart를 ~/_w/chart-keycloak 경로에 내려받고 압축 해제




3. Helm Chart values.yaml 수정
  ```bash
  sed -i -e 's/defaultStorageClass: ""/defaultStorageClass: "nfs-client"/g' $HOMEU/_w/chart-keycloak/charts/postgresql/values.yaml
  sed -i -e 's/storageClass: ""/storageClass: "nfs-client"/g' $HOMEU/_w/chart-keycloak/charts/postgresql/values.yaml
  sed -i -e 's/docker.io/{{harbor 레지스트리 주소}}\/docker/g' $HOMEU/_w/chart-keycloak/charts/postgresql/Chart.yaml
  ```

  PostgreSQL의 storage class, image 경로를 설정하기 위해 Helm Chart Values 수정

  ```bash
  ### (PEM 기반인 경우만 실행)
  sed -i -e "s/\/opt\/bitnami\/keycloak\/certs\/tls/\/etc\/x509\/https\/tls/g" $HOMEU/_w/chart-keycloak/templates/configmap-env-vars.yaml
  ```
  configmap-env-vars.yaml 템플릿의 인증서 경로 수정 (PEM 기반인 경우만 실행)
  certManager를 통해 인증서를 생성한 경우(JKS 방식) keystore/truststore는 /opt/bitnami/keycloak/certs에 마운트되어야 하므로 추후 다른 설정이 필요합니다.


4. Helm Chart values-override.yaml 생성 및 수정
  ```bash
  ssh u@<<keycloak을 설치할 클러스터의 마스터노드 IP 주소>>
  su -
  export HOMEU=$(cat /etc/passwd | grep 1000 | awk '{ split($1,a, ":"); print a[6] }')
  cd $HOMEU/_w
  export cert_domain=keycloak.tg-cloud.co.kr
  vi $HOMEU/_w/chart-keycloak/values-override.yaml
  ```
  마스터 노드의 root 계정에서 values-override.yaml 파일 생성

  4.1. PEM 방식 values-override.yaml
  > OpenSSL로 pem 형식의 인증서를 생성한 경우 PEM 방식으로 인증서 구성
      https://github.com/tg-cloud/tks-platform/blob/main/keycloak/values-override.yaml
  링크를 참고하여 마스터 노드의 root 계정에서 $HOMEU/_w/chart-keycloak 경로에 values-override.yaml 파일을 생성

  4.2. JKS 방식 values-override.yaml
  > CertManager로 jks형식의 인증서를 생성한 경우 JKS 방식으로 인증서 구성
    1. values-override.yaml 파일을 생성
      https://github.com/tg-cloud/tks-platform/blob/main/keycloak/values-override.yaml
  링크를 참고하여 마스터 노드의 root 계정에서 $HOMEU/_w/chart-keycloak 경로에 values-override.yaml 파일을 생성

      주요 value 목록:
      - tls: 외부 Secret 사용, truststore/keystore 파일명 및 패스워드 설정
      - ingress: nginx 사용, 인증서 Secret 및 client cert 인증 설정
      - extraEnv: HTTPS 경로, 인증서 경로 환경변수 설정

    2. 수동으로 Secret에 Helm metadata 추가
      ```bash
      # JKS 방식으로 인증서 구성시
      kubectl patch secret $cert_domain-tls   -n keycloak   -p '{"metadata": {
        "annotations": {
          "meta.helm.sh/release-name": "keycloak",
          "meta.helm.sh/release-namespace": "keycloak"
        },
        "labels": {
          "app.kubernetes.io/managed-by": "Helm"
        }
      }}'
      ```

  Helm이 관리하지 않는 Secret을 차트에서 사용하려고 할 때 발생하는 오류를 해결하기 위해 기존 Secret에 Helm 관련 메타데이터를 수동으로 추가




## 5. NFS Storage 설치 (미설치의 경우)

> Keycloak 네임스페이스의 PostgreSQL Pod에 바인딩될 Persistent Volume(PV) 프로비저닝을 위한 NFS Storage를 설치 및 구성합니다.

  가이드 링크: https://tgcloud.atlassian.net/wiki/spaces/dks3nd/pages/194084931




## 6. Keycloak 배포

> Helm을 통해 TLS 구성이 포함된 Keycloak을 Kubernetes Cluster의 keycloak namespace에 배포합니다.

  ```bash
  helm install -n keycloak keycloak $HOMEU/_w/chart-keycloak/ -f $HOMEU/_w/chart-keycloak/values-override.yaml
  ```




## 7. Keycloak Domain 접근을 위한 네임 리졸루션 설정

> 클라이언트에서 Keycloak 도메인을 올바르게 인식하기 위한 DNS, hosts 정보를 설정합니다.

1. DNS 설정
  윈도우 dns 설정:
    시작 메뉴 → 설정 → 네트워크 및 인터넷 → 네트워크 및 공유 센터 → 현재 네트워크 연결 → 속성 → TCP/IPv4 → 속성 → DNS 설정
  리눅스 dns 설정: sudo vi /etc/resolv.conf




2. hosts 설정

  ```bash
  vi /etc/hosts

  {{Keycloak 서버 또는 Ingress 컨트롤러의 주소}} keycloak.tg-cloud.co.kr
  ```

  윈도우 hosts 파일 경로: C:\Windows\System32\drivers\etc\hosts
  리눅스 hosts 파일 경로: /etc/hosts




## 8. Keycloak Domain 접속 정보

> 로컬 PC에서 keycloak에 접속하기 위한 주요 정보입니다.

  - 접속 URL: https://keycloak.tg-cloud.co.kr
  - 초기 ID/PW: admin/admin
  - VPN을 통해 내부망 접속 필요




## 9. Keycloak 관리자 계정 ID, Password 변경

> 기존의 설정을 그대로 유지하면서 관리자 계정의 ID와 Password를 변경하는 방법을 설명합니다. values.yaml 파일을 따로 수정할 필요 없이 빠르게 변경할 수 있습니다.

  ```bash
  helm upgrade keycloak bitnami/keycloak \
    --set auth.adminUser=newadmin \
    --set auth.adminPassword=newpassword \
    --reuse-values
  ```




## 10. Keycloak 삭제

> Helm을 통해 배포된 Keycloak과 바인딩된 볼륨을 삭제하는 방법과 삭제 시 주의사항을 설명합니다.

  ```bash
  helm uninstall -n keycloak keycloak
  kubectl delete pvc -n keycloak data-keycloak-postgresql-0
  ```
  
  주의사항:
    - 만약 Keycloak을 재설치하거나 전히 초기화하려는 경우, 기존의 PVC가 남아있으면 이전 데이터가 유지되어 초기화되지 않은 상태로 실행될 수 있음
    - 기존 PVC가 남아 있으면 Helm 재설치 시 충돌이 발생하거나, 예기치 않은 동작을 유발
    - Persistent Volume Claim(PVC)은 기본적으로 자동 삭제되지 않으므로, kubectl delete pvc 명령을 따로 실행하여 PVC를 수동으로 삭제
    - PVC 삭제 시 PV는 reclaimPolicy에 따라 자동 삭제되거나 그대로 남아있을 수 있으므로 재설치를 위해 완전히 정리하려면 PV 상태도 확인