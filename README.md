# malro-data

공공데이터(AI Hub ‘소상공인 고객 주문 질의-응답’) 원천 CSV에서 kiosk AI 서비스용 **경량 아티팩트**를 생성하는 데이터 저장소입니다.

## 산출물
- menu.json: 데모 메뉴/옵션/가격 스키마(도메인: 카페 → 확장 가능)
- aliases.json: 별칭·약어·구어체 정규화 사전
- few_shots.jsonl: LLM 프롬프트용 소수 예시
- evalset.jsonl: 회귀 테스트용 고정 평가셋
- artifact_manifest.json: 버전/해시/생성 일시

## 빠른 시작
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 원천 CSV를 data/raw 에 배치 (train/validation)
# 예) data/raw/cafe_train.csv, data/raw/cafe_validation.csv

# 아티팩트 생성 (카페/음식점)
make artifacts DOMAIN=cafe
make artifacts DOMAIN=food
```

## 디렉터리
```
malro-data/
  configs/               # 규칙/스키마/메뉴 템플릿
  src/                   # ETL 스크립트
  data/                  # (gitignored) 원천/중간 산출
  outputs/               # 최종 아티팩트(경량 JSON/JSONL)
  docs/                  # 문서/플랜
```

## 라이선스/거버넌스
- AI Hub 원천 CSV는 저장소에 **커밋/배포 금지**입니다.
- `LICENSE_NOTICE.md`에 출처/이용약관 고지를 포함합니다.
- PII(전화/주소/이메일 등)는 정규식으로 **마스킹**합니다.

## 참고
- 상세 계획과 규칙은 `docs/PLAN.md`를 확인하세요.
