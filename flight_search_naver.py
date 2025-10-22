#!/usr/bin/env python3
"""
네이버 항공권 검색 도구
네이버 항공권 MCP를 사용하여 항공편을 검색합니다.
"""
import json
import sys
import argparse
from datetime import datetime, timedelta
import subprocess
import os

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
        # MCP 호출을 위한 명령어 구성
        # 실제 MCP 호출은 Cursor 환경에서 직접 이루어져야 함
        print(f"네이버 항공권 검색: {departure} → {arrival}")
        print(f"출발일: {departure_date}, 복귀일: {return_date}")
        
        # MCP 호출 결과를 시뮬레이션 (실제로는 MCP 도구를 사용해야 함)
        # 이 부분은 실제 MCP 호출로 대체되어야 합니다
        return None
        
    except Exception as e:
        print(f"MCP 호출 오류: {e}")
        return None

def search_flights_naver(params):
    """네이버 항공권 검색 실행"""
    print(f"=== {params['origin']} ↔ {params['destination']} 네이버 항공권 검색 ===")
    print(f"검색 조건:")
    print(f"  - 노선: {params['origin']} ↔ {params['destination']} (왕복)")
    print(f"  - 기간: {params['start_date']} ~ {params['end_date']}")
    print(f"  - 체류일: {params['min_stay_days']}~{params['max_stay_days']}일")
    print(f"  - 승객: 성인 {params['adults']}명")
    
    try:
        # 날짜 범위 생성
        start_dt = datetime.strptime(params['start_date'], '%Y-%m-%d').date()
        end_dt = datetime.strptime(params['end_date'], '%Y-%m-%d').date()
        
        date_list = []
        current_date = start_dt
        while current_date <= end_dt:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        
        print(f"\n검색할 날짜: {len(date_list)}개")
        
        # 각 날짜 조합에 대해 검색
        results_data = []
        total_combinations = 0
        valid_combinations = 0
        error_count = 0
        
        for i, depart_date in enumerate(date_list):
            for j, return_date in enumerate(date_list[i:]):
                stay_duration = (return_date - depart_date).days + 1  # 시작일과 복귀일 포함
                total_combinations += 1
                
                # 체류일 조건 확인
                if params['min_stay_days'] <= stay_duration <= params['max_stay_days']:
                    valid_combinations += 1
                    
                    # 진행률 표시
                    if valid_combinations % 10 == 0:
                        print(f"진행률: {valid_combinations}개 조합 검색 중...")
                    
                    try:
                        # 네이버 항공권 MCP 호출
                        result = call_naver_flight_mcp(
                            departure=params['origin'],
                            arrival=params['destination'],
                            departure_date=depart_date.strftime('%Y-%m-%d'),
                            return_date=return_date.strftime('%Y-%m-%d')
                        )
                        
                        if result:
                            # 결과 처리 (실제 MCP 응답에 맞게 수정 필요)
                            flight_dict = {
                                'departure_date': depart_date.strftime('%Y-%m-%d'),
                                'return_date': return_date.strftime('%Y-%m-%d'),
                                'stay_days': stay_duration,
                                'flight_info': result
                            }
                            results_data.append(flight_dict)
                        else:
                            print(f"결과 없음: {depart_date} -> {return_date}")
                            
                    except Exception as e:
                        error_count += 1
                        print(f"오류: {depart_date} -> {return_date}: {type(e).__name__}")
                        if error_count <= 5:  # 처음 5개 오류만 상세 출력
                            print(f"  상세: {str(e)}")
        
        print(f"\n검색 완료!")
        print(f"총 조합: {total_combinations}개")
        print(f"유효 조합: {valid_combinations}개")
        print(f"검색 성공: {len(results_data)}개")
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
        
        print(f"| {i} | {result['departure_date']} | {result['return_date']} | {flight_info.get('flight_number', 'N/A')} | {flight_info.get('total_price', 'N/A')} | {flight_info.get('departure_time', 'N/A')} | {flight_info.get('arrival_time', 'N/A')} | {flight_info.get('duration', 'N/A')} |")
    
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
    parser = argparse.ArgumentParser(description='네이버 항공권 검색 도구')
    parser.add_argument('--origin', '-o', default='PUS', help='출발지 공항코드 (기본값: PUS)')
    parser.add_argument('--destination', '-d', default='NRT', help='도착지 공항코드 (기본값: NRT)')
    parser.add_argument('--start-date', '-s', help='검색 시작일 (YYYY-MM-DD)')
    parser.add_argument('--end-date', '-e', help='검색 종료일 (YYYY-MM-DD)')
    parser.add_argument('--min-stay', type=int, default=5, help='최소 체류일 (기본값: 5)')
    parser.add_argument('--max-stay', type=int, default=7, help='최대 체류일 (기본값: 7)')
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
        'min_stay_days': args.min_stay,
        'max_stay_days': args.max_stay,
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
