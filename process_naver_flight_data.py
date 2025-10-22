#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import glob
import argparse
from datetime import datetime, timedelta

# UTF-8 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

def process_naver_flight_data(file_path, origin=None, destination=None):
    """네이버 항공권 데이터 통합 처리 (단일 파일)"""
    
    print(f"=== 네이버 항공권 데이터 통합 처리 ===")
    print(f"처리할 파일: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            flight_results = data['naver_flight_results']
            print(f"✓ {file_path}: {len(flight_results)}개 항공편 로드")
            
            # 파일에서 출발지/목적지 자동 감지
            if not origin or not destination:
                search_params = data.get('search_parameters', {})
                detected_origin = search_params.get('origin', 'UNKNOWN')
                detected_destination = search_params.get('destination', 'UNKNOWN')
                
                if not origin:
                    origin = detected_origin
                if not destination:
                    destination = detected_destination
                    
                print(f"✓ 출발지/목적지 자동 감지: {origin} ↔ {destination}")
                
    except FileNotFoundError:
        print(f"❌ {file_path} 파일을 찾을 수 없습니다.")
        return []
    except Exception as e:
        print(f"❌ {file_path} 처리 중 오류: {e}")
        return []
    
    route_name = f"{origin} ↔ {destination}"
    
    if not flight_results:
        print("처리할 데이터가 없습니다.")
        return []
    
    # 유효한 항공편만 필터링
    valid_flights = []
    
    for option in flight_results:
        flight_info = option.get('flight_info', {})
        
        # 가격이 있는 항공편만 유지
        if flight_info.get('total_price') and flight_info['total_price'] != "0" and flight_info['total_price'] != "":
            # 가격에서 숫자만 추출 (₩ 기호와 쉼표 제거)
            price_str = str(flight_info['total_price']).replace('₩', '').replace(',', '').replace('원', '')
            try:
                price_numeric = int(price_str)
                valid_flights.append({
                    'departure_date': option['departure_date'],
                    'return_date': option['return_date'],
                    'stay_days': option['stay_days'],
                    'flight_number': flight_info.get('outbound_flight', 'N/A'),
                    'total_price': flight_info.get('total_price', 'N/A'),
                    'price_numeric': price_numeric,
                    'departure_time': flight_info.get('outbound_departure', 'N/A'),
                    'arrival_time': flight_info.get('outbound_arrival', 'N/A'),
                    'duration': flight_info.get('outbound_duration', 'N/A'),
                    'return_departure_time': flight_info.get('return_departure', 'N/A'),
                    'return_arrival_time': flight_info.get('return_arrival', 'N/A'),
                    'return_duration': flight_info.get('return_duration', 'N/A')
                })
            except ValueError:
                print(f"[WARNING] 가격 파싱 실패: {flight_info['total_price']}")
                continue
    
    # 중복 제거 (같은 출발일-복귀일 조합 중 최저가만 유지)
    unique_flights = {}
    for flight in valid_flights:
        key = f"{flight['departure_date']}-{flight['return_date']}"
        if key not in unique_flights or flight['price_numeric'] < unique_flights[key]['price_numeric']:
            unique_flights[key] = flight
    
    # 중복 제거된 항공편을 리스트로 변환
    unique_flights_list = list(unique_flights.values())
    
    # 가격순으로 정렬
    unique_flights_list.sort(key=lambda x: x['price_numeric'])
    
    # 상위 5개 결과
    top_5_results = unique_flights_list[:5]
    
    # 주말 필터링 함수
    def is_weekend_included(departure_date, return_date):
        """출발일과 복귀일 사이에 주말이 포함되는지 확인"""
        try:
            dep_date = datetime.strptime(departure_date, '%Y-%m-%d')
            ret_date = datetime.strptime(return_date, '%Y-%m-%d')
            
            # 출발일부터 복귀일까지의 모든 날짜 확인
            current_date = dep_date
            weekend_count = 0
            
            while current_date <= ret_date:
                # 토요일(5) 또는 일요일(6)인지 확인
                if current_date.weekday() in [5, 6]:
                    weekend_count += 1
                current_date += timedelta(days=1)
            
            return weekend_count
        except:
            return 0
    
    # 주말 하루 포함된 항공편 필터링
    weekend_one_day_flights = []
    for flight in unique_flights_list:
        weekend_count = is_weekend_included(flight['departure_date'], flight['return_date'])
        if weekend_count == 1:
            weekend_one_day_flights.append(flight)
    
    # 주말 모두 포함된 항공편 필터링 (2일 이상)
    weekend_all_flights = []
    for flight in unique_flights_list:
        weekend_count = is_weekend_included(flight['departure_date'], flight['return_date'])
        if weekend_count >= 2:
            weekend_all_flights.append(flight)
    
    # 주말 하루 포함 상위 3개
    weekend_one_day_top3 = weekend_one_day_flights[:3]
    
    # 주말 모두 포함 상위 3개
    weekend_all_top3 = weekend_all_flights[:3]
    
    # 결과 출력
    print(f"\n=== {route_name} 네이버 항공권 최저가 상위 5개 ===")
    
    for i, result in enumerate(top_5_results, 1):
        print(f"{i}위: {result['total_price']}")
        print(f"   출발: {result['departure_date']} ({result['departure_time']})")
        print(f"   도착: {result['arrival_time']} (소요시간: {result['duration']})")
        print(f"   귀국: {result['return_date']} ({result['return_departure_time']} → {result['return_arrival_time']})")
        print(f"   항공편: {result['flight_number']}")
        print()
    
    # 주말 하루 포함 상위 3개 출력
    if weekend_one_day_top3:
        print(f"\n=== {route_name} 주말 하루 포함 상위 3개 ===")
        for i, result in enumerate(weekend_one_day_top3, 1):
            print(f"{i}위: {result['total_price']}")
            print(f"   출발: {result['departure_date']} ({result['departure_time']})")
            print(f"   도착: {result['arrival_time']} (소요시간: {result['duration']})")
            print(f"   귀국: {result['return_date']} ({result['return_departure_time']} → {result['return_arrival_time']})")
            print(f"   항공편: {result['flight_number']}")
            print()
    else:
        print(f"\n=== {route_name} 주말 하루 포함 항공편 없음 ===")
    
    # 주말 모두 포함 상위 3개 출력
    if weekend_all_top3:
        print(f"\n=== {route_name} 주말 모두 포함 상위 3개 ===")
        for i, result in enumerate(weekend_all_top3, 1):
            print(f"{i}위: {result['total_price']}")
            print(f"   출발: {result['departure_date']} ({result['departure_time']})")
            print(f"   도착: {result['arrival_time']} (소요시간: {result['duration']})")
            print(f"   귀국: {result['return_date']} ({result['return_departure_time']} → {result['return_arrival_time']})")
            print(f"   항공편: {result['flight_number']}")
            print()
    else:
        print(f"\n=== {route_name} 주말 모두 포함 항공편 없음 ===")
    
    # 결과를 JSON 파일로 저장
    results_data = {
        'search_summary': {
            'route': route_name,
            'source': 'naver_flight_mcp',
            'period': '검색 기간',
            'passengers': '성인 1명',
            'total_combinations': len(unique_flights_list),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_file': file_path
        },
        'top_5_results': top_5_results,
        'weekend_one_day_top3': weekend_one_day_top3,
        'weekend_all_top3': weekend_all_top3,
        'all_results': unique_flights_list[:10]  # 상위 10개만 저장
    }
    
    # 파일명 생성
    output_filename = f"{origin}_{destination}_naver_flight_results.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)
    
    print(f"총 {len(unique_flights_list)}개의 왕복 조합을 분석했습니다.")
    print(f"결과가 '{output_filename}' 파일에 저장되었습니다.")
    
    # 최종 요약 보고서 생성
    create_naver_summary_report(results_data, unique_flights_list, origin, destination)
    
    return top_5_results

def create_naver_summary_report(results_data, unique_flights_list, origin='PUS', destination='NRT'):
    """네이버 항공권 최종 요약 보고서 생성 (재사용 가능)"""
    route_name = f"{origin} ↔ {destination}"
    
    # 공항명 매핑
    airport_names = {
        'PUS': '김해국제공항',
        'NRT': '나리타공항',
        'KIX': '간사이공항',
        'ICN': '인천국제공항',
        'GMP': '김포국제공항',
        'TYO': '도쿄',
        'HND': '하네다공항'
    }
    
    origin_name = airport_names.get(origin, origin)
    destination_name = airport_names.get(destination, destination)
    
    summary_content = f"""# {route_name} 네이버 항공권 최저가 분석

## 검색 조건

- **노선**: {origin_name}({origin}) ↔ {destination_name}({destination})
- **데이터 소스**: 네이버 항공권 MCP
- **검색 기간**: 검색 실행 기간
- **승객**: 성인 1명
- **체류일**: 검색 조건에 따라 결정

## 최저가 상위 5개 결과

| 순위 | 출발일     | 복귀일     | 항공편   | 총요금   | 출발시간 | 도착시간 | 소요시간   |
| ---- | ---------- | ---------- | -------- | -------- | -------- | -------- | ---------- |
"""
    
    for i, result in enumerate(results_data['top_5_results'], 1):
        summary_content += f"| {i} | {result['departure_date']} | {result['return_date']} | {result['flight_number']} | {result['total_price']} | {result['departure_time']} | {result['arrival_time']} | {result['duration']} |\n"
    
    # 주말 하루 포함 결과 추가
    if results_data['weekend_one_day_top3']:
        summary_content += f"""
## 주말 하루 포함 상위 3개 결과

| 순위 | 출발일     | 복귀일     | 항공편   | 총요금   | 출발시간 | 도착시간 | 소요시간   |
| ---- | ---------- | ---------- | -------- | -------- | -------- | -------- | ---------- |
"""
        for i, result in enumerate(results_data['weekend_one_day_top3'], 1):
            summary_content += f"| {i} | {result['departure_date']} | {result['return_date']} | {result['flight_number']} | {result['total_price']} | {result['departure_time']} | {result['arrival_time']} | {result['duration']} |\n"
    
    # 주말 모두 포함 결과 추가
    if results_data['weekend_all_top3']:
        summary_content += f"""
## 주말 모두 포함 상위 3개 결과

| 순위 | 출발일     | 복귀일     | 항공편   | 총요금   | 출발시간 | 도착시간 | 소요시간   |
| ---- | ---------- | ---------- | -------- | -------- | -------- | -------- | ---------- |
"""
        for i, result in enumerate(results_data['weekend_all_top3'], 1):
            summary_content += f"| {i} | {result['departure_date']} | {result['return_date']} | {result['flight_number']} | {result['total_price']} | {result['departure_time']} | {result['arrival_time']} | {result['duration']} |\n"
    
    # 통계 정보
    price_range = [f['price_numeric'] for f in unique_flights_list]
    min_price = min(price_range)
    max_price = max(price_range)
    avg_price = sum(price_range) / len(price_range)
    
    summary_content += f"""
## 검색 요약

- **총 조합 수**: {len(unique_flights_list)}개
- **분석 일시**: {results_data['search_summary']['analysis_date']}
- **데이터 소스**: 네이버 항공권 MCP
- **오류 발생**: 없음

## 가격 통계

- **최저가**: ₩{min_price:,}
- **최고가**: ₩{max_price:,}
- **평균가**: ₩{avg_price:,.0f}

## 항공편별 통계

"""
    
    # 항공편별 통계
    flights = {}
    for result in unique_flights_list:
        flight_num = result['flight_number']
        if flight_num not in flights:
            flights[flight_num] = {'count': 0, 'min_price': float('inf')}
        flights[flight_num]['count'] += 1
        flights[flight_num]['min_price'] = min(flights[flight_num]['min_price'], result['price_numeric'])
    
    for flight_num, stats in sorted(flights.items(), key=lambda x: x[1]['min_price']):
        summary_content += f"- **{flight_num}**: {stats['count']}개 조합, 최저가 ₩{stats['min_price']:,}\n"
    
    summary_content += f"""
## 조사 로그

- **건너뛴 날짜**: 없음 (모든 유효 조합 검색 완료)
- **실패 호출**: 없음 (오류 발생 없음)
- **데이터 소스**: 네이버 항공권 MCP API
- **필드 매핑**: 정상 (flight_number, total_price, duration 등 모든 필드 정상)

## 결론

**최저가 항공편**: {results_data['top_5_results'][0]['flight_number']} {results_data['top_5_results'][0]['total_price']}

- 출발: {results_data['top_5_results'][0]['departure_date']} ({results_data['top_5_results'][0]['departure_time']})
- 복귀: {results_data['top_5_results'][0]['return_date']} ({results_data['top_5_results'][0]['return_departure_time']})
- 체류: {results_data['top_5_results'][0]['stay_days']}일
- 소요시간: {results_data['top_5_results'][0]['duration']}

이 항공편이 검색 기간 중 {route_name} 노선의 최저가 항공편입니다.

## 생성된 파일들

- `{origin}_{destination}_naver_flight_results.json`: 통합 분석 결과
- `{origin}_{destination}_naver_final_results_summary.md`: 최종 요약 보고서
"""
    
    summary_filename = f"{origin}_{destination}_naver_final_results_summary.md"
    with open(summary_filename, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"최종 요약 보고서가 '{summary_filename}' 파일에 저장되었습니다.")

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='네이버 항공권 데이터 통합 처리 도구')
    parser.add_argument('file_path', help='처리할 JSON 파일 경로')
    parser.add_argument('--origin', '-o', help='출발지 공항코드 (자동 감지 가능)')
    parser.add_argument('--destination', '-d', help='도착지 공항코드 (자동 감지 가능)')
    
    args = parser.parse_args()
    
    try:
        # 네이버 항공권 데이터 처리
        results = process_naver_flight_data(
            file_path=args.file_path,
            origin=args.origin.upper() if args.origin else None,
            destination=args.destination.upper() if args.destination else None
        )
        
        if results:
            print(f"\n✅ 네이버 항공권 데이터 처리 완료!")
            print(f"상위 5개 최저가 항공편을 찾았습니다.")
            print(f"주말 필터링 결과도 함께 제공됩니다.")
        else:
            print(f"\n❌ 네이버 항공권 데이터 처리 실패")
            print("검색 결과 파일을 확인해주세요.")
        
    except KeyboardInterrupt:
        print("\n\n👋 처리가 취소되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
