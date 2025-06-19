# Fluentd와 Fluent Bit 운영 매뉴얼

>본 문서는 Fluentd와 Fluent Bit 설치 및 운영 가이드입니다.



## 목차
1. [사전 준비](#1-사전-준비)
2. [설치 및 설정](#2-설치-및-설정)
    - [Fluent Bit 관련 시스템 설정](#21-fluent-bit-관련-시스템-설정)
    - [OpenSearch 권한 설정(FluentD 연동용)](#22-opensearch-권한-설정fluentd-연동용) 
    - [FluentD Helm Chart 배포 가이드](#23-fluentd-helm-chart-배포-가이드)
    - [Fluent Bit Helm Chart 배포 가이드](#24-fluent-bit-helm-chart-배포-가이드)
3. [운영 및 모니터링](#3-운영-및-모니터링)

## 개요
**Fluentd와 Fluent Bit 차이점 및 역할**

Fluent Bit는 클러스터의 각 노드에서 로그를 수집하고, Fluentd는 이를 중앙에서 집계하여 OpenSearch로 전달합니다.\
이러한 구조에서 Fluent Bit은 로그 수집기(Collector) 역할을, Fluentd는 로그 전달자(Aggregator) 역할을 담당합니다.
![](img/fluentdiff.png)

**다음과 같은 흐름으로 구성됩니다:**

- 로그 소스 - 애플리케이션 로그, 시스템 로그, Kubernetes API 서버 로그, 컨테이너 로그
- Fluent Bit(Collector) - 각 노드에 DaemonSet으로 배포되어 로그를 수집
- Fluentd(Aggregator) - StatefulSet으로 배포되어 수집된 로그를 집계 및 처리
- OpenSearch - 로그 데이터 저장 및 검색
- OpenSearch Dashboards - 데이터 시각화 및 분석

```text
다양한 소스에서 발생한 로그 → Fluent Bit 수집 → Fluentd 처리 → OpenSearch 저장 → Dashboards 시각화
```

## 1. 사전 준비

1. ingress-nginx controller 로그 수집시 네임스페이스 추출 위한 Configmap 설정 추가
- ingress-nginx 네임스페이스의 ConfigMap (ingress-nginx)에 다음 항목을 추가합니다.
- data: 블록은 metadata: 와 같은 레벨에 위치해야 합니다.
```yaml
data:
  allow-snippet-annotations: 'true'
  log-format-upstream: >-
    $remote_addr - $remote_user [$time_local] "$request" $status
    $body_bytes_sent "$http_referer" "$http_user_agent" $request_length
    $request_time [$proxy_upstream_name] [$proxy_alternative_upstream_name]
    $upstream_addr $upstream_response_length $upstream_response_time
    $upstream_status $req_id $namespace
```

## 2. 설치 및 설정

1. 네임스페이스 생성 (namespace 명 logging 권장)
```bash
kubectl create namespace [namespace명]
```
2. Helm 설치 (미설치 상태인 경우)
```bash
wget https://get.helm.sh/helm-v3.15.3-linux-amd64.tar.gz
tar -zxvf helm-v3.15.3-linux-amd64.tar.gz
cd linux-amd64
sudo cp ./helm /usr/local/bin/helm
ls -al  /usr/local/bin/helm
```
3. Fluent Helm 차트 추가
```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
helm search repo
```

### 2.1 Fluent Bit 관련 시스템 설정
1. Too Many Open Files 오류 해결
DaemonSet으로 설치된 Fluent Bit Pod가 다음 오류로 인해 시작되지 않는 경우:
```bash
[error] [/src/fluent-bit/plugins/in_tail/tail_fs_inotify.c:360 errno=24] Too many open files
```
각 노드의 max_user_instances를 확인하고 값을 증가 시켜야합니다.

```bash
# 현재 값 확인
cat /proc/sys/fs/inotify/max_user_instances

# 일시적 상향
sudo sysctl fs.inotify.max_user_instances=1024
sudo sysctl -p

# 영구 적용
sudo vi /etc/sysctl.conf

# 아래 내용 추가
fs.inotify.max_user_instances=1024
```
>fs.inotify.max_user_instances는 사용자당 생성 가능한 inotify 인스턴스 수를 정의하며, 파일 시스템 이벤트 모니터링 수용량에 영향을 줍니다

### 2.2 OpenSearch 권한 설정(Fluentd 연동용)
1. 오류 발생 및 원인 분석
- Fluent Bit, Fluentd 를 모두 배포하였으나 오픈서치로 로그 수집이 안되는 상황 발생함.
- Fluentd 컨테이너 로그를 확인해보면 NoMethodError 등 warn 로그만 표시되고 오픈서치에 로그가 수집되지 않고 오픈서치에서 인덱스도 만들어지지 않는 상황
- 디버그를 위해 Fluentd 의 output 설정에 오픈서치 연동 네트워크 로그 출력 옵션 추가 (해결후 다시 제거함) with_transporter_log true 추가 후 Fluentd 재배포

```yaml
04_outputs.conf: |-
    <match app.workload-api.**>
       @type opensearch
       host "<opensearch-host>"
       port 31010
       scheme https
       user logstash
       password {password}
       ssl_verify false
       reconnect_on_error true
       reload_on_failure true
       reload_connections false
       logstash_format true
       logstash_prefix workload-api-application-log
       logstash_dateformat %Y.%m.%d
       with_transporter_log true
       <buffer time>
         @type file
         path /fluentd/log/opensearch-buffer/workload-api-application
         timekey_use_utc true
         timekey 1m
         flush_thread_count 16
         flush_interval 1s
         chunk_limit_size 10M
         queue_limit_length 16
         flush_mode interval
         retry_max_interval 30
         retry_timeout 10m
         overflow_action drop_oldest_chunk
       </buffer>
    </match>
```
- 위 옵션 적용 후 로그를 확인해보면 아래와 같은 로그가 출력됨
```bash
2024-08-27 07:57:56 +0000 [debug]: #0 fluent/log.rb:341:debug: < {"took":0,"errors":true,"items":[{"index":{"_index":"ingress-nginx-log-2024.08.27","_id":null,"status":403,"error":{"type":"security_exception","reason":"no permissions for [indices:admin/create] and User [name=logstash, backend_roles=[logstash], requestedTenant=null]"}}},{"index":{"_index":"ingress-nginx-log-2024.08.27","_id":null,"status":403,"error":{"type":"security_exception","reason":"no permissions for [indices:admin/create] and User [name=logstash, backend_roles=[logstash], requestedTenant=null]"}}},{"index":{"_index":"ingress-nginx-log-2024.08.27","_id":null,"status":403,"error":{"type":"security_exception","reason":"no permissions for [indices:admin/create] and User [name=logstash, backend_roles=[logstash], requestedTenant=null]"}}},{"index":{"_index":"ingress-nginx-log-2024.08.27","_id":null,"status":403,"error":{"type":"security_exception","reason":"no permissions for [indices:admin/create] and User [name=logstash, backend_roles=[logstash], requestedTenant=null]"}}}]}
2024-08-27 07:57:56 +0000 [info]: #0 fluent/log.rb:362:info: POST https://logstash:******@10.120.105.31:31010/_bulk [status:200, request:0.010s, query:0.000s]
```

**..no permissions for [indices:admin/create] and User [name=logstash, backend_roles=[logstash]]**

> Fluentd 에서 사용중인 logstash 계정이 오픈서치에 인덱스를 생성할 수 있는 권한(indices:admin/create)이 없다는 오류임.

---

2. 솔루션 - OpenSearch 권한 설정
Fluentd에서 사용 중인 logstash 계정에 인덱스 생성 권한을 부여하기 위해 다음 절차를 수행합니다:
  - 1. OpenSearch Dashboards 접속

    - OpenSearch Dashboards에 admin 계정으로 로그인합니다.\
        좌측 메뉴에서 Security > Roles 메뉴로 이동합니다.

  - 2. 기존 logstash 역할 확인

    - "logstash" 역할을 검색하여 상세 정보를 확인합니다.\
      현재 설정된 인덱스 권한이 'logstash-*','beats*'로 제한되어 있는 것을 확인할 수 있습니다.\
      기본 logstash 역할은 reserved 역할이므로 직접 수정이 불가능합니다.

  - 3. 새 역할 생성

    -  logstash 역할 상세 페이지에서 우측 상단의 Duplicate role 버튼을 클릭합니다.
      새 역할 이름을 "logstash_fluentd"로 지정합니다.

    -  Index permissions 섹션에서:
      Index patterns 항목에 * 패턴을 추가합니다 (모든 인덱스에 접근 가능)

    - Permissions 항목에 다음 권한들을 추가합니다:

      "crud"
      "create_index"
      "indices/create"
      ![](img/index-permission.png)
    -  Save role 버튼을 클릭하여 새 역할을 저장합니다.

  - 4. 사용자 권한 업데이트

    -  좌측 메뉴에서 Security > Internal users 메뉴로 이동합니다.
      "logstash" 사용자를 찾아 상세 정보를 확인합니다.
      Backend roles 섹션에서:

    -  기존 "logstash" 역할은 유지합니다
      새로 생성한 "logstash_fluentd" 역할을 추가합니다.


    -  Save changes 버튼을 클릭하여 변경사항을 저장합니다.


### 2.3 Fluentd Helm Chart 배포 가이드
1. 사전 참고
- Helm chart 를 통해 배포 (4.0 버전 주의사항 README 확인)\
[FluentD Helm Chart](https://github.com/fluent/helm-charts/blob/main/charts/fluentd/README.md)

- Image\
[Image](https://github.com/fluent/fluentd-kubernetes-daemonset)

- Fluent-opensearch-plugin\
[Fluent-opensearch-plugin](https://github.com/fluent/fluent-plugin-opensearch)

2. 배포 시 주의사항

| 구분   | 설정 |
|:------|:-----|
| **Image** | `fluent/fluentd-kubernetes-daemonset:v1.17.1-debian-opensearch-amd64-1.0` 사용 |
| **kind** | `StatefulSet` 설정 및 `replicaCount` 1 |
| **Output** | OpenSearch `NodePort(31010)` 사용, 계정: `logstash` |



3. 클러스터별 변경 사항

| 클러스터       | clustername 값 | storageClass 또는 설정 |
|:---------------|:---------------|:-----------------------|
| **platform.io** | platform.io     | csi-cephfs-sc           |
| **userclu1.io** | userclu1.io     | nfs-client              |
| **userclu2.io** | userclu2.io     | nfs-client              |
| **single.io**   | single.io       | persistence: false      |

>클러스터명과 storageClass 값은 **배포 전 반드시 수정**해야 합니다.

- tks-platform 깃헙 레파지토리 (최종 values 관리)\
https://github.com/tg-cloud/tks-platform/blob/main/fluent/fluentd_values.yaml

- 주요 내용 요약 :
```yaml
kind: "StatefulSet"
replicaCount: 1

image:
  repository: "fluent/fluentd-kubernetes-daemonset"
  tag: "v1.17.1-debian-opensearch-amd64-1.0"

persistence:
  enabled: true
  storageClass: "csi-cephfs-sc" # platform.io 기준 (다른 클러스터는 nfs-client)

plugins:
  - fluent-plugin-opensearch

env:
  - name: FLUENTD_CONF
    value: "../../../etc/fluent/fluent.conf"

```
### 2.4 Fluent Bit Helm Chart 배포 가이드
1. 사전 준비
- Fluent Bit을 Helm Chart를 이용해 위에서 생성했던 네임스페이스(logging)에 배포합니다.

- Helm  Chart : [Fluent-bit Helm Chart](https://github.com/fluent/helm-charts/blob/main/charts/fluent-bit/README.md)

2. 배포 전 주의사항
- Helm 버전에 맞지 않는 values.yaml 항목이나 잘못된 indent 설정이 있을 경우, 컨테이너 기동 실패 및 다음과 같은 오류 로그가 발생할 수 있습니다:

```bash
[engine] caught signal (SIGTERM)
[warn] [engine] service will shutdown in max 5 seconds
[info] [input] pausing cpu.0
[info] [output:stdout:stdout.0] thread worker #0 stopping...
[info] [output:stdout:stdout.0] thread worker #0 stopped
```
> values.yaml 파일 작성 시 indent(들여쓰기) 오류가 없도록 주의해야 합니다.

3. Fluent Bit 배포 가이드

- Helm Chart 설치
```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
helm install fluent-bit fluent/fluent-bit -n logging -f fluent-bit_values.yaml
```
**로그 수집 대상 및 파이프라인**

| 수집 대상                | 설명 |
|:---------------------------|:-----|
| ingress-nginx-controller    | 컨테이너 로그 수집 |
| Kubernetes Audit 로그       | API Server 감사 로그 수집 |
| workload-api                | Access Log, Application Log 별도 태깅 후 수집 |
| TKS Console                 | Gateway Access Log 및 서비스별 Application Log 수집 |
| kube-system 컨테이너        | 시스템 관련 컨테이너 로그 수집 |
| Host 및 Journal 메시지      | OS 레벨 및 시스템 이벤트 수집 |


**Values.yaml 주요 설정 (fluent-bit_values.yaml)**

```bash
# kind -- DaemonSet or Deployment
kind: DaemonSet

# replicaCount -- Only applicable if kind=Deployment
replicaCount: 1

image:
  repository: cr.fluentbit.io/fluent/fluent-bit
  pullPolicy: IfNotPresent

testFramework:
  enabled: true
  image:
    repository: busybox
    pullPolicy: Always
    tag: latest

serviceAccount:
  create: true

rbac:
  create: true
  nodeAccess: false

podSecurityPolicy:
  enabled: true

```
- 주의사항
  - DaemonSetVolumes 및 DaemonSetVolumeMounts 설정을 통해 호스트 경로 마운트 필수
     예: /var/log, /run/log/journal 등

  - systemd input 사용 시 /run/log/journal 경로 반드시 Mount 필요

  - values.yaml 파일 작성 시 Helm 버전에 맞는 키와 값을 사용하고, indent 오류를 주의할 것

  - 컨테이너 로그를 모니터링하여 배포 실패 여부 확인

  - 네임스페이스는 logging 고정 사용


## 3. 운영 및 모니터링

### 3.1 로그 확인
- Fluentd 로그 확인
```bash
# Fluentd 로그 확인
kubectl logs -f -l app.kubernetes.io/name=fluentd -n logging

# 특정 Fluentd 파드 로그 확인
kubectl logs -f fluentd-0 -n logging
```
- Fluent Bit 로그 확인
```bash
# 모든 Fluent Bit 파드 로그 확인
kubectl logs -f -l app.kubernetes.io/name=fluent-bit -n logging

# 특정 노드의 Fluent Bit 로그 확인
kubectl logs -f fluent-bit-xxxxx -n logging
```

### 3.2 Fluent Bit 설정 가이드
>Fluent Bit 입력(Input), 필터(Filter), 파서(Parser) 설정을 위한 기본 규칙입니다. 운영자는 아래 포맷에 맞춰 설정 파일을 작성합니다.

- Input 정의
    - Name: 입력 플러그인 이름 (tail 등)

    - Path: 수집할 파일 경로 지정 (/var/log/secure 등)

    - Parser: 사용할 파서 지정 (syslog 등)

    - DB: 오프셋 저장용 데이터베이스 파일 경로 설정

    - Mem_Buf_Limit: 메모리 버퍼 한계 지정 (예: 5MB)

    - 기타 옵션: Refresh_Interval, Read_from_Head 등 필요에 따라 설정

- Filter 정의
    -  Name: 필터 플러그인 이름 (modify 등)

    -  Match: 적용 대상 매칭 (journal.* 등)

    -  필드 수정: 불필요한 필드는 Remove, 필요한 데이터는 Add

    -  시간 포맷 설정: Time_Format 옵션으로 시간 포맷 통일

- Parser 정의
    -   Name: 파서 이름 (cri 등)

    -  Format: 데이터 포맷 유형 (regex 등)

    -   Regex: 데이터 파싱에 사용할 정규 표현식 설정

    -  Time_Key, Time_Format: 시간 인식 관련 필수 설정

- 작성 예시
```yaml
[INPUT]
    Name tail
    Path /var/log/secure
    Parser syslog
    DB /var/log/secure.db
    Mem_Buf_Limit 5MB
    Skip_Long_Lines On
    Refresh_Interval 10
    Read_from_Head false

[FILTER]
    Name modify
    Match journal.*
    Remove cap_effective
    Remove machine_id
    Remove boot_id
    Remove stream_id
    Add tks.logType SYSCL
    Time_Format %d/%b/%Y:%H:%M:%S %z

[PARSER]
    Name cri
    Format regex
    Regex ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<message>.*)$
    Time_Key time
    Time_Format %Y-%m-%dT%H:%M:%S.%L%z
```

> yaml 수정 후에는 재시작이 필요합니다.

### 3.3 Fluentd 설정 가이드
> Fluentd 설정 파일은 주로 source, filter, match 섹션으로 구성됩니다.

**기본 구성**

| 구분    | 설명                                      |
|---------|-------------------------------------------|
| source  | 데이터를 수집하는 입력 설정              |
| filter  | 수집한 데이터의 전처리 및 수정 설정       |
| match   | 데이터를 최종 목적지(출력)로 전달하는 설정 |


**설정 파일 작성 규칙**
- Source 정의
    - 수집할 대상과 포맷 지정

```yaml
<source>
  @type tail
  path /var/log/secure
  pos_file /var/log/td-agent/secure.pos
  tag secure.log
  format syslog
</source>
```

- Filter 정의
    - 데이터 수정 및 가공

```yaml
<filter secure.log>
  @type record_transformer
  remove_keys cap_effective,machine_id,boot_id,stream_id
  <record>
    tks.logType SYSCL
  </record>
</filter>
```

- Match 정의
    - 데이터 출력 대상 설정

```yaml
<match secure.log>
  @type forward
  <server>
    host log-collector.example.com
    port 24224
  </server>
</match>
```