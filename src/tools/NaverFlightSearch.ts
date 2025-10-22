import { z } from "zod";
import fetch from "node-fetch";

const NAVER_FLIGHT_API_BASE =
  "https://flight-api.naver.com/flight/international/searchFlights";
const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";

// 전역 검색 간격 제어 (Rate Limiting 방지)
let lastSearchTime = 0;
const MIN_SEARCH_INTERVAL = 3000; // 3초 최소 간격 (네이버 API 특성 고려)

// API 응답 타입 정의
interface FlightSegment {
  departure: {
    airportCode: string;
    date: string;
    time: string;
    terminal: string;
  };
  arrival: {
    airportCode: string;
    date: string;
    time: string;
    terminal: string;
  };
  marketingCarrier: {
    airlineCode: string;
    flightNumber: string;
  };
  operatingCarrier: {
    airlineCode: string;
    flightNumber: string;
  };
  flightDuration: number;
  groundDuration: number;
  aircraftCode: string;
}

interface Itinerary {
  itineraryId: string;
  duration: number;
  sequence: number;
  segments: FlightSegment[];
  carbonEmission: number;
}

interface Fare {
  partnerCode: string;
  fareType: string;
  adult: {
    totalFare: number;
    qCharge: number;
    tax: number;
  };
  isConfirmed: boolean;
  baggageFeeType: string;
}

interface FareMapping {
  itineraryIds: string;
  fares: Fare[];
  carbonEmission: number;
  curation: string[];
  sameFareMappings: any[];
}

interface SearchStatus {
  searchKey: string;
  __v: number;
  requestedPartnerCount: number;
  completedPartnerCount: number;
  isCompleted: boolean;
  airlinesCodeMap: Record<string, string>;
  itineraryAirports: any[];
  airportsCodeMap: Record<string, { airportName: string; cityName: string }>;
  fareTypesCodeMap: Record<string, any>;
  durationSecondsRanges: any[];
  lowestFare: {
    direct: number;
    a01: number;
  };
  priceRange: {
    min: number;
    max: number;
  };
  expireAt: string;
  hasCarbonEmission: boolean;
}

interface NaverFlightApiResponse {
  uniqueId: string;
  status: SearchStatus;
  itineraries: Itinerary[];
  fareMappings: FareMapping[];
  isExpired: boolean;
  popularFlights: any[];
}

interface ProcessedFlight {
  rank: number;
  departureDate: string;
  returnDate: string;
  outboundFlight: string;
  returnFlight: string;
  totalFare: number;
  outboundDeparture: string;
  outboundArrival: string;
  outboundDuration: number;
  returnDeparture: string;
  returnArrival: string;
  returnDuration: number;
}

