# malro-data: 공공데이터 기반 ETL & 아티팩트 생성

말로(Malro) 프로젝트의 **데이터 전용 저장소**입니다.

**AI Hub ‘소상공인 고객 주문 질의-응답’**(카페/음식점, `train`/`validation`) CSV 원천에서, 서비스에 필요한 **가벼운 아티팩트**를 생성합니다.

## 목표(Output)

- `menu.json` : 데모용 메뉴/옵션/가격 스키마(도메인: 카페 → 확장 가능)
- `aliases.json` : 별칭·약어·구어체 정규화 사전 (예: “아아”→“아이스 아메리카노”)
- `few_shots.jsonl` : LLM 프롬프트용 **소수 예시**(입력문 → 목표 JSON/ASK)
- `evalset.jsonl` : 프롬프트/모델 변경 시 회귀 테스트용 **고정 평가셋**
- `patterns.yml` : 주문성 문장 필터/정규식/의도 매핑 규칙
- `artifact_manifest.json` : 산출물 버전/해시/생성 일시

> 중요: AI Hub 원천 CSV는 저장소에 커밋/배포 금지 (라이선스).
> 
> 
> `outputs/` 이하의 **경량 아티팩트만** 앱 저장소(malro-app)에서 사용합니다.
> 

---

## 데이터 구조(원천 CSV)

다음 스키마를 가정합니다(열 이름은 데이터 기준):

| 항목 | 설명 | 타입 | 필수 |
| --- | --- | --- | --- |
| `IDX` | 파일 내 고유 순번 | number | Y |
| `발화자` | `c`(고객) / `s`(점원) | string | Y |
| `발화문` | 대화 텍스트 | string | Y |
| `카테고리` | 상점/도메인(카페/음식점 등) | string | Y |
| `QA번호` | 질의응답 묶음 ID | number | Y |
| `QA여부` | `q`(질문)/`a`(응답) | string | Y |
| `감성` | `m`/`n`/`p` | string | Y |
| `인텐트` | 질의 의도(질문 행 기준) | string | Y |
| `개체명` | NER 라벨(있으면 사용) | string | N |
| `상담번호` | 대화 세션 ID | number | Y |
| `상담내순번` | 세션 내 순번 | number | Y |

> 일부 파일에는 가격/수량/크기/상품명 등 추가 슬롯 유사 열이 포함될 수 있습니다. 있으면 적극 활용, 없으면 텍스트/인텐트로 추정합니다.
> 

---

## 처리 범위(What we do)

1. **조사(EDA)**
    - 도메인/발화자/인텐트/QA여부 분포, 중복/결측/이상치 확인
    - “주문성” 발화 정의 및 커버리지 추정
2. **주문성 문장 필터링(Extract)**
    - `발화자=c & QA여부=q`를 기본
    - `인텐트`에 **주문·추가·변경·취소·포장·수량·사이즈·옵션·메뉴** 등의 키워드/정규식 매칭
    - (선택) 키워드 기반 BM25/임베딩으로 보조 필터
3. **별칭/정규화 사전 생성(Transform-Aliases)**
    - 빈출 n-gram/표현을 수집 → **표준 슬롯 값으로 매핑**
    - 예) “아아/아이스아메/아이스 아메리카노” → `sku=AMERICANO_ICE`
        
        “연하게/샷 적게/진하게” → 옵션 규칙으로 정규화
        
4. **Few-shot 예시 생성(Transform-FewShots)**
    - 입력문 → 목표 **(a) 주문초안 JSON** 또는 **(b) ASK(부족 슬롯)**
    - 도메인/표현 다양성 균형 샘플링(중복/유사 중복 제거)
5. **평가셋 생성(Transform-Eval)**
    - `validation` 중심, `상담번호` 기반 **세션 누수 방지** 분할
    - 200~500개 규모 권장, 슬롯 정답(or 기대 동작) 라벨링
