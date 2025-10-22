# naver-flight-mcp

네이버 항공권 검색 API를 사용하여 최저가 항공권 정보를 조회하는 Model Context Protocol (MCP) 서버입니다.

## 기능

- 직항 항공권 최저가 검색 (성인 1명, 이코노미 클래스)
- 왕복 항공편 정보 조회
- 최저가 순으로 상위 10개 항공권 정보 제공
- 출발/도착 시간, 소요시간, 항공편명 등 상세 정보

## 설치 및 사용

### Cursor / Claude Desktop에서 사용

**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

#### 로컬 개발 시

```json
{
  "mcpServers": {
    "naver-flight-mcp": {
      "command": "node",
      "args": ["C:...{실제 루트경로}/naver-flight-mcp/dist/index.js"]
    }
  }
}
```

#### npm 패키지 배포 후

```json
{
  "mcpServers": {
    "naver-flight-mcp": {
      "command": "npx",
      "args": ["-y", "naver-flight-mcp"]
    }
  }
}
```

### 개발자용

```bash
# 의존성 설치
npm install

# 빌드
npm run build

# 로컬 테스트
npm link
```

## 사용 예시

### search_naver_flights 도구

```typescript
{
  departure: "PUS",      // 출발지 공항 코드 (예: PUS, ICN, GMP)
  arrival: "KIX",        // 도착지 공항 코드 (예: TYO, NRT, KIX)
  departureDate: "2025-12-02",  // 출발일 (YYYY-MM-DD)
  returnDate: "2025-12-09"      // 복귀일 (YYYY-MM-DD)
}
```

**출력 형식:**

| 순위 | 출발일   | 복귀일   | 가는편 | 오는편 | 총요금    | 가는편 출발 | 가는편 도착 | 소요시간 | 오는편 출발 | 오는편 도착 | 소요시간 |
| ---- | -------- | -------- | ------ | ------ | --------- | ----------- | ----------- | -------- | ----------- | ----------- | -------- |
| 1    | 20251202 | 20251209 | BX0126 | BX0123 | 153,000원 | 11:25       | 12:55       | 90분     | 11:00       | 13:00       | 120분    |

## 프로젝트 구조

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

## API 정보

- **엔드포인트**: `https://flight-api.naver.com/flight/international/searchFlights`
- **방식**: REST API (Server-Sent Events)
- **검색 조건**: 성인 1명, 직항만, 이코노미 클래스 (고정)

자세한 API 분석은 `NAVER_FLIGHT_API_ANALYSIS.md` 참고

## 테스트 결과

다양한 노선에 대한 테스트 결과는 `NAVER_FLIGHT_MCP_TEST_RESULTS.md` 참고

## 라이선스

MIT
