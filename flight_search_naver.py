#!/usr/bin/env python3
"""
네이버 항공권 검색 도구
네이버 항공권 MCP를 사용하여 항공편을 검색합니다.
사용자가 체류일을 설정할 수 있습니다.
"""
import json
import sys
import argparse
from datetime import datetime, timedelta
import subprocess
import os
import time

# UTF-8 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

def parse_price(price_str):
    """가격 문자열에서 숫자 추출"""
    if not price_str or not isinstance(price_str, str):
        return float('inf')
    try:
        return int(price_str.replace('₩', '').replace(',', '').replace('원', ''))
    except ValueError:
        return float('inf')

def call_naver_flight_mcp(departure, arrival, departure_date, return_date):
    """네이버 항공권 MCP 호출"""
    try:
        print(f"네이버 항공권 검색: {departure} → {arrival}")
        print(f"출발일: {departure_date}, 복귀일: {return_date}")
        
        # Node MCP 서버 실행
        process = subprocess.Popen(
            ["node", "dist/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=os.getcwd()
        )
        
        # JSON-RPC 요청 구성
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_naver_flights",
                "arguments": {
                    "departure": departure,
                    "arrival": arrival,
                    "departureDate": departure_date,
                    "returnDate": return_date
                }
            }
        }
        
        # 요청 전송
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=30)
        
        if process.returncode != 0:
            print(f"MCP 서버 오류 (return code: {process.returncode})")
            if stderr:
                print(f"에러 메시지: {stderr}")
            return None
        
        # 응답 파싱 - 마지막 JSON 라인만 추출
        try:
            lines = stdout.strip().split('\n')
            json_line = None
            
            # 마지막 JSON 라인 찾기
            for line in reversed(lines):
                if line.strip().startswith('{') and '"jsonrpc"' in line:
                    json_line = line.strip()
                    break
            
            if not json_line:
                print(f"JSON 응답을 찾을 수 없음")
                print(f"응답 내용: {stdout}")
                return None
                
            response = json.loads(json_line)
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0 and "text" in content[0]:
                    # 텍스트 응답을 파싱하여 구조화된 데이터로 변환
                    return parse_mcp_response(content[0]["text"])
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"JSON 라인: {json_line}")
            return None
        
    except subprocess.TimeoutExpired:
        print("MCP 호출 타임아웃 (30초)")
        process.kill()
        return None
    except Exception as e:
        print(f"MCP 호출 오류: {e}")
        return None

def parse_mcp_response(response_text):
    """MCP 응답 텍스트를 구조화된 데이터로 파싱"""
    try:
        lines = response_text.split('\n')
        flight_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == "순위":
                    flight_data['rank'] = int(value)
                elif key == "출발일":
                    flight_data['departure_date'] = value
                elif key == "복귀일":
                    flight_data['return_date'] = value
                elif key == "가는편":
                    flight_data['outbound_flight'] = value
                elif key == "오는편":
                    flight_data['return_flight'] = value
                elif key == "총요금":
                    flight_data['total_price'] = value
                elif key == "가는편 출발":
                    flight_data['outbound_departure'] = value
                elif key == "가는편 도착":
                    flight_data['outbound_arrival'] = value
                elif key == "소요시간" and "가는편" in lines[lines.index(line)-1]:
                    flight_data['outbound_duration'] = value
                elif key == "오는편 출발":
                    flight_data['return_departure'] = value
                elif key == "오는편 도착":
                    flight_data['return_arrival'] = value
                elif key == "소요시간" and "오는편" in lines[lines.index(line)-1]:
                    flight_data['return_duration'] = value
        
        return flight_data if flight_data else None
        
    except Exception as e:
        print(f"응답 파싱 오류: {e}")
        return None

def search_flights_naver(params):
    """네이버 항공권 검색 실행 (사용자 설정 체류일)"""
    print(f"=== {params['origin']} ↔ {params['destination']} 네이버 항공권 검색 ===")
    print(f"검색 조건:")
    print(f"  - 노선: {params['origin']} ↔ {params['destination']} (왕복)")
    print(f"  - 기간: {params['start_date']} ~ {params['end_date']}")
    print(f"  - 체류일: 현지 체류 {params['stay_days']}일 (출발일+{params['stay_days']-1}일=복귀일)")
    print(f"  - 승객: 성인 {params['adults']}명")
    
    try:
        # 날짜 범위 생성
        start_dt = datetime.strptime(params['start_date'], '%Y-%m-%d').date()
        end_dt = datetime.strptime(params['end_date'], '%Y-%m-%d').date()
        
        # 출발일 리스트 생성
        departure_dates = []
        current_date = start_dt
        while current_date <= end_dt:
            departure_dates.append(current_date)
            current_date += timedelta(days=1)
        
        print(f"\n검색할 출발일: {len(departure_dates)}개")
        
        # 각 출발일에 대해 사용자 설정 체류일 후 복귀일로 검색
        results_data = []
        total_searches = len(departure_dates)
        success_count = 0
        error_count = 0
        
        for i, depart_date in enumerate(departure_dates):
            return_date = depart_date + timedelta(days=params['stay_days'] - 1)  # 체류일 - 1일 (복귀일)
            
            # 진행률 표시
            print(f"진행률: {i+1}/{total_searches} - {depart_date} → {return_date}")
            
            try:
                # Rate limiting: 3초 대기 (MCP 서버 로직과 동일)
                if i > 0:
                    print("검색 간격 제어: 3초 대기 중...")
                    time.sleep(3)
                
                # 네이버 항공권 MCP 호출
                result = call_naver_flight_mcp(
                    departure=params['origin'],
                    arrival=params['destination'],
                    departure_date=depart_date.strftime('%Y-%m-%d'),
                    return_date=return_date.strftime('%Y-%m-%d')
                )
                
                if result:
                    # 결과 처리
                    flight_dict = {
                        'departure_date': depart_date.strftime('%Y-%m-%d'),
                        'return_date': return_date.strftime('%Y-%m-%d'),
                        'stay_days': params['stay_days'],
                        'flight_info': result
                    }
                    results_data.append(flight_dict)
                    success_count += 1
                    print(f"✓ 검색 성공: {result.get('total_price', 'N/A')}")
                else:
                    print(f"✗ 결과 없음: {depart_date} → {return_date}")
                    
            except Exception as e:
                error_count += 1
                print(f"✗ 오류: {depart_date} → {return_date}: {type(e).__name__}")
                if error_count <= 5:  # 처음 5개 오류만 상세 출력
                    print(f"  상세: {str(e)}")
        
        print(f"\n검색 완료!")
        print(f"총 검색: {total_searches}개")
        print(f"검색 성공: {success_count}개")
        print(f"오류 발생: {error_count}개")
        
        return results_data
        
    except Exception as e:
        print(f"[ERROR] 검색 중 오류 발생: {type(e).__name__}: {str(e)}")
        return []