// Helper function for making Naver Flight API requests with retry logic
async function makeNaverFlightRequest<T>(
  payload: any,
  retryCount = 3
): Promise<T | null> {
  const headers = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    "User-Agent": USER_AGENT,
    Referer: "https://flight.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    Pragma: "no-cache",
  };

  for (let attempt = 1; attempt <= retryCount; attempt++) {
    try {
      console.log(`네이버 항공권 API 요청 시도 ${attempt}/${retryCount}`);

      // 요청 간 지연 시간 추가 (Rate Limiting 방지)
      if (attempt > 1) {
        const delay = attempt * 3000; // 3초, 6초, 9초... (네이버 API 특성 고려)
        console.log(`${delay}ms 대기 중...`);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃 (네이버 API 특성 고려)

      const response = await fetch(NAVER_FLIGHT_API_BASE, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        if (response.status === 429) {
          console.log(
            `Rate limit 도달 (429), ${attempt * 5000}ms 대기 후 재시도`
          );
          await new Promise((resolve) => setTimeout(resolve, attempt * 5000));
          continue;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // SSE 스트림 처리 - 여러 번 시도해서 완전한 데이터 수집
      let result = (await processSSEStream(response)) as T;

      // 데이터가 부족한 경우 추가 대기 후 재시도
      if (!result || (result as any).itineraries?.length < 5) {
        console.log("데이터가 부족함, 추가 대기 후 재시도...");
        await new Promise((resolve) => setTimeout(resolve, 3000)); // 3초 대기

        // 같은 요청을 다시 시도
        const retryResponse = await fetch(NAVER_FLIGHT_API_BASE, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (retryResponse.ok) {
          const retryResult = (await processSSEStream(retryResponse)) as T;
          if (
            retryResult &&
            (retryResult as any).itineraries?.length >
              (result as any)?.itineraries?.length
          ) {
            result = retryResult;
            console.log("재시도로 더 많은 데이터 획득");
          }
        }
      }

      console.log(`API 요청 성공 (시도 ${attempt}/${retryCount})`);
      return result;
    } catch (error) {
      console.error(
        `네이버 항공권 API 요청 실패 (시도 ${attempt}/${retryCount}):`,
        error
      );

      if (attempt === retryCount) {
        console.error("모든 재시도 실패");
        return null;
      }

      // 네트워크 오류나 타임아웃의 경우 더 긴 대기 (네이버 API 특성 고려)
      if (
        (error as any).name === "AbortError" ||
        (error as any).message?.includes("timeout")
      ) {
        console.log(
          `타임아웃 또는 네트워크 오류, ${attempt * 2000}ms 대기 후 재시도`
        );
        await new Promise((resolve) => setTimeout(resolve, attempt * 2000));
      }
    }
  }

  return null;
}

// 유틸리티 함수들
function formatDate(dateStr: string): string {
  // YYYY-MM-DD -> YYYYMMDD
  return dateStr.replace(/-/g, "");
}

function formatTime(timeStr: string): string {
  // "0720" -> "07:20"
  if (timeStr.length === 4) {
    return `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}`;
  }
  return timeStr;
}

function formatDuration(seconds: number): number {
  // 초 -> 분
  return Math.floor(seconds / 60);
}

function parseSSE(text: string): any {
  // SSE 형식에서 JSON 추출
  const lines = text.split("\n");
  const dataLine = lines.find((line) => line.startsWith("data: "));
  if (!dataLine) {
    throw new Error("SSE 데이터를 찾을 수 없습니다");
  }
  return JSON.parse(dataLine.substring(6));
}

// SSE 스트림을 완전히 처리하는 함수 (node-fetch 호환)
async function processSSEStream(response: any): Promise<any> {
  const text = await response.text();
  const lines = text.split("\n");

  let lastValidData: any = null;

  console.log("SSE 응답 처리 시작...");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      try {
        const data = JSON.parse(line.substring(6));
        console.log(
          `SSE 데이터 수신: 항공편 ${data.itineraries?.length || 0}개, 요금 ${
            data.fareMappings?.length || 0
          }개`
        );

        // 데이터가 있는 경우에만 업데이트
        if (
          data.itineraries &&
          data.itineraries.length > 0 &&
          data.fareMappings &&
          data.fareMappings.length > 0
        ) {
          lastValidData = data;
          console.log(
            `유효한 데이터 발견: 항공편 ${data.itineraries.length}개, 요금 ${data.fareMappings.length}개`
          );
        }
      } catch (error) {
        console.log(`SSE 데이터 파싱 오류: ${error}`);
      }
    }
  }

  if (!lastValidData) {
    console.log("유효한 데이터를 찾을 수 없음");
    return null;
  }

  console.log(
    `최종 데이터: 항공편 ${lastValidData.itineraries.length}개, 요금 ${lastValidData.fareMappings.length}개`
  );
  return lastValidData;
}

function validateDate(dateStr: string): boolean {
  const regex = /^\d{4}-\d{2}-\d{2}$/;
  if (!regex.test(dateStr)) return false;

  // 날짜 문자열을 로컬 시간대로 파싱
  const [year, month, day] = dateStr.split("-").map(Number);
  const date = new Date(year, month - 1, day);

  // 현재 시간이 잘못 설정된 경우를 대비해 2024년 이후 날짜는 모두 허용
  const minDate = new Date(2024, 0, 1);

  return date >= minDate;
}

function createFlightSearchPayload(
  departure: string,
  arrival: string,
  departureDate: string,
  returnDate: string
) {
  return {
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
        departureDate: formatDate(departureDate),
      },
      {
        departureLocationCode: arrival,
        departureLocationType: "airport",
        arrivalLocationCode: departure,
        arrivalLocationType: "airport",
        departureDate: formatDate(returnDate),
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
}

function processFlightData(
  apiResponse: NaverFlightApiResponse
): ProcessedFlight[] {
  try {
    console.log(
      `API 응답 처리 시작 - 항공편: ${apiResponse.itineraries.length}개, 요금: ${apiResponse.fareMappings.length}개`
    );

    // API 응답 유효성 검사
    if (!apiResponse.itineraries || apiResponse.itineraries.length === 0) {
      console.log("항공편 정보가 없습니다");
      return [];
    }

    if (!apiResponse.fareMappings || apiResponse.fareMappings.length === 0) {
      console.log("요금 정보가 없습니다");
      return [];
    }

    // 모든 fare 추출 및 평탄화
    const allFares = apiResponse.fareMappings.flatMap((mapping) =>
      mapping.fares.map((f) => ({
        itineraryIds: mapping.itineraryIds.split("-"),
        totalFare: f.adult.totalFare,
        partnerCode: f.partnerCode,
        fareType: f.fareType,
        isConfirmed: f.isConfirmed,
      }))
    );

    console.log(`총 ${allFares.length}개의 요금 정보 발견`);

    // 가격 순 정렬
    const sortedFares = allFares.sort((a, b) => a.totalFare - b.totalFare);

    // 상위 10개 선택
    const top10 = sortedFares.slice(0, 10);

    // 항공편 정보와 조합
    const flightInfo = top10
      .map((fare, idx) => {
        const itinerary1 = apiResponse.itineraries.find(
          (it) => it.itineraryId === fare.itineraryIds[0]
        );
        const itinerary2 = apiResponse.itineraries.find(
          (it) => it.itineraryId === fare.itineraryIds[1]
        );

        const getFlightInfo = (itinerary: Itinerary | undefined) => {
          if (
            !itinerary ||
            !itinerary.segments ||
            itinerary.segments.length === 0
          ) {
            return null;
          }
          const seg = itinerary.segments[0];
          return {
            airline:
              seg.marketingCarrier.airlineCode +
              seg.marketingCarrier.flightNumber,
            departure: seg.departure.time,
            arrival: seg.arrival.time,
            duration: formatDuration(itinerary.duration),
            date: seg.departure.date,
          };
        };

        const out = getFlightInfo(itinerary1);
        const ret = getFlightInfo(itinerary2);

        return {
          rank: idx + 1,
          departureDate: out?.date || "",
          returnDate: ret?.date || "",
          outboundFlight: out?.airline || "",
          returnFlight: ret?.airline || "",
          totalFare: fare.totalFare,
          outboundDeparture: out?.departure || "",
          outboundArrival: out?.arrival || "",
          outboundDuration: out?.duration || 0,
          returnDeparture: ret?.departure || "",
          returnArrival: ret?.arrival || "",
          returnDuration: ret?.duration || 0,
        };
      })
      .filter(
        (flight) =>
          // 유효한 데이터만 필터링
          flight.outboundFlight && flight.returnFlight && flight.totalFare > 0
      );

    console.log(`처리 완료 - ${flightInfo.length}개의 유효한 항공편`);
    return flightInfo;
  } catch (error) {
    console.error("항공편 데이터 처리 중 오류:", error);
    return [];
  }
}

// Format flight data
function formatFlight(flight: ProcessedFlight): string {
  return [
    `순위: ${flight.rank}`,
    `출발일: ${flight.departureDate}`,
    `복귀일: ${flight.returnDate}`,
    `가는편: ${flight.outboundFlight}`,
    `오는편: ${flight.returnFlight}`,
    `총요금: ${flight.totalFare.toLocaleString()}원`,
    `가는편 출발: ${formatTime(flight.outboundDeparture)}`,
    `가는편 도착: ${formatTime(flight.outboundArrival)}`,
    `소요시간: ${flight.outboundDuration}분`,
    `오는편 출발: ${formatTime(flight.returnDeparture)}`,
    `오는편 도착: ${formatTime(flight.returnArrival)}`,
    `소요시간: ${flight.returnDuration}분`,
    "---",
  ].join("\n");
}

// Export the tool function for use in index.ts
export async function searchNaverFlights(
  departure: string,
  arrival: string,
  departureDate: string,
  returnDate: string
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  try {
    console.log(
      `네이버 항공권 검색 시작: ${departure} → ${arrival}, ${departureDate} ~ ${returnDate}`
    );

    // 검색 간격 제어 (Rate Limiting 방지)
    const currentTime = Date.now();
    const timeSinceLastSearch = currentTime - lastSearchTime;

    if (timeSinceLastSearch < MIN_SEARCH_INTERVAL) {
      const waitTime = MIN_SEARCH_INTERVAL - timeSinceLastSearch;
      console.log(`검색 간격 제어: ${waitTime}ms 대기 중...`);
      await new Promise((resolve) => setTimeout(resolve, waitTime));
    }
    lastSearchTime = Date.now();

    // 입력 유효성 검사
    if (!validateDate(departureDate)) {
      return {
        content: [
          {
            type: "text",
            text: "출발일 형식이 올바르지 않거나 과거 날짜입니다. YYYY-MM-DD 형식으로 입력해주세요.",
          },
        ],
      };
    }

    if (!validateDate(returnDate)) {
      return {
        content: [
          {
            type: "text",
            text: "복귀일 형식이 올바르지 않거나 과거 날짜입니다. YYYY-MM-DD 형식으로 입력해주세요.",
          },
        ],
      };
    }

    const departureDateObj = new Date(departureDate);
    const returnDateObj = new Date(returnDate);

    if (returnDateObj <= departureDateObj) {
      return {
        content: [
          {
            type: "text",
            text: "복귀일은 출발일보다 늦어야 합니다.",
          },
        ],
      };
    }

    // API 호출
    const payload = createFlightSearchPayload(
      departure,
      arrival,
      departureDate,
      returnDate
    );

    console.log("API 요청 페이로드 생성 완료");
    const apiResponse = await makeNaverFlightRequest<NaverFlightApiResponse>(
      payload
    );

    if (!apiResponse) {
      console.log("API 응답이 없습니다");
      return {
        content: [
          {
            type: "text",
            text: `항공권 검색 중 오류가 발생했습니다.\n\n**가능한 원인:**\n- 네이버 API 서버 응답 지연 (일반적으로 4-5초 소요)\n- 네트워크 연결 문제\n- 서버 일시적 오류\n- 검색 제한 (Rate Limiting)\n\n**해결방법:**\n- 잠시 후 다시 시도해주세요 (네이버 API는 응답이 느릴 수 있습니다)\n- 다른 날짜나 노선으로 검색해보세요\n- 연속 검색 시 첫 번째가 실패할 수 있으니 재시도해주세요\n\n**검색 조건:**\n- 출발지: ${departure} → 도착지: ${arrival}\n- 출발일: ${departureDate}\n- 복귀일: ${returnDate}`,
          },
        ],
      };
    }

    console.log("API 응답 수신 완료, 데이터 처리 시작");

    // 데이터 처리
    const processedFlights = processFlightData(apiResponse);

    if (processedFlights.length === 0) {
      console.log("처리된 항공편이 없습니다");
      return {
        content: [
          {
            type: "text",
            text: `검색 결과가 없습니다.\n\n**검색 조건:**\n- 출발지: ${departure} → 도착지: ${arrival}\n- 출발일: ${departureDate}\n- 복귀일: ${returnDate}\n\n**가능한 원인:**\n- 해당 날짜에 운항하지 않는 항공편\n- 직항편이 없는 노선\n- 항공사 스케줄 변경\n- 네이버 API 응답 지연 (4-5초 소요)\n\n**권장사항:**\n- 다른 날짜로 검색해보세요\n- 경유편 포함 검색을 고려해보세요\n- 인근 공항으로 검색해보세요\n- 잠시 후 재시도해보세요 (API 응답이 느릴 수 있습니다)`,
          },
        ],
      };
    }

    console.log(`검색 완료: ${processedFlights.length}개 항공편 발견`);

    // 결과 포맷팅
    const formattedFlights = processedFlights.map(formatFlight);
    const flightsText = `항공권 검색 결과 (${departure} → ${arrival}):\n\n${formattedFlights.join(
      "\n"
    )}`;

    const summary = `\n\n**검색 요약:**\n- 출발지: ${departure} → 도착지: ${arrival}\n- 출발일: ${departureDate}\n- 복귀일: ${returnDate}\n- 총 ${
      processedFlights.length
    }개 항공권 발견\n- 최저가: ${processedFlights[0]?.totalFare.toLocaleString()}원`;

    return {
      content: [
        {
          type: "text",
          text: flightsText + summary,
        },
      ],
    };
  } catch (error) {
    console.error("네이버 항공권 검색 중 예상치 못한 오류:", error);
    return {
      content: [
        {
          type: "text",
          text: `항공권 검색 중 예상치 못한 오류가 발생했습니다.\n\n**오류 정보:** ${
            (error as any).message || "알 수 없는 오류"
          }\n\n**네이버 API 특성:**\n- 일반적으로 4-5초 응답 시간 소요\n- 첫 번째 검색이 실패할 수 있음\n- 연속 검색 시 성공률 향상\n\n**해결방법:**\n- 잠시 후 다시 시도해주세요\n- 다른 검색 조건으로 시도해보세요\n- 연속으로 2-3회 재시도해보세요\n- 문제가 지속되면 관리자에게 문의해주세요`,
        },
      ],
    };
  }
}
