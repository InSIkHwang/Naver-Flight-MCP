# 네이버 항공권 API 분석 보고서

## 개요

네이버 항공권 검색 시스템은 **REST API**를 사용하여 항공권 정보를 가져옵니다. GraphQL이 아닌 **Server-Sent Events (SSE) 방식**의 일반 REST API입니다.

## API 엔드포인트

### 항공권 검색 API

- **URL**: `https://flight-api.naver.com/flight/international/searchFlights`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Accept**: `text/event-stream` (SSE 방식)
- **응답 상태**: `201 Created`

## 요청 페이로드 구조

```json
{
  "adultCount": 1,
  "childCount": 0,
  "infantCount": 0,
  "device": "pc",
  "isNonstop": true,
  "itineraries": [
    {
      "departureLocationCode": "PUS",
      "departureLocationType": "airport",
      "arrivalLocationCode": "TYO",
      "arrivalLocationType": "airport",
      "departureDate": "20251202"
    },
    {
      "departureLocationCode": "TYO",
      "departureLocationType": "airport",
      "arrivalLocationCode": "PUS",
      "arrivalLocationType": "airport",
      "departureDate": "20251209"
    }
  ],
  "openReturnDays": 0,
  "seatClass": "Y",
  "tripType": "RT",
  "flightFilter": {
    "filter": {
      "airlines": [],
      "departureAirports": [["PUS"], []],
      "arrivalAirports": [[], ["PUS"]],
      "departureTime": [],
      "fareTypes": [],
      "flightDurationSeconds": [],
      "hasCardBenefit": true,
      "isIndividual": false,
      "isLowCarbonEmission": false,
      "isSameAirlines": false,
      "isSameDepArrAirport": true,
      "isTravelClub": false,
      "minFare": {},
      "viaCount": [],
      "selectedItineraries": []
    },
    "limit": 200,
    "skip": 0,
    "sort": {
      "adultMinFare": 1
    }
  },
  "initialRequest": true
}
```

### 주요 파라미터 설명

| 파라미터                              | 설명         | 예시 값                 |
| ------------------------------------- | ------------ | ----------------------- |
| `adultCount`                          | 성인 인원 수 | `1`                     |
| `childCount`                          | 아동 인원 수 | `0`                     |
| `infantCount`                         | 유아 인원 수 | `0`                     |
| `isNonstop`                           | 직항 여부    | `true` (직항만)         |
| `seatClass`                           | 좌석 등급    | `"Y"` (이코노미)        |
| `tripType`                            | 여행 유형    | `"RT"` (왕복)           |
| `itineraries[].departureLocationCode` | 출발지 코드  | `"PUS"` (부산)          |
| `itineraries[].arrivalLocationCode`   | 도착지 코드  | `"TYO"` (도쿄)          |
| `itineraries[].departureDate`         | 출발일       | `"20251202"` (YYYYMMDD) |

### 좌석 등급 코드

- `Y`: 이코노미 (Economy)
- `C`: 비즈니스 (Business)
- `F`: 일등석 (First Class)

### 여행 유형 코드

- `RT`: Round Trip (왕복)
- `OW`: One Way (편도)

## 응답 데이터 구조

응답은 **Server-Sent Events (SSE)** 형식으로 전달됩니다.

```
data: {JSON_DATA}
```

### 응답 JSON 구조

```json
{
  "uniqueId": "40ed2dc0-2e82-416f-948e-03cad42bd985",
  "status": {
    "searchKey": "RTY100PY020251202PUSATYOA20251209TYOAPUSA",
    "__v": 16,
    "requestedPartnerCount": 20,
    "completedPartnerCount": 20,
    "isCompleted": true,
    "airlinesCodeMap": { ... },
    "itineraryAirports": [ ... ],
    "airportsCodeMap": { ... },
    "fareTypesCodeMap": { ... },
    "durationSecondsRanges": [ ... ],
    "lowestFare": {
      "direct": 223500,
      "a01": 230200
    },
    "priceRange": {
      "min": 223500,
      "max": 1252400
    },
    "expireAt": "2025-10-22T01:50:56.373Z",
    "hasCarbonEmission": true
  },
  "itineraries": [ ... ],
  "fareMappings": [ ... ],
  "isExpired": false,
  "popularFlights": [ ... ]
}
```

### 주요 데이터 필드

#### 1. `status` - 검색 상태 정보

```json
{
  "searchKey": "검색 고유 키",
  "isCompleted": true,
  "lowestFare": {
    "direct": 223500,
    "a01": 230200
  },
  "priceRange": {
    "min": 223500,
    "max": 1252400
  }
}
```

#### 2. `itineraries` - 항공편 정보 배열

각 항공편(leg)의 상세 정보를 포함합니다.