6. **산출물/버전 관리(Load)**
    - `outputs/<domain>/...`로 저장, 작은 JSONL/JSON
    - `artifact_manifest.json`에 버전/해시/카운트 기록

---

## 디렉터리 구조 제안

```
malro-data/
  README.md
  LICENSE_NOTICE.md              # AI Hub 출처/약관 고지 (원천 재배포 금지)
  pyproject.toml | requirements.txt
  .gitignore                     # data/**, *.csv 등 원천 무시
  Makefile

  configs/
    patterns.yml                 # 주문성 키워드/정규식, 인텐트 매핑
    menu.cafe.yml                # 데모 메뉴/옵션/가격(수기/샘플)
    slots.schema.json            # 표준 주문 슬롯 스키마(문서화)

  src/
    etl/
      00_eda_report.py           # 분포/통계 리포트 생성(.md/.html)
      01_filter_orders.py        # 주문성 발화 추출
      02_build_aliases.py        # 별칭/정규화 사전 생성
      03_build_fewshots.py       # few-shots 생성
      04_build_evalset.py        # 평가셋 생성
      05_validate_artifacts.py   # 산출물 스키마/일관성 검증
    utils/
      io.py, textnorm.py, sampling.py, eval.py

  data/                          # (gitignored)
    raw/                         # AI Hub CSV (train/validation)
      cafe_train.csv
      cafe_validation.csv
      food_train.csv
      food_validation.csv
    interim/                     # 중간 산출(파셜/캐시)

  outputs/
    cafe/
      menu.json
      aliases.json
      few_shots.jsonl
      evalset.jsonl
      artifact_manifest.json
    food/
      ...

```

---

## 작업 플로우 & 명령어

### 1) 환경

```bash
# 가상환경 & 패키지 설치
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

```

### 2) 원천 배치

- AI Hub CSV를 `data/raw/`에 수동 배치 (절대 커밋 금지)

### 3) 아티팩트 생성

```bash
# 카페 도메인 예시
make artifacts DOMAIN=cafe
# 음식점 도메인
make artifacts DOMAIN=food

```

`Makefile` 내부 동작:

```makefile
artifacts:
	python -m src.etl.00_eda_report --domain $(DOMAIN)
	python -m src.etl.01_filter_orders --domain $(DOMAIN)
	python -m src.etl.02_build_aliases --domain $(DOMAIN)
	python -m src.etl.03_build_fewshots --domain $(DOMAIN) --k 50
	python -m src.etl.04_build_evalset --domain $(DOMAIN) --n 300
	python -m src.etl.05_validate_artifacts --domain $(DOMAIN)

```

---

## 규칙/정책(핵심 디테일)

### A) “주문성” 정의(초안)

- 기본 필터: `발화자 == "c" AND QA여부 == "q"`
- `인텐트` 또는 `발화문` 내 키워드(예시):
    - `주문|추가|빼|변경|포장|드시고|테이크아웃|사이즈|샷|시럽|뜨거운|차가운|아이스|핫|수량|개|잔|세트|메뉴|옵션`
- (선택) `patterns.yml`로 관리, 도메인별 예외/가중치 지정

### B) 별칭/정규화

- 토큰/문자 정규화 → 빈출 n-gram 상위 **표준 슬롯** 매핑
- 예:
    - 사이즈: `톨|레귤러|미디움 → M`, `라지|벤티 → L`
    - 온도: `아아 → ICE`, `뜨아 → HOT`
    - 진하기/얼음: `연하게 → ice:more|shot:-1`(정책에 맞게 정의)
- 모든 규칙은 `aliases.json`에 **양방향(표준↔자유표현) 주석**과 함께 명시

### C) Few-shot 생성 가이드

- 입력 다양성 확보: 길이/옵션 종류/표현 스타일(약어/구어/오탈자) 균형
- 목표 라벨:
    - **ORDER_DRAFT**: 표준 주문 JSON(미확정 슬롯은 `null` 또는 제외)
    - **ASK**: “부족 슬롯” 식별과 **짧은 질문 문구**
