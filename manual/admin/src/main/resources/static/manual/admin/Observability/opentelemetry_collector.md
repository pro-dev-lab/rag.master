# OpenTelemetry Collector

> OpenTelemetry 는 Observability(관측성) 데이터(메트릭, 로그, 트레이스)를 수집하고 처리하는 표준 프레임워크입니다. Kubernetes 환경에서는 Operator와 Collector를 활용하여 자동화된 배포 및 데이터 수집을 수행할 수 있습니다.

---

## 목차

1. [개요](#1-개요)
2. [OpenTelemetry Operator 설치](#2-opentelemetry-operator-설치)
3. [RBAC 설정](#3-rbac-설정)
4. [OpenTelemetry Collector 설치](#4-opentelemetry-collector-설치)
5. [서비스 엔드포인트 구성](#5-서비스-엔드포인트-구성)
6. [NodePort 설정](#6-nodeport-설정)
7. [Collector YAML 설정 상세](#7-collector-yaml-설정-상세)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. 개요

OpenTelemetry Operator 는 Kubernetes 환경에서 OpenTelemetry Collector 의 자동 배포 및 구성을 관리하는 컨트롤러입니다. 사용자 친화적인 CRD(Custom Resource Definition)를 제공하여 Collector를 쉽게 관리할 수 있습니다.

주요 기능은 다음과 같습니다:
- Collector 자동 배포 및 관리
- Observability 데이터 수집 자동화
- 애플리케이션 자동 Instrumentation

Collector 는 다음의 파이프라인을 사용하여 데이터를 처리합니다:
- Receivers: 데이터 수집
- Processors: 데이터 가공 및 필터링
- Exporters: 외부 시스템 전송

---

## 2. OpenTelemetry Operator 설치

OpenTelemetry Operator 는 Helm 차트를 통해 설치합니다. 먼저, Helm 저장소를 추가하고 업데이트한 후, Operator를 설치합니다.

### Helm 저장소 추가 및 업데이트

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update
```

### Operator 설치

Namespace: `opentelemetry` (가변적)

```bash
helm install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --create-namespace --namespace opentelemetry \
  --set "manager.collectorImage.repository=<내부 Registry 주소>" \
  --set admissionWebhooks.certManager.enabled=true \  # 이미 설치된 Cert-Manager 사용
  --set admissionWebhooks.autoGenerateCert.enabled=false  # 자동 인증서 생성 비활성화
```

### 설치 확인 방법

설치 후 Operator Pod 상태를 확인합니다.

```bash
kubectl get pods -n opentelemetry
kubectl logs -n opentelemetry <operator-pod-name>
```

---

## 3. RBAC 설정

Collector 가 Kubernetes 리소스 정보를 수집할 때 필요한 권한을 제공하기 위해 ClusterRole, ClusterRoleBinding 을 생성하고 OpenTelemetryCollector 서비스어카운트에 연결해야 합니다. TKS 플랫폼 레파지토리의 OpenTelemetry > RBAC.yaml 을 참조하세요.

### RBAC 설정 적용

```bash
kubectl apply -f RBAC.yaml
```

---

## 4. OpenTelemetry Collector 설치

Collector 는 Kubernetes의 CRD(Custom Resource Definition)를 통해 YAML 파일을 배포하여 설치합니다.   
Collector 는 Kubernetes 의 Deployment 리소스로 배포하는 Deployment 모드 방식으로 배포합니다. 
TKS 플랫폼 레파지토리의 OpenTelemetry > collector-deployment_mode.yaml 을 참조하세요.

### Collector 배포

```bash
kubectl apply -f collector-deployment_mode.yaml
```

### 설치 확인 방법

Collector Pod 상태를 확인합니다.

```bash
kubectl get pods -n opentelemetry
kubectl describe pod -n opentelemetry <collector-pod-name>
```

---

## 5. 서비스 엔드포인트 구성

Collector 는 Kubernetes 서비스로 배포되어 있으며, 이를 통해 데이터를 수집합니다. 클러스터 내의 각 서비스는 다음 형태의 도메인을 사용하여 접근합니다.


```bash
opentelemetry-collector-collector.opentelemetry.svc.<가변적 도메인 또는 cluster.local>:4317
```

---

## 6. NodePort 설정

클러스터 외부에서 Collector 로 데이터를 전송하려면 Collector 의 Ingress 또는 NodePort 서비스를 구성하여 외부 접근을 허용합니다.  
아래의 예시에서는 NodePort 를 구성합니다.

### NodePort 구성 YAML

```yaml
apiVersion: v1
kind: Service
metadata:
  name: opentelemetry-collector-nodeport
  namespace: opentelemetry
spec:
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
      nodePort: 30317
    - name: otlp-http
      port: 4318
      targetPort: 4318
      nodePort: 30318
  selector:
    app.kubernetes.io/component: opentelemetry-collector
  type: NodePort
```

---

## 7. Collector YAML 설정 상세

Collector 의 구성은 다음 주요 항목으로 이루어져 있으며, 각각의 설정 역할은 아래와 같습니다:

- **기본 설정**: 이미지 주소 및 리소스 요청 및 제한 정의
- **Receivers**: 애플리케이션으로부터 데이터를 수집하는 프로토콜 설정
- **Processors**: 수집된 데이터를 필터링하고 변환 및 배치 처리
- **Exporters**: 최종적으로 데이터를 전달할 시스템 정의 (Tempo, Loki 등)

---

## 8. 트러블슈팅

설치 및 운영 중 흔히 발생할 수 있는 문제와 해결 방법입니다:

- **데이터 미수집 문제**
    - 서비스 도메인 및 포트 설정 검토
    - Pod 로그 분석

- **RBAC 권한 오류**
    - 권한 설정 파일 재적용 및 확인

- **리소스 부족에 따른 재시작**
    - 리소스 요청 및 제한 조정

- **Loki로 로그가 전송되지 않을 때**
    - 헤더 `X-Scope-OrgID` 설정 확인
    - Loki 서비스 접근성 확인

### 유용한 트러블슈팅 명령어

- Pod 상태 점검:
```bash
kubectl get pods -n opentelemetry
kubectl describe pod <collector-pod-name> -n opentelemetry
kubectl logs -n opentelemetry <collector-pod-name>
```

- 서비스 점검:
```bash
kubectl get svc -n opentelemetry
kubectl describe svc <service-name> -n opentelemetry
```

- 이벤트 조회:
```bash
kubectl get events -n opentelemetry --sort-by=.metadata.creationTimestamp
```


---

