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

1) `configs/menu.cafe.yml`: 메뉴와 동의어 정의(매칭 정확도 핵심)
```
version: "0.2.0"
sku:
  AMERICANO:
    display: "아메리카노"
    synonyms: ["아이스 아메리카노", "아아", "뜨아", "아메리카노"]
    options:
      size: [S, M, L]
      temp: [ICE, HOT]
  LATTE:
    display: "카페라떼"
    synonyms: ["라떼", "카페라떼", "카페 라떼", "아이스 라떼", "뜨거운 라떼"]
    options:
      size: [S, M, L]
      temp: [ICE, HOT]
  VANILLA_LATTE:
    display: "바닐라 라떼"
    synonyms: ["바닐라라떼", "아이스 바닐라라떼"]
    options:
      size: [S, M, L]
      temp: [ICE, HOT]
```
- 동의어 배열에 실제 점포 표현/오탈자/구어체를 추가할수록 SKU 매칭률이 향상됩니다.
- 메뉴가 늘어나면 `sku:` 아래에 계속 추가하세요.

2) `configs/patterns.yml`: 주문성 키워드/정규식 게이트
```
intents:
  order:
    include_regex:
      - "주문|주세요|추가|빼|변경|포장|테이크아웃|예약|사이즈|샷|시럽|뜨거운|차가운|아이스|핫|수량|개|잔|세트|메뉴|옵션"
```
- few_shots 생성 시, 메뉴 언급 + 위 정규식 중 하나라도 매칭되어야 ORDER_DRAFT로 채택됩니다.

3) 스키마 파일(검증용)
- `configs/slots.schema.json`: 주문 JSON 스키마
- `configs/aliases.schema.json`, `configs/few_shots.schema.json`, `configs/evalset.schema.json`, `configs/artifact_manifest.schema.json`
- ETL 마지막 단계에서 `jsonschema`로 모든 산출물을 검증합니다.

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