- 중복/유사도 제거: 유사도(코사인/BM25) 기준 상위 중복 제거

### D) 평가셋 생성/관리

- `validation` 위주 + `상담번호` 단위로 **학습/평가 분리**
- 200~500개, **슬롯 정답**(sku/size/temp/qty/ice/shot/syrup/type/special_request) 주석
- **고정(seed, list)**: 프롬프트/모델 교체 시 동일 셋 재사용

### E) 산출물 검증

- `slots.schema.json`로 스키마 검사(Pydantic/JSONSchema)
- `aliases` 키 충돌/순환 매핑 금지
- `few_shots`/`evalset` 텍스트 중복률, 도메인 편향 경고

### F) 라이선스/거버넌스

- `LICENSE_NOTICE.md`에 **AI Hub 출처/이용약관** 명시
- 원천 CSV는 **비공개·비배포**, 산출물만 공개
- PII 검증: 전화/주소/이메일 패턴 **마스킹**(정규식 필터)

### G) 버전/추적

- `artifact_manifest.json`
    
    ```json
    {
      "domain": "cafe",
      "version": "0.2.0",
      "generated_at": "2025-10-25T12:00:00+09:00",
      "counts": {"aliases": 120, "few_shots": 50, "evalset": 300},
      "source_hash": "sha256:...",
      "patterns_version": "2025-10-20"
    }
    
    ```
    

---

## 산출 예시(샘플)

**aliases.json**

```json
{
  "아아": {"sku": "AMERICANO", "temp": "ICE"},
  "뜨아": {"sku": "AMERICANO", "temp": "HOT"},
  "연하게": {"ice": "more"},
  "톨": {"size": "M"},
  "라지": {"size": "L"}
}

```

**few_shots.jsonl**

```json
{"input": "아아 라지 두 잔 포장", "label": "ORDER_DRAFT",
 "target": {"order":{"type":"TAKE_OUT","items":[{"sku":"AMERICANO","quantity":2,"options":{"temp":"ICE","size":"L"}}]}}}

{"input": "라떼 하나요", "label": "ASK",
 "missing_slots": ["temp","size"],
 "question": "라떼를 핫으로 드릴까요, 아이스로 드릴까요? 사이즈는 S/M/L 중 선택해주세요."}

```

**evalset.jsonl**

```json
{"input":"바닐라 라떼 톨로 두 잔, 샷 하나 추가",
 "gold":{"order":{"items":[{"sku":"VANILLA_LATTE","quantity":2,"options":{"size":"M","shot":1}}],"type":"TAKE_OUT"}}}

```

---

## 요구 스택

- Python 3.10+
- pandas, numpy, pydantic, regex, rapidfuzz, scikit-learn(선택), rank-bm25(선택), jinja2(리포트)
- pre-commit(black, isort, flake8)

---

## 향후 로드맵

- (옵션) 임베딩 기반 별칭/유사 SKU 추천기
- (옵션) 다도메인 지원: 패스트푸드/영화관 등
- (옵션) 데이터 카드 자동 생성(EDA → `reports/eda_{domain}.md`)

---

## 앱 연동(malro-app)

- `ARTIFACTS_DIR`에 `menu.json / aliases.json / few_shots.jsonl / evalset.jsonl` 배치
- 서버 기동 시 `artifact_manifest.json` 버전 로깅 → 프롬프트 캐시 키에 포함

---

### 체크리스트

- [ ]  원천 CSV `data/raw/` 배치 (gitignore 확인)
- [ ]  `patterns.yml` 도메인 키워드/정규식 작성
- [ ]  `menu.cafe.yml` 데모 SKU/옵션 정의
- [ ]  `make artifacts DOMAIN=cafe` 실행 → `outputs/cafe/*` 확인
- [ ]  `artifact_manifest.json` 생성/버전 기록
- [ ]  `README.md`에 사용법/주의사항 갱신