# naver-flight-mcp

네이버 항공권 검색 API를 사용하여 최저가 항공권 정보를 조회하는 Model Context Protocol (MCP) 서버입니다.

## ✨ 주요 기능

- **직항 항공권 최저가 검색** (성인 1명, 이코노미 클래스)
- **왕복 항공편 정보 조회** (출발/도착 시간, 소요시간, 항공편명)
- **최저가 순 상위 10개** 항공권 정보 제공
- **실시간 SSE 스트림 처리**로 완전한 데이터 수집
- **상세한 로그**로 검색 과정 추적

## 🚀 설치 및 설정

### 1. 프로젝트 클론 및 설치

```bash
# 프로젝트 클론
git clone https://github.com/your-username/naver-flight-mcp.git
cd naver-flight-mcp

# 의존성 설치
npm install

# TypeScript 빌드
npm run build
```

### 2. Cursor MCP 설정

**Windows**: `C:\Users\{사용자명}\.cursor\mcp.json`
**MacOS**: `~/.cursor/mcp.json`

#### 설정 파일 예시

```json
{
  "mcpServers": {
    "naver-flight": {
      "command": "node",
      "args": ["C:/Users/{사용자명}/naver-flight-mcp/dist/index.js"],
      "env": {}
    }
  }
}
```

#### 실제 경로 예시 (Windows)

```json
{
  "mcpServers": {
    "naver-flight": {
      "command": "node",
      "args": ["C:/Users/hwang/naver-flight-mcp/dist/index.js"],
      "env": {}
    }
  }
}
```

### 3. Cursor 재시작

MCP 설정을 추가한 후 Cursor를 재시작하면 네이버 항공권 검색 도구를 사용할 수 있습니다.

## 📖 사용 방법

### Cursor에서 사용

MCP 설정 후 Cursor에서 다음과 같이 사용할 수 있습니다:

```
네이버 항공권 검색: 부산(PUS) → 나리타(NRT), 2025-12-15 ~ 2025-12-19
```

### 검색 파라미터

```typescript
{
  departure: "PUS",           // 출발지 공항 코드
  arrival: "NRT",             // 도착지 공항 코드
  departureDate: "2025-12-15", // 출발일 (YYYY-MM-DD)
  returnDate: "2025-12-19"    // 복귀일 (YYYY-MM-DD)
}
```

### 출력 예시

```
항공권 검색 결과 (PUS → NRT):

순위: 1
출발일: 20251215
복귀일: 20251219
가는편: 7C1153
오는편: 7C1154
총요금: 278,700원
가는편 출발: 11:05
가는편 도착: 13:10
소요시간: 125분
오는편 출발: 14:05
오는편 도착: 16:45
소요시간: 160분
---
```

## 🧪 테스트 결과

### 2025년 12월 부산(PUS) - 나리타(NRT) 검색 결과

| 날짜                    | 최저가        | 항공편        | 상태    |
| ----------------------- | ------------- | ------------- | ------- |
| 2025-12-01 ~ 2025-12-05 | 304,000원     | 7C1153/7C1154 | ✅ 성공 |
| 2025-12-08 ~ 2025-12-12 | **277,000원** | 7C1153/7C1154 | ✅ 성공 |
| 2025-12-15 ~ 2025-12-19 | 278,700원     | 7C1153/7C1154 | ✅ 성공 |
| 2025-12-22 ~ 2025-12-26 | 416,400원     | 7C1153/7C1154 | ✅ 성공 |

### 인천(ICN) - 나리타(NRT) 검색 결과

| 날짜                    | 최저가    | 항공편        | 상태    |
| ----------------------- | --------- | ------------- | ------- |
| 2025-12-15 ~ 2025-12-19 | 312,600원 | BX0164/BX0163 | ✅ 성공 |

## 🔧 기술적 특징

### SSE 스트림 처리 개선

- **실시간 데이터 수집**: 네이버 API의 Server-Sent Events를 완전히 처리
- **점진적 데이터 증가**: 0개 → 16개 → 18개 → 20개 → 76개 → 77개
- **최종 유효 데이터 선택**: 가장 많은 데이터가 포함된 응답 사용
- **상세한 로그**: 각 단계별 데이터 수집 과정 추적

### 로그 예시

```
SSE 응답 처리 시작...
SSE 데이터 수신: 항공편 0개, 요금 0개
SSE 데이터 수신: 항공편 16개, 요금 32개
유효한 데이터 발견: 항공편 16개, 요금 32개
SSE 데이터 수신: 항공편 20개, 요금 100개
유효한 데이터 발견: 항공편 20개, 요금 100개
최종 데이터: 항공편 20개, 요금 100개
총 7009개의 요금 정보 발견
처리 완료 - 10개의 유효한 항공편
```

## 📁 프로젝트 구조

```
naver-flight-mcp/
├── src/
│   ├── tools/
│   │   └── NaverFlightSearch.ts  # 네이버 항공권 검색 도구
│   └── index.ts                   # MCP 서버 진입점
├── dist/                          # 빌드된 파일
├── NAVER_FLIGHT_API_ANALYSIS.md  # API 분석 문서
├── NAVER_FLIGHT_MCP_TEST_RESULTS.md  # 테스트 결과
├── package.json
├── tsconfig.json
└── README.md
```

## 🔌 API 정보

- **엔드포인트**: `https://flight-api.naver.com/flight/international/searchFlights`
- **방식**: REST API (Server-Sent Events)
- **검색 조건**: 성인 1명, 직항만, 이코노미 클래스 (고정)
- **응답 시간**: 일반적으로 4-5초 소요

## 🛠️ 개발자 정보

### 로컬 개발

```bash
# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 로그 확인
node dist/index.js
```

### 의존성

- **TypeScript**: 타입 안전성
- **node-fetch**: HTTP 요청 처리
- **zod**: 스키마 검증
- **@modelcontextprotocol/sdk**: MCP 서버 구현

## 📄 라이선스

MIT
