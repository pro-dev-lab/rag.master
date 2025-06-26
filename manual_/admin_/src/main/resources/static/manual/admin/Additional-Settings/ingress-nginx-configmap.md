# Ingress-Nginx-Controller ConfigMap 추가 설정

> 쿠버네티스 클러스터를 구성한 후 Ingress Nginx Controller의 ConfigMap 추가 설정을 통해 로그 포맷 변경, 버퍼 크기 조정, 압축 설정 등 네트워크 성능과 디버깅을 개선하는 방법을 다룹니다.

---

## 목차

1. [개요](#1-개요)
2. [Ingress Nginx ConfigMap 추가 설정](#2-ingress-nginx-configmap-추가-설정)
3. [설정 적용 방법](#3-설정-적용-방법)
4. [설정 검증 방법](#4-설정-검증-방법)
5. [트러블슈팅](#5-트러블슈팅)

---

## 1. 개요

Ingress Nginx Controller 는 클러스터로 들어오는 외부 트래픽을 관리하는 중요한 컴포넌트로, 적절한 ConfigMap 설정을 통해 다양한 네트워크 성능 최적화와 문제 해결이 가능합니다.

### 주요 설정 영역

- 로그 포맷 설정
- 버퍼 크기 조정
- HTTP 압축 설정
- 어노테이션 허용 설정

---

## 2. Ingress Nginx ConfigMap 추가 설정

Ingress Nginx Controller 의 동작을 최적화하기 위해 ConfigMap 에 여러 설정값을 추가할 수 있습니다. 아래는 주요 설정 항목과 그 목적에 대한 상세 설명입니다.

### 2.1 로그 포맷 설정 (log-format-upstream)

**설정 목적**:
Ingress Nginx Controller 의 로그 출력 형식을 사용자 정의하여, 네임스페이스 정보와 같은 추가 정보를 포함시켜 디버깅과 트러블슈팅을 용이하게 합니다.

**설정 내용**:
```yaml
log-format-upstream: >-
  $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent 
  "$http_referer" "$http_user_agent" $request_length $request_time [$proxy_upstream_name] 
  [$proxy_alternative_upstream_name] $upstream_addr $upstream_response_length 
  $upstream_response_time $upstream_status $req_id $namespace
```

**설정 효과**:
- 표준 Nginx 로그 형식에 더해 다음 정보를 추가로 기록:
    - `$request_length`: 요청 길이(바이트)
    - `$request_time`: 요청 처리 시간
    - `$proxy_upstream_name`: 프록시로 연결된 업스트림 서버명
    - `$proxy_alternative_upstream_name`: 대체 업스트림 서버명
    - `$upstream_addr`: 업스트림 서버 주소
    - `$upstream_response_length`: 업스트림 응답 길이
    - `$upstream_response_time`: 업스트림 응답 시간
    - `$upstream_status`: 업스트림 서버 응답 상태 코드
    - `$req_id`: 요청 고유 ID
    - `$namespace`: 요청이 처리되는 쿠버네티스 네임스페이스

**로그 포맷 활용 사례**:
- 특정 네임스페이스에서 발생하는 오류 패턴 분석
- 응답 시간이 긴 요청 식별 및 최적화
- 요청 ID를 통한 전체 요청 흐름 추적

### 2.2 버퍼 크기 설정 (proxy-buffer-size)

**설정 목적**:
HTTP 응답 헤더를 처리할 때 사용되는 버퍼의 크기를 확장하여, 대용량 데이터나 복잡한 인증 정보가 포함된 응답을 올바르게 처리합니다.

**설정 내용**:
```yaml
proxy-buffer-size: 512k
proxy-buffers-number: '8'
proxy-busy-buffers-size: 1024k
```

**설정 배경**:
- 기본 버퍼 크기는 4KB로, OIDC(OpenID Connect) 인증과 같은 복잡한 헤더나 쿠키를 처리할 때 불충분
- 버퍼 크기가 작으면 502 Bad Gateway 오류가 발생할 수 있음
- 특히 Keycloak과 같은 인증 서비스 리다이렉트 시 응답 헤더가 크게 증가

**상세 설정 항목 설명**:
- `proxy-buffer-size`: 업스트림 서버 응답의 첫 부분을 읽는 버퍼 크기 (512KB로 설정)
- `proxy-buffers-number`: 각 요청에 할당되는 버퍼의 수 (8개로 설정)
- `proxy-busy-buffers-size`: 클라이언트에 응답을 보내는 동안 사용할 수 있는 버퍼의 최대 크기 (1024KB로 설정)

### 2.3 HTTP 압축 설정 (http-snippet)

**설정 목적**:
HTTP 응답 압축을 활성화하여 대역폭 사용량을 줄이고, 특히 Grafana와 같은 웹 애플리케이션의 로딩 시간을 단축합니다.

**설정 내용**:
```yaml
http-snippet: |
  gzip on;
  gzip_types text/plain text/javascript application/javascript text/css application/json application/xml image/svg+xml;
  gzip_vary on;
  gzip_comp_level 5;
  gzip_min_length 1024;
  gzip_proxied any;
```

**상세 설정 항목 설명**:
- `gzip on`: gzip 압축 활성화
- `gzip_types`: 압축할 MIME 타입 지정
    - `text/plain`: 일반 텍스트 파일
    - `text/javascript`, `application/javascript`: 자바스크립트 파일
    - `text/css`: CSS 스타일시트
    - `application/json`: JSON 응답
    - `application/xml`, `image/svg+xml`: XML 및 SVG 이미지
- `gzip_vary on`: 'Vary: Accept-Encoding' 헤더 추가하여 캐싱 최적화
- `gzip_comp_level 5`: 압축 레벨 설정 (1-9 범위, 5는 압축률과 CPU 사용량의 균형점)
- `gzip_min_length 1024`: 최소 1KB 이상의 응답만 압축 (작은 파일 압축은 비효율적)
- `gzip_proxied any`: 모든 프록시 요청에 대해 압축 적용

**압축 설정의 효과**:
- 그라파나와 같은 대시보드 애플리케이션의 초기 로딩 시간 단축
- 네트워크 대역폭 사용량 감소 (일반적으로 70-90% 압축률)
- 특히 JavaScript와 CSS 파일의 전송 크기 감소로 인한 성능 향상

### 2.4 스니펫 어노테이션 허용 설정

**설정 목적**:
Ingress 리소스에서 커스텀 Nginx 설정 스니펫을 사용할 수 있도록 허용합니다. 

**설정 내용**:
```yaml
allow-snippet-annotations: 'true'
```

**설정 효과**:
- Ingress 리소스에서 `nginx.ingress.kubernetes.io/configuration-snippet`과 같은 어노테이션을 통해 추가 Nginx 설정을 적용 가능
- 특정 서비스나 경로에 대한 세부 조정이 가능해짐
- 보안 정책, 헤더 추가, 리다이렉션 등의 고급 기능 구현 가능

**사용 예시**:
```yaml
annotations:
  nginx.ingress.kubernetes.io/configuration-snippet: |
    more_set_headers "X-Frame-Options: DENY";
    more_set_headers "X-Content-Type-Options: nosniff";
```

---

## 3. 설정 적용 방법

### 3.1 ConfigMap 생성 또는 수정

아래 명령어를 사용하여 ConfigMap을 생성하거나 기존 ConfigMap을 수정합니다.

```bash
# ConfigMap YAML 파일 생성
cat <<EOF > ingress-nginx-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
data:
  allow-snippet-annotations: 'true'
  log-format-upstream: >-
    $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" 
    "$http_user_agent" $request_length $request_time [$proxy_upstream_name] 
    [$proxy_alternative_upstream_name] $upstream_addr $upstream_response_length 
    $upstream_response_time $upstream_status $req_id $namespace
  proxy-buffer-size: 512k
  proxy-buffers-number: '8'
  proxy-busy-buffers-size: 1024k
  http-snippet: |
    gzip on;
    gzip_types text/plain text/javascript application/javascript text/css application/json application/xml image/svg+xml;
    gzip_vary on;
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_proxied any;
EOF

# ConfigMap 적용
kubectl apply -f ingress-nginx-configmap.yaml
```

### 3.2 기존 ConfigMap 업데이트

이미 존재하는 ConfigMap을 수정하려면 아래 명령어를 사용합니다.

```bash
# 기존 ConfigMap 편집
kubectl edit configmap ingress-nginx -n ingress-nginx
```

### 3.3 설정 적용 후 Ingress Controller 재시작

설정이 적용된 후 Ingress Controller를 재시작하여 변경사항을 적용합니다.

```bash
# Ingress Controller Pod 찾기
kubectl get pods -n ingress-nginx

# Ingress Controller 재시작
kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx
```

---

## 4. 설정 검증 방법

적용된 설정이 올바르게 작동하는지 확인하기 위한 방법입니다.

### 4.1 ConfigMap 설정 확인

```bash
kubectl get configmap ingress-nginx -n ingress-nginx -o yaml
```

### 4.2 로그 형식 검증

```bash
# Ingress Controller Pod 로그 확인
kubectl logs -n ingress-nginx $(kubectl get pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -o jsonpath='{.items[0].metadata.name}')
```

### 4.3 압축 설정 검증

```bash
# 테스트 요청 보내기
curl -I -H "Accept-Encoding: gzip" https://your-ingress-domain/
```

예상 응답에 `Content-Encoding: gzip` 헤더가 포함되어 있어야 합니다.

### 4.4 버퍼 설정 검증

OIDC 인증 리다이렉트와 같은 대용량 헤더 요청을 테스트하여 502 오류가 발생하지 않는지 확인합니다.

---

## 5. 트러블슈팅

Ingress Nginx 설정 관련 문제 해결 방법입니다.

### 5.1 일반적인 문제와 해결 방법

- **502 Bad Gateway 오류 지속 발생**
    - 버퍼 크기가 여전히 부족할 수 있음
    - `proxy-buffer-size`와 `proxy-busy-buffers-size` 값을 더 증가시켜 보세요
    - Ingress Controller 로그에서 구체적인 오류 메시지 확인

- **압축이 적용되지 않는 경우**
    - 클라이언트 요청에 `Accept-Encoding: gzip` 헤더가 포함되었는지 확인
    - `gzip_types`에 해당 콘텐츠 타입이 포함되었는지 확인
    - 파일 크기가 `gzip_min_length` 설정보다 큰지 확인

- **로그 형식 변경이 적용되지 않는 경우**
    - Ingress Controller가 재시작되었는지 확인
    - ConfigMap이 올바른 네임스페이스에 적용되었는지 확인

### 5.2 유용한 디버깅 명령어

- ConfigMap 내용 확인:
```bash
kubectl describe configmap ingress-nginx -n ingress-nginx
```

- Ingress Controller 상태 점검:
```bash
kubectl describe pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

- 이벤트 로그 확인:
```bash
kubectl get events -n ingress-nginx --sort-by=.metadata.creationTimestamp
```

- Nginx 설정 검증:
```bash
kubectl exec -it $(kubectl get pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -o jsonpath='{.items[0].metadata.name}') -n ingress-nginx -- /bin/bash -c "nginx -T"
```

---