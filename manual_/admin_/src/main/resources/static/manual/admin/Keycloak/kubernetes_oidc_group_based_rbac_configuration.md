# kubernetes OIDC Group 기반 RBAC 구성

> Keycloak과 연동된 AD 사용자와 keycloak realm users 기반으로 Kubernetes OIDC 인증과 그룹 기반 RBAC을 구성하는 전체 과정을 설명합니다.



## 목차

1. [OIDC 토큰 발급](#1-oidc-토큰-발급)  
2. [OIDC 사용자 자격 정보 등록 및 컨텍스트 구성](#2-oidc-사용자-자격-정보-등록-및-컨텍스트-구성)  
3. [Keycloak group에 대한 rbac 구성](#3-keycloak-group에-대한-rbac-구성)  
4. [권한 테스트](#4-권한-테스트)  
5. [AD 사용자와 내부 사용자 간 RBAC 설정의 특징](#5-ad-사용자와-내부-사용자-간-rbac-설정의-특징)  



## 1. OIDC 토큰 발급

> Kubernetes OIDC 인증에 사용하기 위한 Keycloak의 사용자 계정에 대한 ID 토큰과 Refresh 토큰을 발급받습니다.

1. keycloak AD 사용자의 토큰을 발급받는 경우

  ```bash
  OIDC_ISSER_URL="https://keycloak.tg-cloud.co.kr/realms/tks-sso"
  OIDC_TOKEN_ENDPOINT_URL="https://keycloak.tg-cloud.co.kr/realms/tks-sso/protocol/openid-connect/token"
  OIDC_CLIENT_ID="oidc-client"
  OIDC_CLIENT_SECRET="{{oidc-client 클라이언트의 secret}}"
  OIDC_USER="hh.lee"
  OIDC_GROUP="TCP개발2팀"
  OIDC_PASSWORD='Timegate1!'
  OIDC_TOKENS=$(
      curl -k -X POST -s \
          -H "Content-Type:application/x-www-form-urlencoded" \
          -d "scope=openid" \
          -d "grant_type=password" \
          -d "client_id=${OIDC_CLIENT_ID}" \
          -d "client_secret=${OIDC_CLIENT_SECRET}" \
          -d "username=${OIDC_USER}" \
          -d "password=${OIDC_PASSWORD}" \
          "${OIDC_TOKEN_ENDPOINT_URL}"
  )
  ```

2. keycloak 내부 사용자의 토큰을 발급받는 경우

  ```bash
    OIDC_ISSER_URL="https://keycloak.tg-cloud.co.kr/realms/tks-sso"
    OIDC_TOKEN_ENDPOINT_URL="https://keycloak.tg-cloud.co.kr/realms/tks-sso/protocol/openid-connect/token"
    OIDC_CLIENT_ID="account"
    OIDC_CLIENT_SECRET="{{account 클라이언트의 secret}}"
    OIDC_USER="test-user"
    OIDC_GROUP="test-group"
    OIDC_PASSWORD='Timegate1!'

    OIDC_TOKENS=$(
        curl -k -X POST -s \
            -H "Content-Type:application/x-www-form-urlencoded" \
            -d "scope=openid" \
            -d "grant_type=password" \
            -d "client_id=${OIDC_CLIENT_ID}" \
            -d "client_secret=${OIDC_CLIENT_SECRET}" \
            -d "username=${OIDC_USER}" \
            -d "password=${OIDC_PASSWORD}" \
            "${OIDC_TOKEN_ENDPOINT_URL}"
    )
  ```

  keycloak openid-configuration 정보와 사용자 정보를 기반으로 환경변수를 설정하고 keycloak의 OIDC 인증 토큰을 발급

  ```bash
  OIDC_USER_ID_TOKEN=$(echo "${OIDC_TOKENS}" | jq -r .id_token)
  OIDC_USER_REFRESH_TOKEN=$(echo "${OIDC_TOKENS}" | jq -r .refresh_token)
  ```

  받은 JSON 응답에서 ID 토큰과 Refresh 토큰을 추출

  ```bash
  echo $OIDC_USER_ID_TOKEN
  echo $OIDC_USER_REFRESH_TOKEN
  ```

  ID 토큰과 Refresh 토큰을 출력하여 확인


## 2. OIDC 사용자 자격 정보 등록 및 컨텍스트 구성

> 연동된 keycloak user에 대한 사용자 자격증명을 kubernetes cluster에 구성합니다.

  ```bash
  kubectl config use-context kubernetes-admin
  ```

  kubeconfig에서 "kubernetes-admin" context를 현재 사용 context로 활성화
  이 context는 devclu0.io 클러스터에 kubernetes-admin 사용자로 접근하는 설정임

  ```bash
  kubectl config get-users

  Ex)
  NAME
  kubernetes-admin
  ```

  현재 생성하려는 사용자가 존재하지 않음을 확인 

  ```bash
  kubectl config set-credentials "${OIDC_USER}"  --auth-provider=oidc    --auth-provider-arg=idp-issuer-url="${OIDC_ISSER_URL}"    --auth-provider-arg=client-id="${OIDC_CLIENT_ID}"     --auth-provider-arg=refresh-token="${OIDC_USER_REFRESH_TOKEN}"    --auth-provider-arg=id-token="${OIDC_USER_ID_TOKEN}"
  ```

  kubectl이 클러스터에 접근할 때 사용할 사용자 자격 정보(credentials)를 추가 (OIDC 기반)
  
  ```bash
  kubectl config get-users

  Ex)
  NAME
  kubernetes-admin
  hh.lee # ${OIDC_USER}가 생성됨 
  ```

  keycloak 사용자가 추가되었는지 확인

  ```bash
  kubectl config set-context "${OIDC_USER}-context" --user="${OIDC_USER}" --cluster=userclu1.io
  ```

  앞서 생성한 OIDC 사용자를 기반으로, kubectl이 사용할 컨텍스트를 생성



## 3. Keycloak group에 대한 rbac 구성

> kubernetes cluster에 role, rolebinding 리소스를 생성하여 Keycloak의 사용자 그룹에 특정 네임스페이스의 특정 리소스에 대한 권한을 부여

  ```bash
  cat << EOF | kubectl apply -f -
  apiVersion: rbac.authorization.k8s.io/v1
  kind: Role
  metadata:
    namespace: default
    name: role-ns-default-viewer
  rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "watch", "list", "create", "delete"]
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: RoleBinding
  metadata:
    namespace: default ####권한 부여할 namespace 설저 
    name: rolebinding-ns-default-viewer
  subjects:
  - kind: Group
    name: TCP개발2팀
    apiGroup: rbac.authorization.k8s.io
  roleRef:
    kind: Role
    name: role-ns-default-viewer
    apiGroup: rbac.authorization.k8s.io
  EOF
  ```

  Kubernetes RBAC (Role-Based Access Control) 을 사용하여 특정 Group (예: TCP개발2팀) 에게 default 네임스페이스에서 pods 리소스에 대한 제한된 권한을 부여

  즉, 이 설정은 특정 사용자 그룹이 kubectl로 default 네임스페이스의 Pods를 조회하거나 생성/삭제할 수 있게 허용


## 4. 권한 테스트

> kube-apiserver에 요청을 통해 OIDC 사용자가 실제로 부여된 권한을 갖는지 확인하는 방법을 설명합니다.


  ```bash
  kubectl config use-context {{OIDC 사용자 이름}}-context

  Ex) kubectl config use-context hh.lee-context
  ```

  OIDC 사용자의 컨텍스트로 전환

  ```bash
  kubectl get po -n default

  Ex) 
  NAME                                            READY   STATUS    RESTARTS      AGE
  airflow-1723099151-postgresql-0                 1/1     Running   0             43d
  airflow-1723099151-redis-master-0               1/1     Running   0             43d
  airflow-1723099151-scheduler-546f7fcddb-ptprl   1/1     Running   1 (43d ago)   70d
  airflow-1723099151-web-774d487974-v4hfn         1/1     Running   0             43d
  airflow-1723099151-worker-0                     1/1     Running   0             43d
  numbers-api-545b9d9ccd-fjtvg                    1/1     Running   0             20d
  numbers-web-76447f6964-5fvz2                    1/1     Running   0             20d
  sleep-1-5b88cbd4bf-hbt6q                        1/1     Running   0             20d
  sleep-2-7f69798f94-6zhxh                        1/1     Running   0             20d
  ```

  권한이 있는 default 네임스페이스의 Pod 조회 → 성공

  ```bash
  kubectl get po -n kube-system

  Ex)
  Error from server (Forbidden): pods is forbidden: User "hh.lee" cannot list resource "pods" in API group "" in the namespace "kube-system"
  ```

  권한이 없는 kube-system 네임스페이스의 Pod 조회 → 실패 (권한 없음 메시지 기대)




## 5. AD 사용자와 내부 사용자 간 RBAC 설정의 특징

> Kubernetes 클러스터에서 Keycloak 기반 OIDC 인증을 사용하는 경우, Keycloak에 직접 생성한 내부 사용자와 Active Directory(AD)와 연동된 외부 사용자, 두 유형에 대해 RBAC 설정 방식과 OIDC 연동의 차이점을 비교합니다.

1. 공통점
  1. 두 OIDC 토큰을 curl로 받아 id_token과 refresh_token을 사용
  2. kubectl config set-credentials로 사용자를 추가
  3. RBAC은 Kubernetes의 Role + RoleBinding을 이용하여 Group 기준으로 권한 설정
  4. 테스트 방법 동일 (kubectl use-context, 리소스 접근 시도)




2. 차이점
  1. 사용자 소스
    - Keycloak 내부 사용자: Keycloak 내부에서 직접 생성한 사용자 (예: test-user)
    - Keycloak AD 연동 사용자: Active Directory(AD)에서 SSO를 통해 연동된 사용자 (예: hh.lee)
    
  2. OIDC Client ID
    - Keycloak 내부 사용자: 기본 제공 클라이언트인 account 사용
    - Keycloak AD 연동 사용자: 별도로 생성한 클라이언트 oidc-client 사용

  3. Group 설정 위치
    - Keycloak 내부 사용자: Keycloak 내부의 Group에 사용자를 수동으로 할당
    - Keycloak AD 연동 사용자: AD 그룹이 SSO를 통해 Keycloak에 자동 연동 또는 Keycloak에서 매핑(Mapping) 설정을 통해 그룹 부여

  4. Group 이름 예시
    - Keycloak 내부 사용자: test-group (Keycloak에 존재하는 내부 그룹)
    - Keycloak AD 연동 사용자: TCP개발2팀 (AD에서 연동되었거나 Keycloak에 매핑된 그룹)

  5. 토큰에 포함되는 그룹 정보 (groups 클레임)
    - Keycloak 내부 사용자: Keycloak에서 직접 설정한 groups 클레임에 그룹 정보 포함
    - Keycloak AD 연동 사용자: AD에서 가져오거나 Keycloak Group Mapper에 따라 토큰에 그룹 정보 포함