def display_results(results_data, params):
    """결과 출력"""
    if not results_data:
        print("\n❌ 검색 결과가 없습니다.")
        return
    
    # 결과를 가격순으로 정렬
    results_data.sort(key=lambda x: parse_price(x.get('flight_info', {}).get('total_price', '0')))
    
    # 상위 5개 결과 출력
    print(f"\n=== {params['origin']} ↔ {params['destination']} 네이버 항공권 최저가 상위 5개 ===")
    print("| 순위 | 출발일 | 복귀일 | 항공편 | 총요금 | 출발시간 | 도착시간 | 소요시간 |")
    print("| -- | --- | --- | --- | ---- | ---- | ---- | ---- |")
    
    for i, result in enumerate(results_data[:5], 1):
        flight_info = result.get('flight_info', {})
        
        print(f"| {i} | {result['departure_date']} | {result['return_date']} | {flight_info.get('outbound_flight', 'N/A')} | {flight_info.get('total_price', 'N/A')} | {flight_info.get('outbound_departure', 'N/A')} | {flight_info.get('outbound_arrival', 'N/A')} | {flight_info.get('outbound_duration', 'N/A')} |")
    
    # 통계 정보
    prices = [parse_price(r.get('flight_info', {}).get('total_price', '0')) for r in results_data]
    valid_prices = [p for p in prices if p != float('inf')]
    
    if valid_prices:
        min_price = min(valid_prices)
        max_price = max(valid_prices)
        avg_price = sum(valid_prices) / len(valid_prices)
        
        print(f"\n### 통계 정보")
        print(f"- **총 조합 수**: {len(results_data)}개")
        print(f"- **최저가**: ₩{min_price:,}")
        print(f"- **최고가**: ₩{max_price:,}")
        print(f"- **평균가**: ₩{avg_price:,.0f}")

def save_results(results_data, params):
    """결과를 JSON 파일로 저장"""
    if not results_data:
        return
    
    # 파일명 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{params['origin']}_{params['destination']}_naver_flights_{timestamp}.json"
    
    # 결과 데이터 구성
    output_data = {
        'search_parameters': params,
        'naver_flight_results': results_data,
        'search_summary': {
            'total_combinations': len(results_data),
            'search_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'naver_flight_mcp'
        }
    }
    
    # 파일 저장
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과가 '{filename}' 파일에 저장되었습니다.")

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='네이버 항공권 검색 도구 (사용자 설정 체류일)')
    parser.add_argument('--origin', '-o', default='PUS', help='출발지 공항코드 (기본값: PUS)')
    parser.add_argument('--destination', '-d', default='NRT', help='도착지 공항코드 (기본값: NRT)')
    parser.add_argument('--start-date', '-s', help='검색 시작일 (YYYY-MM-DD)')
    parser.add_argument('--end-date', '-e', help='검색 종료일 (YYYY-MM-DD)')
    parser.add_argument('--stay-days', type=int, default=5, help='체류일 수 (기본값: 5일)')
    parser.add_argument('--adults', type=int, default=1, help='성인 승객 수 (기본값: 1)')
    parser.add_argument('--save', action='store_true', help='결과를 JSON 파일로 저장')
    
    args = parser.parse_args()
    
    # 기본값 설정
    if not args.start_date:
        args.start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    if not args.end_date:
        args.end_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
    
    params = {
        'origin': args.origin.upper(),
        'destination': args.destination.upper(),
        'start_date': args.start_date,
        'end_date': args.end_date,
        'stay_days': args.stay_days,
        'adults': args.adults
    }
    
    try:
        # 항공편 검색
        results_data = search_flights_naver(params)
        
        # 결과 출력
        display_results(results_data, params)
        
        # 결과 저장
        if args.save and results_data:
            save_results(results_data, params)
        
        print("\n✅ 네이버 항공권 검색 완료!")
        
    except KeyboardInterrupt:
        print("\n\n👋 검색이 취소되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
