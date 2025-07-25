# CronJob

> CronJob은 네임스페이스에 서비스중인 CronJob 목록과 생성, 삭제, 수정하는 서비스 입니다.

---
## **목차**
1. [CronJob 조회](#cronjob-조회)
   - [1.1. CronJob 목록](#cronjob-목록)
   - [1.2. CronJob 상세정보](#cronjob-상세정보)
   - [1.3. CronJob Metric](#cronjob-metric)
   - [1.4. CronJob Pod](#cronjob-pod)
   - [1.5. CronJob event](#cronjob-event)
2. [CronJob 생성](#cronjob-생성)
3. [CronJob 삭제](#cronjob-삭제)
4. [CronJob 수정](#cronjob-수정)

## CronJob 조회

---
### CronJob 목록

![img.png](./img/cronjob_list.png)

메뉴 진입시 상위 선택된 클러스터/네임스페이스 내 CronJob 목록이 조회됩니다.
* Name, Schedule, Suspend 등 확인할 수 있습니다.

### CronJob 상세정보

![img.png](./img/cronjob_detail.png)

선택한 CronJob의 상세정보를 표시합니다.
생성날짜, Name, namespace를 확인할 수 있습니다.

### CronJob 상세정보-Namespace

![img.png](./img/cronjob_detail_namespace.png)

상세정보에서 namespace를 클릭하면 namespace 정보가 표시됩니다.


---
### CronJob Metric
* CronJob의 metric 정보를 확인할 수 있습니다.

---
### CronJob Pod

![img.png](./img/cronjob_pod.png)

CronJob으로 배포된 pod 목록을 표시합니다.
Name, Node, Status 등을 확인할 수 있습니다.

---
### CronJob event

![img.png](./img/cronjob_event.png)

CronJob에 발생한 이벤트 목록을 표시합니다.

---
## CronJob 생성

![img.png](./img/cronjob_create.png)

생성 버튼 클릭 시, CronJob 생성 template이 포함된 팝업 호출됩니다. 

${} 로 표기된 곳에 사용자가 입력 후(필요시 추가 데이터 입력), 확인 버튼 클릭하면 CronJob이 생성됩니다.

* 생성 예시

![img.png](./img/cronjob_create_ex.png)

metadata > namespace에 입력한 namespace에 CronJob 생성됩니다.
* <strong>상단 헤더에 선택된 클러스터 내에 존재하는</strong> namespace 입력

ex)
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
   name:  develop-cronjob1
   namespace: develop
spec:
   schedule: "*/1 * * * *"
   jobTemplate:
      spec:
         template:
            spec:
               containers:
                  - name: hello
                    image: 10.120.105.228/docker/library/nginx
                    resources:
                       requests:
                          cpu: "100m"
                          memory: "64Mi"
                          ephemeral-storage: "256Mi"
                       limits:
                          cpu: "100m"
                          memory: "64Mi"
                          ephemeral-storage: "256Mi"
               restartPolicy: OnFailure
```
---
## CronJob 수정

![img.png](./img/cronjob_modify.png)

수정하고자하는 CronJob 선택 후, 수정 버튼 클릭하면 해당 CronJob의 yaml 데이터를 팝업으로 호출합니다.

수정하고자하는 값을 수정 후, 확인 버튼 클릭하면 수정됩니다.


---
## CronJob 삭제

![img.png](./img/cronjob_delete.png)

삭제하고자하는 CronJob 선택 후, 삭제 버튼 클릭하면 해당 CronJob은 삭제됩니다.