```json
{
  "itineraryId": "20251202PUSNRT7C1151",
  "duration": 7500,
  "sequence": 1,
  "segments": [
    {
      "departure": {
        "airportCode": "PUS",
        "date": "20251202",
        "time": "0720",
        "terminal": "I"
      },
      "arrival": {
        "airportCode": "NRT",
        "date": "20251202",
        "time": "0925",
        "terminal": "3"
      },
      "marketingCarrier": {
        "airlineCode": "7C",
        "flightNumber": "1151"
      },
      "operatingCarrier": {
        "airlineCode": "7C",
        "flightNumber": "1151"
      },
      "flightDuration": 7500,
      "groundDuration": 0,
      "aircraftCode": "738"
    }
  ],
  "carbonEmission": -1
}
```

**필드 설명:**

- `itineraryId`: 항공편 고유 ID (형식: `YYYYMMDD출발공항도착공항항공사편명`)
- `duration`: 총 비행 시간 (초 단위)
- `sequence`: 1 = 가는 편, 2 = 오는 편
- `segments`: 구간별 상세 정보 (경유가 있으면 여러 개)
- `time`: HHMM 형식 (예: "0720" = 07시 20분)
- `flightDuration`: 실제 비행 시간 (초)
- `groundDuration`: 지상 대기 시간 (초)

#### 3. `fareMappings` - 가격 정보 배열

항공편 조합과 각 OTA(온라인 여행사)별 가격 정보를 포함합니다.

```json
{
  "itineraryIds": "20251202PUSNRT7C1151-20251209NRTPUS7C1152",
  "fares": [
    {
      "partnerCode": "TBK033",
      "fareType": "A01/B16",
      "adult": {
        "totalFare": 223500,
        "qCharge": 0,
        "tax": 55000
      },
      "isConfirmed": true,
      "baggageFeeType": "FREE"
    }
  ],
  "carbonEmission": -3,
  "curation": ["MIN_PRICE", "NONSTOP_MIN_PRICE"]
}
```

**필드 설명:**

- `itineraryIds`: 가는편-오는편 항공편 ID 조합 (`-`로 연결)
- `fares`: 해당 조합에 대한 판매 파트너별 요금 정보
- `partnerCode`: OTA 파트너 코드
- `fareType`: 요금 유형 (카드 할인 등)
- `totalFare`: 총 요금 (원 단위)
- `qCharge`: Q-Charge (유류할증료 등)
- `tax`: 세금
- `baggageFeeType`: 수하물 정책 (`FREE`, `PAID` 등)

## 실제 검색 결과 예시

### 최저가 TOP 10 항공권 (PUS-TYO, 2025.12.02~12.09)

| 순위 | 출발일   | 복귀일   | 가는편 | 오는편 | 총요금    | 가는편 출발 | 가는편 도착 | 가는편 소요시간 | 오는편 출발 | 오는편 도착 | 오는편 소요시간 |
| ---- | -------- | -------- | ------ | ------ | --------- | ----------- | ----------- | --------------- | ----------- | ----------- | --------------- |
| 1    | 20251202 | 20251209 | 7C1151 | 7C1152 | 223,500원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 2    | 20251202 | 20251209 | 7C1151 | 7C1152 | 223,500원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 3    | 20251202 | 20251209 | 7C1151 | 7C1152 | 223,900원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 4    | 20251202 | 20251209 | 7C1151 | 7C1152 | 224,500원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 5    | 20251202 | 20251209 | 7C1151 | 7C1152 | 225,900원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 6    | 20251202 | 20251209 | 7C1151 | 7C1152 | 225,900원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 7    | 20251202 | 20251209 | 7C1151 | 7C1152 | 226,000원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 8    | 20251202 | 20251209 | 7C1151 | 7C1152 | 226,000원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 9    | 20251202 | 20251209 | 7C1151 | 7C1152 | 226,100원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |
| 10   | 20251202 | 20251209 | 7C1151 | 7C1152 | 226,400원 | 0720        | 0925        | 125분           | 1015        | 1300        | 165분           |

**참고:** 같은 항공편 조합이 여러 번 나타나는 이유는 각기 다른 카드 할인 혜택이나 판매 파트너에 따라 가격이 다르기 때문입니다.

## MCP 서버 구현을 위한 핵심 정보

### 1. 필수 입력 파라미터

- `departureCode`: 출발지 공항/도시 코드 (예: "PUS", "ICN")
- `arrivalCode`: 도착지 공항/도시 코드 (예: "TYO", "NRT")
- `departureDate`: 출발일 (YYYYMMDD 형식)
- `returnDate`: 복귀일 (YYYYMMDD 형식)

### 2. 고정 파라미터

```javascript
{
  adultCount: 1,          // 성인 1명
  childCount: 0,
  infantCount: 0,
  isNonstop: true,        // 직항만
  seatClass: "Y",         // 이코노미
  tripType: "RT"          // 왕복
}
```

### 3. 응답 데이터 처리

#### 항공편 정보 추출

```javascript
const itineraries = response.itineraries;
// sequence: 1 = 가는편, 2 = 오는편
```

#### 가격 정보 추출 및 최저가 계산

```javascript
const allFares = response.fareMappings.flatMap((mapping) =>
  mapping.fares.map((f) => ({
    itineraryIds: mapping.itineraryIds.split("-"),
    totalFare: f.adult.totalFare,
    partnerCode: f.partnerCode,
  }))
);

// 가격 순 정렬
const sorted = allFares.sort((a, b) => a.totalFare - b.totalFare);
```

