# APP Advice (MVP 서버 연동 가이드)

본 문서는 이 저장소가 생성한 outputs를 이용해 MVP 풀스택 서버에서 LLM 호출을 구성하는 실전 권장안을 요약합니다.

## 무엇을 서버에 배포하나
- 필수: `outputs/{domain}/menu.json`, `outputs/{domain}/aliases.json`, `outputs/{domain}/artifact_manifest.json`
- 선택(품질/테스트): `outputs/{domain}/few_shots.jsonl`, `outputs/{domain}/evalset.jsonl`
- 주의: `configs/*.yml`은 빌드 전용. 서버는 JSON 아티팩트만 참조 권장

## 요청 파이프라인(요약)
1) 전처리: STT 텍스트 정규화 → 키워드/퍼지/임베딩으로 후보 SKU/별칭 Top-K 추출 → 별칭의 암시 옵션을 사용자 명시 옵션과 병합(명시 우선)
2) 컨텍스트 슬라이싱: 메뉴 후보(10~20), 별칭 후보(10~30), few-shots(5~10), 세션 요약(1~2문장)
3) LLM 호출: 시스템 프롬프트(역할/스키마 요약/정책/`artifact_manifest` 버전) + 위 슬라이스 + 사용자 입력
4) 사후 처리: JSON Schema 검증 → 부족 슬롯 ASK(짧은 질문) → 완성 시 제출

## 컨텍스트 구성 예시
```text
[System]
카페 주문문을 표준 JSON으로 추출. enum: size(S/M/L), temp(ICE/HOT), ice(less/normal/more), shot(>=0 int).
출력: {"order":{"items":[{sku, quantity, options?}], "type?": "DINE_IN|TAKE_OUT"}}
artifacts: domain=cafe, version=0.1.0, source={sha256:...}
규칙: 확인 불가 슬롯 생략, 모호하면 ASK(한 문장)

[Few-shots] (ORDER_DRAFT 예시 5~10)
[Menu] AMERICANO(temps HOT/ICE, sizes S/M/L, allow shot,decaf,syrup,ice), CAFE_LATTE(...)
[Aliases] 아아→{sku:AMERICANO,temp:ICE}, 뜨아→{sku:AMERICANO,temp:HOT}, 라지→{size:L} ...
[User] "아이스 아메리카노 라지 두 잔 포장"
[Assistant] (위 스키마 JSON만 출력)
```

## 서버 구현 팁
- 토큰 예산: 1.2k~2.5k tokens 목표(가격/설명/카테고리 제거)
- 캐싱: 정적 시스템 프롬프트는 `artifact_manifest` 해시로 캐시(공급자 프롬프트 캐시/스레드ID 지원 시 활용)
- 세션 메모리: 대화 전체 대신 요약 1~2문장 유지
- 동적 선택(RAG): 메뉴 후보(키워드+퍼지/임베딩 Top-20), 별칭 후보(직접 매칭+근접 Top-30), few-shots(유사도 기반 Top-8)
- 구조화 출력: JSON 모드/함수 호출/스키마 제약 활용 → 파싱 실패 최소화
- 검증 루프: jsonschema 실패 시 자동 보정 또는 ASK 반환

## 의사 코드(Typescript)
```ts
const artifacts = loadArtifacts(domain); // menu.json, aliases.json, few_shots.jsonl, manifest
export async function inferOrder(userText: string, session: Session) {
  const { menu, aliases, fewShots, manifest } = artifacts;
  const slice = buildContextSlice(userText, menu, aliases);
  const sys = buildSystemPrompt(manifest);
  const shots = pickFewShots(userText, fewShots, 8);
  const messages = composeMessages(sys, shots, slice, userText, session.summary);
  const resp = await openai.chat.completions.create({
    model: "gpt-5",
    messages,
    response_format: { type: "json_object" }
  });
  const json = safeParse(resp.choices[0].message.content);
  const valid = validateWithSchema(json, slotsSchema);
  if (!valid.ok) return makeASK(valid.missing);
  return json;
}
```

## 품질/운영
- 회귀: `evalset.jsonl`로 간단 정확도 체크(슬롯 기준)
- 피드백 루프: 실패 로그 → `aliases.{domain}.yml` 보강 → 재생성
- few-shots: 5~15개 유지, 표현/옵션 다양성, 중복/모순 금지
- 거버넌스: PII 마스킹, 원천 CSV 비배포, manifest 버전/해시 로깅

## FAQ
- few-shots를 “미리 주입”해 상주시킬 수 있나? → 미세튜닝이 아닌 이상 불가(컨텍스트/캐시 재사용만 가능)
- 메뉴/별칭을 전부 넣어도 되나? → 비권장. 항상 질의 기반 슬라이스(Top-K)만
