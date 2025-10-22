import { MCPTool } from "mcp-framework";
import { z } from "zod";
import fetch from "node-fetch";

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

interface FlightSearchInput {
  departure: string;
  arrival: string;
  departureDate: string;
  returnDate: string;
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

class NaverFlightSearch extends MCPTool<FlightSearchInput> {
  name = "search_naver_flights";
  description =
    "네이버 항공권 검색 API를 사용하여 최저가 항공권 정보를 조회합니다";

  schema = {
    departure: {
      type: z.string(),
      description: "출발지 공항 코드 (예: PUS, ICN, GMP)",
    },
    arrival: {
      type: z.string(),
      description: "도착지 공항 코드 (예: TYO, NRT, HND)",
    },
    departureDate: {
      type: z.string(),
      description: "출발일 (YYYY-MM-DD 형식)",
    },
    returnDate: {
      type: z.string(),
      description: "복귀일 (YYYY-MM-DD 형식)",
    },
  };

  // 유틸리티 함수들
  private formatDate(dateStr: string): string {
    // YYYY-MM-DD -> YYYYMMDD
    return dateStr.replace(/-/g, "");
  }

  private formatTime(timeStr: string): string {
    // "0720" -> "07:20"
    if (timeStr.length === 4) {
      return `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}`;
    }
    return timeStr;
  }

  private formatDuration(seconds: number): number {
    // 초 -> 분
    return Math.floor(seconds / 60);
  }

  private parseSSE(text: string): any {
    // SSE 형식에서 JSON 추출
    const lines = text.split("\n");
    const dataLine = lines.find((line) => line.startsWith("data: "));
    if (!dataLine) {
      throw new Error("SSE 데이터를 찾을 수 없습니다");
    }
    return JSON.parse(dataLine.substring(6));
  }

  private validateDate(dateStr: string): boolean {
    const regex = /^\d{4}-\d{2}-\d{2}$/;
    if (!regex.test(dateStr)) return false;

    // 날짜 문자열을 로컬 시간대로 파싱
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);

    // 현재 시간이 잘못 설정된 경우를 대비해 2024년 이후 날짜는 모두 허용
    const minDate = new Date(2024, 0, 1);

    return date >= minDate;
  }

  async callNaverFlightAPI(
    departure: string,
    arrival: string,
    departureDate: string,
    returnDate: string
  ): Promise<NaverFlightApiResponse> {
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
          departureDate: this.formatDate(departureDate),
        },
        {
          departureLocationCode: arrival,
          departureLocationType: "airport",
          arrivalLocationCode: departure,
          arrivalLocationType: "airport",
          departureDate: this.formatDate(returnDate),
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
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
          Referer: "https://flight.naver.com/",
        },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      throw new Error(
        `API 호출 실패: ${response.status} ${response.statusText}`
      );
    }

    const text = await response.text();
    return this.parseSSE(text);
  }

  processFlightData(apiResponse: NaverFlightApiResponse): ProcessedFlight[] {
    // 모든 fare 추출 및 평탄화
    const allFares = apiResponse.fareMappings.flatMap((mapping) =>
      mapping.fares.map((f) => ({
        itineraryIds: mapping.itineraryIds.split("-"),
        totalFare: f.adult.totalFare,
        partnerCode: f.partnerCode,
        fareType: f.fareType,
      }))
    );

    // 가격 순 정렬
    const sortedFares = allFares.sort((a, b) => a.totalFare - b.totalFare);

    // 상위 10개 선택
    const top10 = sortedFares.slice(0, 10);

    // 항공편 정보와 조합
    const flightInfo = top10.map((fare, idx) => {
      const itinerary1 = apiResponse.itineraries.find(
        (it) => it.itineraryId === fare.itineraryIds[0]
      );
      const itinerary2 = apiResponse.itineraries.find(
        (it) => it.itineraryId === fare.itineraryIds[1]
      );

      const getFlightInfo = (itinerary: Itinerary | undefined) => {
        if (!itinerary) return null;
        const seg = itinerary.segments[0];
        return {
          airline:
            seg.marketingCarrier.airlineCode +
            seg.marketingCarrier.flightNumber,
          departure: seg.departure.time,
          arrival: seg.arrival.time,
          duration: this.formatDuration(itinerary.duration),
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
    });

    return flightInfo;
  }

  private generateMarkdownTable(flights: ProcessedFlight[]): string {
    if (flights.length === 0) {
      return "검색 결과가 없습니다.";
    }

    const header =
      "| 순위 | 출발일 | 복귀일 | 가는편 | 오는편 | 총요금 | 가는편 출발 | 가는편 도착 | 소요시간 | 오는편 출발 | 오는편 도착 | 소요시간 |";
    const separator =
      "|------|--------|--------|--------|--------|--------|-------------|-------------|----------|-------------|-------------|----------|";

    const rows = flights
      .map((flight) => {
        return `| ${flight.rank} | ${flight.departureDate} | ${
          flight.returnDate
        } | ${flight.outboundFlight} | ${
          flight.returnFlight
        } | ${flight.totalFare.toLocaleString()}원 | ${this.formatTime(
          flight.outboundDeparture
        )} | ${this.formatTime(flight.outboundArrival)} | ${
          flight.outboundDuration
        }분 | ${this.formatTime(flight.returnDeparture)} | ${this.formatTime(
          flight.returnArrival
        )} | ${flight.returnDuration}분 |`;
      })
      .join("\n");

    return `${header}\n${separator}\n${rows}`;
  }

  async execute(input: FlightSearchInput): Promise<string> {
    try {
      // 입력 유효성 검사
      if (!this.validateDate(input.departureDate)) {
        throw new Error(
          "출발일 형식이 올바르지 않거나 과거 날짜입니다. YYYY-MM-DD 형식으로 입력해주세요."
        );
      }

      if (!this.validateDate(input.returnDate)) {
        throw new Error(
          "복귀일 형식이 올바르지 않거나 과거 날짜입니다. YYYY-MM-DD 형식으로 입력해주세요."
        );
      }

      const departureDate = new Date(input.departureDate);
      const returnDate = new Date(input.returnDate);

      if (returnDate <= departureDate) {
        throw new Error("복귀일은 출발일보다 늦어야 합니다.");
      }

      // API 호출
      console.log(
        `API 호출 시작: ${input.departure} → ${input.arrival}, ${input.departureDate} → ${input.returnDate}`
      );
      const apiResponse = await this.callNaverFlightAPI(
        input.departure,
        input.arrival,
        input.departureDate,
        input.returnDate
      );

      console.log(`API 응답 받음:`, JSON.stringify(apiResponse, null, 2));

      // 데이터 처리
      const processedFlights = this.processFlightData(apiResponse);
      console.log(`처리된 항공편 수: ${processedFlights.length}`);

      // 결과 반환
      const table = this.generateMarkdownTable(processedFlights);

      const summary = `\n\n**검색 요약:**\n- 출발지: ${
        input.departure
      } → 도착지: ${input.arrival}\n- 출발일: ${
        input.departureDate
      }\n- 복귀일: ${input.returnDate}\n- 총 ${
        processedFlights.length
      }개 항공권 발견\n- 최저가: ${processedFlights[0]?.totalFare.toLocaleString()}원`;

      return table + summary;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`항공권 검색 중 오류가 발생했습니다: ${error.message}`);
      }
      throw new Error("알 수 없는 오류가 발생했습니다.");
    }
  }
}

export default NaverFlightSearch;
