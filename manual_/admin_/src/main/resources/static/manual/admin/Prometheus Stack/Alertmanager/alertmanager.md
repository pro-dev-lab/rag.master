# Alertmanager

> Prometheus Alertmanager는 Prometheus에서 생성된 알림(Alert) 을 수신하고, 이를 집계, 그룹화, 라우팅, 알림 전송하는 역할을 하는 알림 관리 도구입니다.

---

## 목차 

1. [Alert Pipeline](#1-alert-pipeline)
2. [Alert Rule](#2-alert-rule)

## 1. Alert Pipeline

> Prometheus가 알림(Alert)을 발생시키면, Alertmanager가 이 알림을 받아서 다음과 같은 과정을 통해 최종적으로 알림을 보냅니다.

1. 수신(Receiving Alerts)

    Prometheus가 Alert를 POST ``/api/v2/alerts``로 Alertmanager에 전달합니다.

2. 그룹핑(Grouping)

    비슷한 Alert를 묶습니다.
    group_by 설정에 따라 특정 라벨(label)이 같은 Alert끼리 하나의 그룹으로 묶습니다.
    예) 같은 ``service=web`` 인 Alert들을 하나로 묶기

3. 분별(Matching / Routing)

    Alertmanager는 수신한 Alert를 Routing Tree를 통해 어떤 경로로 보낼지 결정합니다.
    **match / match_re** 조건을 통해 어떤 알림을 어떤 **receiver(수신자)** 에게 보낼지 판단합니다.

4. 금지(Inhibition)

    어떤 알림이 이미 다른 심각한 Alert로 커버되는 경우, 알림을 **억제**합니다.
    예) 서버 다운 경고가 이미 있는 경우, 같은 서버의 디스크 경고는 억제할 수 있음.

5. 재시도 및 지연(Waiting / Retry)

    알림을 보내기 전에 group_wait, group_interval로 딜레이를 줄 수 있습니다.
    실패한 경우 **재시도(Retry)** 로직도 있습니다.

6. 전달(Sending to Receiver)

    최종적으로 Email, Slack, MS Teams, Webhook 등 설정된 Receiver에게 알림을 보냅니다.

```yaml
"global":           # Alertmanager 전체에서 사용하는 글로벌 설정
"inhibit_rules":    # 특정 조건의 경고 발생 시 다른 경고를 억제하는 규칙
"receivers":        # 알람을 받을 대상 정의 (Email, MsTeams, Slack 등)
"route":            # 어떤 알림을 어떤 receiver로 보낼지 규칙 작성
  "group_by":       # 어떤 라벨 기준으로 알림을 그룹핑할지 설정
  "routes":         # 세부 라우팅 규칙 목록
```

TKS 플랫폼 레파지토리 prometheus-stack > manifests > alertmanager-secret.yaml 참조

- receivers webhoook 설정 예시

```yaml
"receivers":
- "name": "<Receiver Name>"
  "webhook_configs":
  - "url": "<Webhook 전달한 Endpoint>"
    "send_resolved": false
    "max_alerts": 200
    "http_config":  # 필요한 경우 추가 (Optional)
      "basic_auth":
        "username": "<username>"
        "password": "<password>"
```

- route Matchers 설정 예시

```yaml
"routes":
- "matchers":   # matching 조건 설정
  - "severity = <일치하는 Alert Severity 설정값>"
  - 'namespace=~"<제외할 네임스페이스>"'
  "receiver": "<Receiver Name>"
```

## 2. Alert Rule

> Prometheus는 단순히 메트릭(metric)을 수집할 뿐만 아니라,
특정 조건이 발생했을 때 자동으로 "경고(Alert)"를 생성할 수 있어요.
이때, 어떤 상황을 "이상 상태"로 간주할지를 정의하는 규칙이 바로 Alert Rule입니다.

Alert Rule 동작 흐름  

1. Prometheus가 메트릭 데이터를 주기적으로 수집

2. Alert Rule 조건에 맞는지 매 평가 주기마다 확인

3. 조건을 만족하면 "활성화된(Alerting)" 상태로 변경

4. Prometheus → Alertmanager로 Alert 전송

5. Alertmanager가 적절한 사람/시스템으로 알림 전송

Alert Rule 기본 구조

```yaml
groups:   # 여러 Alert Rule을 묶는 그룹
- name: Cluster   # 그룹 이름
  rules:    # 이 그룹에 속한 각각의 Alert Rule
    - alert: High Cluster CPU Utilisation issue   # 알림 이름
      annotations:    # Alert 설명용 필드
        description: "Cluster CPU Utilisation > 80%"
        summary: "High Cluster CPU Utilisation detected."
        alertname_kr: 5분 평균 클러스터 CPU 사용률 80% 초과
      expr: (avg by(cluster) (rate(node_cpu_used_seconds_total{job="node-exporter"}[5m])) * 100 ) > 80    # 조건식
      for: 1m   # (선택) 2분 동안 조건을 만족해야 Alert 발생
      labels:   # 추가 라벨 ( 중요도나 서비스 정보 등 )
        cluster: '{{ $externalLabels.cluster }}'
        grade: warning
        type: Status
        job: node-exporter
        severity: warning
        notification_channel: "tks-alertmanager"
```

TKS 플랫폼 레파지토리 prometheus-stack > manifests > 각 {PrometheusRule}.yaml 참조

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  labels:
    app.kubernetes.io/component: prometheus
    app.kubernetes.io/instance: k8s
    app.kubernetes.io/name: prometheus
    app.kubernetes.io/part-of: kube-prometheus
    app.kubernetes.io/version: 2.53.0
    prometheus: k8s
    role: alert-rules
  name: < Prometheus Rule Name >
  namespace: monitoring
spec:
  groups:
  - name: < Alert Group Name >
```

새로운 Alert Rule 정의하는 경우 기존 Alert Group 에 추가하거나 PrometheusRuleCRD 설정에 맞도록 정의하여 새로운 ``kind: PrometheusRule`` yaml 파일 생성

