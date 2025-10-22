#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { searchNaverFlights } from "./tools/NaverFlightSearch.js";

// Create server instance
const server = new McpServer({
  name: "naver-flight-mcp",
  version: "1.0.0",
});

// Register flight search tool
server.tool(
  "search_naver_flights",
  "네이버 항공권 검색 API를 사용하여 최저가 항공권 정보를 조회합니다",
  {
    departure: z.string().describe("출발지 공항 코드 (예: PUS, ICN, GMP)"),
    arrival: z.string().describe("도착지 공항 코드 (예: TYO, NRT, HND)"),
    departureDate: z.string().describe("출발일 (YYYY-MM-DD 형식)"),
    returnDate: z.string().describe("복귀일 (YYYY-MM-DD 형식)"),
  },
  async ({
    departure,
    arrival,
    departureDate,
    returnDate,
  }): Promise<CallToolResult> => {
    const result = await searchNaverFlights(
      departure,
      arrival,
      departureDate,
      returnDate
    );

    // ✅ 반드시 type: "text" 를 리터럴로 명시
    return result;
  }
);

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("네이버 항공권 MCP 서버가 시작되었습니다.");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
