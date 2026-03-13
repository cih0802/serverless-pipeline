# 🚀 Serverless Data Pipeline (AWS & Snowflake Native)

## 📝 Overview
본 프로젝트는 기존 레거시 환경(Airflow 기반)의 데이터 파이프라인을 **AWS 서버리스 아키텍처**와 **Snowflake 네이티브 환경**으로 전면 개편한 ELT(Extract, Load, Transform) 파이프라인입니다.

인프라 유지보수 비용을 최소화하고 운영 자동화를 달성하기 위해 Step Functions, Lambda, EventBridge 등 AWS의 관리형 서비스를 적극 도입하였으며, 데이터 변환 작업은 Snowflake 내부 기능으로 이관하여 비용 효율성과 안정성을 극대화했습니다.

## 🛠 Tech Stack
* **Orchestration & Trigger:** AWS Step Functions, Amazon EventBridge
* **Compute (Serverless):** AWS Lambda (arm64, Dockerized)
* **Data Storage & Warehouse:** Amazon S3 (Data Lake), Snowflake
* **Serving & API:** Neon (Serverless PostgreSQL), FastAPI (wrapped with Mangum)
* **CI/CD & Monitoring:** GitHub Actions, Amazon ECR, Slack API (Python `urllib`)

---

## 🔄 Data Flow Architecture

본 파이프라인은 매일 지정된 시간에 다음과 같은 생명주기(Trigger ➔ Extract ➔ Load ➔ Transform ➔ Serve)를 거쳐 동작합니다.

### 1. Trigger & Orchestration (Phase 0)
* **Amazon EventBridge:** 매일 정해진 시간에 파이프라인을 자동 트리거합니다.
* **AWS Step Functions:** 전체 파이프라인의 상태를 제어합니다. 병렬 수집(Parallel) 후 적재 단계로 넘어가는 흐름을 완벽히 제어하며, 상태 전환 시 `$$.Execution.Input` 컨텍스트 객체를 활용해 원본 입력 데이터(날짜 등)의 유실을 방지합니다.

### 2. Data Extraction (Phase 1)
* **Ingestion Lambda:** 공공 API를 호출하여 S3에 파티셔닝 적재합니다. 
* 멱등성 보장 및 수동 백필(Backfill) 지원을 위해 기존 Airflow의 `logical_date` 역할을 Lambda event 객체의 시간 값으로 대체하여 유연하게 설계되었습니다.

### 3. Data Load (Phase 2)
* **Snowflake Load Lambda:** S3에 적재된 데이터를 Snowflake로 `COPY INTO` 하는 경량화 함수입니다.
* 효율적인 쿼리 성능을 위해 기존 Partition Pruning 로직을 유지하며, 람다 구동 비용 최적화를 위해 테이블 DDL은 Snowflake 내부에서 사전 구성했습니다.

### 4. Data Transformation (Phase 3)
* **Snowflake View & Task:** 기존 dbt Cloud 무료 티어의 API 제약을 극복하고자 변환 로직을 Snowflake 네이티브 환경으로 100% 이관했습니다.
* 결측치 보간 및 증분 적재(Incremental)를 위한 복잡한 SQL을 `MERGE INTO` 구문과 의존성 체인(`AFTER`)을 갖춘 Task로 재설계했습니다.
* **Trigger Lambda:** 변환 Task를 실행하기 위해 단 1줄의 쿼리(`EXECUTE TASK`)만 호출하는 초경량 람다를 구동합니다.

### 5. Data Serving (Phase 4)
* **Serving DB & API:** 가공된 데이터는 서버리스 PostgreSQL인 **Neon**을 통해 최종 서비스됩니다.
* **FastAPI Server:** Mangum 라이브러리를 통해 FastAPI 애플리케이션을 래핑하여 AWS Lambda 환경에서 안정적으로 API를 제공합니다.

---

## ✨ Key Features & Optimizations

* **완전 자동화된 CI/CD 파이프라인**
  * GitHub Actions를 도입하여, 코드 푸시 시 arm64 아키텍처 기반의 Docker 이미지가 자동 빌드됩니다.
  * Amazon ECR 푸시부터 Lambda 함수 업데이트(Update Function Code)까지 원스톱으로 배포되도록 `.yml` 워크플로우를 구축했습니다. (ECR 생명주기: 최신 버전 유지)
* **비용(Cost) 최적화**
  * 항시 구동되는 Airflow 서버 등 레거시 인프라를 전면 철거했습니다.
  * 외부 트리거 및 무거운 연산을 최소화하고 데이터 웨어하우스(Snowflake)의 컴퓨팅 자원을 효율적으로 통제합니다.
* **내장 모듈을 활용한 경량 알림 시스템**
  * 외부 라이브러리 추가로 인한 용량 부담을 없애기 위해 파이썬 내장 모듈(`urllib`)만을 활용한 Slack 알림 람다를 구축했습니다.
  * Step Functions의 `Catch` 로직과 결합하여 파이프라인 내 어느 구간에서 장애가 발생하더라도 즉각적인 담당자 멘션과 로그 링크가 전송됩니다.
* **안정적인 에러 핸들링**
  * Snowflake 파이썬 커넥터 실행 결과를 명확히 로깅(`fetchall()` 활용)하여 트러블슈팅 시간을 대폭 단축했습니다.