# malro-data

공공데이터(AI Hub ‘소상공인 고객 주문 질의-응답’) 원천 CSV에서 kiosk AI 서비스용 **경량 아티팩트**를 생성하는 데이터 저장소입니다.

## 산출물(Outputs)
- `aliases.json`: 별칭·약어·구어체 정규화 사전
- `few_shots.jsonl`: LLM 프롬프트용 소수 예시(ORDER_DRAFT 중심)
- `evalset.jsonl`: 회귀 테스트용 고정 평가셋
- `artifact_manifest.json`: 버전/해시/생성 일시

## 빠른 시작
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 원천 CSV를 data/raw 에 배치 (train/validation)
# 예) data/raw/cafe_train.csv, data/raw/cafe_validation.csv

# 아티팩트 생성 (카페/음식점)
make artifacts DOMAIN=cafe
# make artifacts DOMAIN=food
```

### 실행 시 생성물
- `data/interim/{domain}_orders.csv`: 주문성 발화 필터 결과
- `outputs/{domain}/aliases.json`
- `outputs/{domain}/few_shots.jsonl`
- `outputs/{domain}/evalset.jsonl`
- `outputs/{domain}/artifact_manifest.json`

## 디렉터리
```
malro-data/
  configs/               # 규칙/스키마/메뉴 템플릿
  src/                   # ETL 스크립트
  data/                  # (gitignored) 원천/중간 산출
  outputs/               # 최종 아티팩트(경량 JSON/JSONL)
  docs/                  # 문서/플랜
```

## 설정(configs) 가이드(MVP 필수)

아래 3개 파일만 준비하면 됩니다. 외부에서 가게 메뉴셋을 정의(1) → 별칭 정의(2) → 본 저장소 `configs/`에 넣고 생성(3).

### 1) 메뉴 정의: `configs/menu.{domain}.yml`
- 역할: 정식 SKU/옵션/가격(선택) 정의. 운영 출처.
- 최소 필드
```
version: "0.2.0"
currency: "KRW"           # 선택
sku:
  AMERICANO:
    display: "아메리카노"
    category: "COFFEE"   # 선택
    price:                # 선택(앱/리포트용)
      base: 3000
      by_size: { S: 0, M: 500, L: 1000 }
    options:
      size: [S, M, L]
      temp: [ICE, HOT]
  LATTE:
    display: "카페라떼"
    options: { size: [S, M, L], temp: [ICE, HOT] }
  VANILLA_LATTE:
    display: "바닐라 라떼"
    options: { size: [S, M, L], temp: [ICE, HOT] }
```
- 비고: `synonyms`는 운영에선 비우는 것을 권장(별칭은 아래 파일에서 관리).

### 2) 별칭/동의어: `configs/aliases.{domain}.yml`
- 역할: 자유표현 → SKU 및 암시 옵션 매핑(옵션 단독 별칭 허용).
```
version: "0.1.0"
aliases:
  "아아": { sku: AMERICANO, options: { temp: ICE } }
  "뜨아": { sku: AMERICANO, options: { temp: HOT } }
  "바닐라라떼": { sku: VANILLA_LATTE }
  # 옵션 단독 별칭(메뉴 없이 옵션만 암시)
  "톨": { options: { size: M } }
  "라지": { options: { size: L } }
  "벤티": { options: { size: L } }
```
- 동작: few-shots/evalset 생성 시, 세그먼트에 별칭이 등장하면 해당 SKU/옵션을 암시값으로 병합(사용자 명시값이 우선).

### 3) 주문 게이트: `configs/patterns.yml`
- 역할: 주문성 문장 판별 키워드/정규식.
```
intents:
  order:
    include_regex:
      - "주문|주세요|추가|빼|변경|포장|테이크아웃|예약|사이즈|샷|시럽|뜨거운|차가운|아이스|핫|수량|개|잔|세트|메뉴|옵션"
    exclude_regex: []    # 선택(취소/환불 등 제외 규칙)
```
- few_shots는 “메뉴 언급 + include_regex 매칭”을 동시에 만족해야 ORDER_DRAFT로 채택.

### 4) 산출물 검증 스키마(참고)
- `configs/slots.schema.json`, `configs/aliases.schema.json`, `configs/few_shots.schema.json`, `configs/evalset.schema.json`, `configs/artifact_manifest.schema.json`
- ETL 마지막 단계에서 `jsonschema`로 모든 산출물을 검증합니다.

### 외부 준비 → 생성 절차
1. 가게 메뉴셋 작성: `menu.{domain}.yml`(정식 SKU/옵션/가격)
2. 별칭 작성: `aliases.{domain}.yml`(동의어/약칭/오탈자, 암시 옵션 포함)
3. 두 파일을 본 저장소 `configs/`에 놓고 실행:
```
make artifacts DOMAIN=cafe
```
4. 산출물 확인: `outputs/{domain}/*`를 앱에서 사용

### 도메인 확장 규칙
- `{domain}` 이름만 바꿔 동일 규격으로 파일을 추가하면 됩니다(예: `menu.food.yml`, `aliases.food.yml`).
- Make 실행 시 `DOMAIN=food`로 지정.

## 파이프라인 개요
- 01 Filter: `data/raw/{domain}_*.csv` 로드 → 발화자=c, QA=q + 정규식 기반 주문성 필터 → `interim`
- 02 Aliases: 빈도+룰 기반 별칭 생성(초안) → `aliases.json`
- 03 Few-shots: 메뉴 동의어 매핑 + 주문 동사 게이트 → 멀티 아이템/수량/옵션 파싱 → `few_shots.jsonl`
- 04 Evalset: 확실한 매칭만 골라 멀티 아이템 gold 생성 → `evalset.jsonl`
- 05 Validate: jsonschema 검증 + `artifact_manifest.json` 기록

### Few-shots 옵션
- 기본: ORDER_DRAFT만 생성하도록 Makefile에 `--only_order_draft` 적용
- ASK 샘플도 포함하고 싶다면 직접 실행:
```
python -m src.etl.03_build_fewshots --domain cafe --k 120 --max_ask_ratio 0.3
```

## 앱 연동 팁
- `outputs/{domain}/*`를 앱의 아티팩트 디렉터리에 배치하세요.
- 주문 객체 타입은 `configs/slots.schema.json`을 기준으로 생성(TypeScript typegen 등 권장).
- 프롬프트 템플릿에 `few_shots.jsonl`의 ORDER_DRAFT 예시를 삽입해 모델 초기 성능을 확보합니다.

## 라이선스/거버넌스
- AI Hub 원천 CSV는 저장소에 **커밋/배포 금지**입니다.
- `LICENSE_NOTICE.md`에 출처/이용약관 고지를 포함합니다.
- PII(전화/주소/이메일 등)는 정규식으로 **마스킹**합니다.

## 참고
- 상세 계획과 규칙은 `docs/PLAN.md`를 확인하세요.
 - 구현 방법론과 현재 한계/개선안은 `docs/REPORT.md`를 확인하세요.
