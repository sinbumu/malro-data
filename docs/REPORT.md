# malro-data REPORT: 방법론 & 현재 상태

## 목표
- AI Hub ‘소상공인 고객 주문 질의-응답’ 원천에서 kiosk AI용 경량 아티팩트 생성
- 산출물: `aliases.json`, `few_shots.jsonl`, `evalset.jsonl`, `artifact_manifest.json`
- 제약: 원천 CSV 비배포, 산출물 스키마 준수(jsonschema 검증)

## 파이프라인 개요
1) Filter(01)
   - 로드: `data/raw/{domain}_*.csv`
   - 규칙: 발화자=c AND QA=q
   - 키워드 게이트: `configs/patterns.yml:intents.order.include_regex`
   - 출력: `data/interim/{domain}_orders.csv`

2) Export Menu(02a)
   - `configs/menu.{domain}.yml` → 런타임 친화 `outputs/{domain}/menu.json`
   - SKU/표시명/가능 온도/사이즈/허용 옵션만 포함(가격 포함 가능)

2) Aliases(02b)
   - `configs/aliases.{domain}.yml` → 정규화 후 `outputs/{domain}/aliases.json`
   - shot 문자열→정수, size XL→L, ice 대문자→스키마 소문자 매핑

3) Few-shots(03)
   - 메뉴 매핑: `configs/menu.{domain}.yml`(정식 SKU/옵션) + `configs/aliases.{domain}.yml`(별칭/암시 옵션) 동시 로드
   - 주문 게이트: (a) 메뉴 언급 존재, (b) 주문 동사 정규식 매칭 → 만족할 때만 샘플 생성
   - 멀티 아이템: 쉼표/접속사(그리고/와/랑/및)로 분할 후 각 세그먼트에서 SKU/수량/옵션 추출
   - 수량 파싱: 숫자/한글수(예: 다섯 개, 10잔)
   - 옵션 파싱: ICE/HOT, S/M/L(톨/라지/벤티 매핑) + 별칭의 암시 옵션 병합(명시값 우선)
   - 라벨 정책: SKU 확실 → ORDER_DRAFT, 불확실 → ASK(기본 파이프라인에선 제외)
   - 출력: `outputs/{domain}/few_shots.jsonl`

4) Evalset(04)
   - Few-shots와 동일한 파싱/매핑 로직(메뉴+별칭, 암시 옵션 병합)으로 확실한 케이스만 gold 생성
   - 멀티 아이템 포함, 상한 N 유지
   - 출력: `outputs/{domain}/evalset.jsonl`

5) Validate(05)
   - `jsonschema`로 모든 산출물 검증
   - `artifact_manifest.json` 기록: domain/version/generated_at/counts/source_hash/patterns_version

## 스키마/계약
- `configs/menu.{domain}.yml`: 정식 SKU/옵션/가격(선택) 정의(운영 원본) → `menu.json`
- `configs/aliases.{domain}.yml`: 별칭/동의어 → { sku?, options? } (옵션 단독 별칭 허용)
- `configs/patterns.yml`: 주문성 게이트 정규식(include/exclude)
- `configs/slots.schema.json`: 주문 JSON 스키마(앱과 공유)
- `configs/*schema.json`: aliases/few_shots/evalset/manifest 검증 스키마

### 사전점검(Preflight) 규칙
- 슬롯 enum 통일: `slots.schema.json`을 기준으로 `size(S/M/L)`, `temp(ICE/HOT)`, `ice(less|normal|more)` 표기 강제(검증 실패 시 중단)
- 메뉴-옵션 허용: `menu.json`의 `allow_options` + `sizes_enabled`/`temps`와 불일치하는 옵션 사용 시 실패
- 별칭 충돌/중복: `aliases.{domain}.yml` 내 동일 term이 다수 SKU에 매핑될 경우 경고 로그(비치명). 앱 단계에서 ASK 유도 권장

## 현재 품질 & 한계
- 장점
  - 메뉴 동의어 기반 매칭 + 주문 게이트로 비주문성/잡음 상당 부분 제거
  - 멀티 아이템/수량/온도/사이즈 기본 추출 지원
  - 스키마 검증으로 일관성 보장
- 한계(로드맵)
  - 메뉴 커버리지: 동의어/오탈자 확장 필요(점포별 상이)
  - 문맥 전파: “전부 아이스로/두 잔 모두 톨” 같은 범위 지시 처리 미흡
  - 의도 세분화: 수정/취소/세트/가용성 문의는 분리 라벨 고려 필요
  - 옵션 다양성: 샷/시럽/얼음/우유 타입 등 확장
  - 평가셋 커버리지: 희소 조합/어려운 케이스 보강 필요

## 성능/재현성
- 대용량 CSV 처리: pandas dtype 지정, 중간 산출 캐시(`data/interim`)
- 결정성: 샘플링 seed 고정, 파일 해시를 manifest에 기록

## 보안/거버넌스
- 원천 CSV 비공개, 산출물만 공개
- PII 정규식 마스킹(전화/이메일/주소 등) 권장

## 운영 팁
- 메뉴 동의어를 꾸준히 확장하면 매칭률과 few-shots/평가셋 품질이 향상됩니다.
- Few-shots는 기본 ORDER_DRAFT만 생성하도록 구성되어 있으며, 필요 시 ASK를 옵션으로 포함하세요.
- 앱은 `slots.schema.json`을 타입 소스로 사용하여 DTO/검증을 일치시키세요.