#### 항공편-가격 조합

```javascript
const flightWithPrice = allFares.map((fare) => {
  const outbound = itineraries.find(
    (it) => it.itineraryId === fare.itineraryIds[0]
  );
  const inbound = itineraries.find(
    (it) => it.itineraryId === fare.itineraryIds[1]
  );

  return {
    price: fare.totalFare,
    outbound: {
      flightNumber:
        outbound.segments[0].marketingCarrier.airlineCode +
        outbound.segments[0].marketingCarrier.flightNumber,
      departure: outbound.segments[0].departure.time,
      arrival: outbound.segments[0].arrival.time,
      duration: Math.floor(outbound.duration / 60), // 초 → 분
    },
    inbound: {
      flightNumber:
        inbound.segments[0].marketingCarrier.airlineCode +
        inbound.segments[0].marketingCarrier.flightNumber,
      departure: inbound.segments[0].departure.time,
      arrival: inbound.segments[0].arrival.time,
      duration: Math.floor(inbound.duration / 60),
    },
  };
});
```

### 4. 출력 형식

최종 MCP 도구는 다음 형식으로 데이터를 반환해야 합니다:

| 순위 | 출발일 | 복귀일 | 가는편 | 오는편 | 총요금 | 출발시간 | 도착시간 | 소요시간 (가는편) | 출발시간 | 도착시간 | 소요시간 (오는편) |
| ---- | ------ | ------ | ------ | ------ | ------ | -------- | -------- | ----------------- | -------- | -------- | ----------------- |

## 추가 참고사항

### 시간 형식 변환

- API 응답: `"0720"` (문자열)
- 표시 형식: `"07:20"` 또는 그대로 사용

### Duration 변환

- API 응답: 초 단위 (예: 7500초)
- 표시 형식: 분 단위 (예: 125분) 또는 시간:분 (예: 2시간 5분)

### 공항 코드 매핑

응답의 `status.airportsCodeMap`에서 공항 이름 확인 가능:

```json
{
  "NRT": {
    "airportName": "나리타국제공항",
    "cityName": "도쿄"
  },
  "PUS": {
    "airportName": "김해국제공항",
    "cityName": "부산"
  }
}
```

### 항공사 코드 매핑

응답의 `status.airlinesCodeMap`에서 항공사 이름 확인 가능:

```json
{
  "7C": "제주항공",
  "LJ": "진에어",
  "KE": "대한항공",
  "OZ": "아시아나항공"
}
```

## 구현 예시 (의사 코드)

```javascript
async function searchNaverFlights(departure, arrival, departDate, returnDate) {
  const payload = {
    adultCount: 1,
    childCount: 0,
    infantCount: 0,
    device: "pc",
    isNonstop: true,
    seatClass: "Y",
    tripType: "RT",
    itineraries: [
      {
        departureLocationCode: departure,
        departureLocationType: "airport",
        arrivalLocationCode: arrival,
        arrivalLocationType: "airport",
        departureDate: departDate, // "YYYYMMDD"
      },
      {
        departureLocationCode: arrival,
        departureLocationType: "airport",
        arrivalLocationCode: departure,
        arrivalLocationType: "airport",
        departureDate: returnDate, // "YYYYMMDD"
      },
    ],
    openReturnDays: 0,
    flightFilter: {
      filter: {
        airlines: [],
        departureAirports: [[departure], []],
        arrivalAirports: [[], [departure]],
        departureTime: [],
        fareTypes: [],
        flightDurationSeconds: [],
        hasCardBenefit: true,
        isIndividual: false,
        isLowCarbonEmission: false,
        isSameAirlines: false,
        isSameDepArrAirport: true,
        isTravelClub: false,
        minFare: {},
        viaCount: [],
        selectedItineraries: [],
      },
      limit: 200,
      skip: 0,
      sort: { adultMinFare: 1 },
    },
    initialRequest: true,
  };

  const response = await fetch(
    "https://flight-api.naver.com/flight/international/searchFlights",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "User-Agent": "Mozilla/5.0 ...",
        Referer: "https://flight.naver.com/",
      },
      body: JSON.stringify(payload),
    }
  );

  const text = await response.text();

  // SSE 형식 파싱: "data: {...}" → {...}
  const dataLine = text.split("\n").find((line) => line.startsWith("data: "));
  const jsonData = JSON.parse(dataLine.substring(6));

  // 데이터 가공 및 반환
  return processFlightData(jsonData);
}
```

## 결론

네이버 항공권 API는 GraphQL이 아닌 **REST API with SSE (Server-Sent Events)** 방식을 사용합니다.

핵심 포인트:

1. ✅ 단일 엔드포인트: `/flight/international/searchFlights`
2. ✅ POST 요청으로 검색 조건 전송
3. ✅ SSE 형식으로 실시간 응답 수신
4. ✅ `itineraries`와 `fareMappings`를 조합하여 최저가 항공편 정보 추출
5. ✅ 항공편 ID로 매칭하여 상세 정보 조회 가능
