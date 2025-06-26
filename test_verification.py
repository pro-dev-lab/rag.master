#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from typing import List, Dict
import pandas as pd

def generate_manual_index(root_dir: str, manual_type: str = "user") -> List[Dict]:
    """
    지정된 루트 디렉토리에서 하위 메뉴얼 디렉토리를 순회하며,
    .md 파일과 img 폴더의 이미지들을 분석하여 지정된 JSON 형태로 반환합니다.
    """
    result = []
    base_dir_name = os.path.basename(os.path.normpath(root_dir))

    for entry in os.scandir(root_dir):
        if entry.is_dir():
            manu_type = entry.name
            md_path = os.path.join(entry.path, f"{manu_type}.md")
            img_dir = os.path.join(entry.path, "img")

            if not os.path.isfile(md_path):
                continue

            image_urls = []
            if os.path.isdir(img_dir):
                for img_file in sorted(os.listdir(img_dir)):
                    if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        image_urls.append(
                            f"https://doc.tg-cloud.co.kr/manual/console/{base_dir_name}/{manu_type}/img/{img_file}"
                        )

            result.append({
                "text": f"{manu_type}.md",
                "metadata": {
                    "manual_type": manual_type,
                    "manu_type": manu_type,
                    "source_url": f"https://doc.tg-cloud.co.kr/manual/console/{base_dir_name}/{manu_type}/{manu_type}",
                    "image_url": image_urls
                }
            })

    return result

def generate_chunks_from_index(index_list: List[Dict], base_dir: str) -> List[Dict]:
    """
    Markdown 파일을 직접 줄 단위로 읽고 섹션(##) 기준으로 나누어 chunk 생성
    """
    all_chunks = []

    for item in index_list:
        md_filename = item["text"]
        manu_type = item["metadata"]["manu_type"]
        manual_type = item["metadata"]["manual_type"]
        source_url = item["metadata"]["source_url"]
        image_url_list = item["metadata"]["image_url"]

        md_path = os.path.join(base_dir, manu_type, md_filename)
        if not os.path.isfile(md_path):
            print(f"⚠️ 파일 없음: {md_path}")
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_section = "__intro__"
        current_text_lines = []
        skip_section = False

        def resolve_image_urls(text: str) -> List[str]:
            matches = re.findall(r'!\[.*?\]\((.*?)\)', text)
            urls = []
            for filename in matches:
                for full_url in image_url_list:
                    if filename in full_url:
                        urls.append(full_url)
            return urls
        
        for line in lines:
            if line.strip().startswith("## "):
                if current_text_lines and not skip_section:
                    full_text = "".join(current_text_lines).strip()
                    if full_text:
                        chunk = {
                            "text": full_text,
                            "metadata": {
                                "manual_type": manual_type,
                                "manu_type": manu_type,
                                "section": current_section,
                                "source_url": source_url,
                                "image_url": resolve_image_urls(full_text)
                            }
                        }
                        all_chunks.append(chunk)

                current_section = line.strip().replace("##", "").strip()
                skip_section = (current_section == "목차")
                current_text_lines = []
            else:
                if not skip_section:
                    current_text_lines.append(line)

        if current_text_lines and not skip_section:
            full_text = "".join(current_text_lines).strip()
            if full_text:
                chunk = {
                    "text": full_text,
                    "metadata": {
                        "manual_type": manual_type,
                        "manu_type": manu_type,
                        "section": current_section,
                        "source_url": source_url,
                        "image_url": resolve_image_urls(full_text)
                    }
                }
                all_chunks.append(chunk)

    return all_chunks

def main():
    print("🔄 매뉴얼 데이터 전처리 시작...")
    
    # 1. 메뉴얼 인덱스 생성
    manual_index = generate_manual_index("./manual/user/firstUser", manual_type="firstUser")
    print(f"📋 인덱스 생성 완료: {len(manual_index)}개 매뉴얼")
    
    # 2. 청크 생성
    chunks = generate_chunks_from_index(manual_index, base_dir="./manual/user/firstUser")
    print(f"📦 청크 생성 완료: {len(chunks)}개 청크")
    
    # 3. DataFrame 변환
    df = pd.json_normalize(chunks)
    
    # 4. 검증 시작
    print("\n" + "=" * 80)
    print("📊 GENERATE_CHUNKS_FROM_INDEX 함수 결과물 검증")
    print("=" * 80)

    # 1. 전체 청크 개수 및 기본 정보
    print(f"\n1️⃣ 기본 정보")
    print(f"   • 총 청크 개수: {len(chunks)}")
    print(f"   • DataFrame 형태 변환 후 행 수: {len(df)}")

    # 2. 각 청크의 구조 검증
    print(f"\n2️⃣ 청크 구조 검증")
    if len(chunks) > 0:
        sample_chunk = chunks[0]
        print(f"   • 청크 키: {list(sample_chunk.keys())}")
        print(f"   • 메타데이터 키: {list(sample_chunk['metadata'].keys())}")

    # 3. 섹션별 분할 검증 (login.md 기준)
    print(f"\n3️⃣ 섹션 분할 검증 (login.md 예상 결과)")
    login_chunks = [chunk for chunk in chunks if chunk['metadata']['manu_type'] == 'login']
    print(f"   • login 관련 청크 수: {len(login_chunks)}")

    expected_login_sections = ["__intro__", "1. 로그인 페이지", "2. 로그인을 통한 인증"]
    actual_login_sections = [chunk['metadata']['section'] for chunk in login_chunks]

    print(f"   • 예상 섹션: {expected_login_sections}")
    print(f"   • 실제 섹션: {actual_login_sections}")
    print(f"   • 목차 섹션 제외됨: {'목차' not in actual_login_sections}")

    # 4. 이미지 URL 매핑 검증
    print(f"\n4️⃣ 이미지 URL 매핑 검증")
    for i, chunk in enumerate(login_chunks):
        section = chunk['metadata']['section']
        images = chunk['metadata']['image_url']
        text_preview = chunk['text'][:100].replace('\n', ' ')
        
        print(f"   청크 {i+1} - 섹션: '{section}'")
        print(f"   • 이미지 개수: {len(images)}")
        print(f"   • 텍스트 미리보기: {text_preview}...")
        if images:
            print(f"   • 첫 번째 이미지: {images[0]}")
        print()

    # 5. namespaces.md 검증
    print(f"\n5️⃣ namespaces.md 검증")
    namespace_chunks = [chunk for chunk in chunks if chunk['metadata']['manu_type'] == 'namespaces']
    print(f"   • namespaces 관련 청크 수: {len(namespace_chunks)}")

    expected_namespace_sections = ["__intro__", "1. Namespace 메뉴 진입", "2. Namespace 생성 신청", "3. Namespace 생성 확인"]
    actual_namespace_sections = [chunk['metadata']['section'] for chunk in namespace_chunks]

    print(f"   • 예상 섹션: {expected_namespace_sections}")
    print(f"   • 실제 섹션: {actual_namespace_sections}")

    # 6. 메타데이터 일관성 검증
    print(f"\n6️⃣ 메타데이터 일관성 검증")
    manual_types = set(chunk['metadata']['manual_type'] for chunk in chunks)
    manu_types = set(chunk['metadata']['manu_type'] for chunk in chunks)

    print(f"   • manual_type 종류: {manual_types}")
    print(f"   • manu_type 종류: {manu_types}")
    print(f"   • 모든 청크가 source_url 보유: {all('source_url' in chunk['metadata'] for chunk in chunks)}")

    # 7. 텍스트 길이 분석
    print(f"\n7️⃣ 텍스트 길이 분석")
    text_lengths = [len(chunk['text']) for chunk in chunks]
    print(f"   • 평균 텍스트 길이: {sum(text_lengths)/len(text_lengths):.1f} 문자")
    print(f"   • 최소 텍스트 길이: {min(text_lengths)} 문자")
    print(f"   • 최대 텍스트 길이: {max(text_lengths)} 문자")

    # 8. 빈 청크 또는 문제 청크 검증
    print(f"\n8️⃣ 데이터 품질 검증")
    empty_chunks = [chunk for chunk in chunks if not chunk['text'].strip()]
    print(f"   • 빈 텍스트 청크 수: {len(empty_chunks)}")

    missing_metadata_chunks = [chunk for chunk in chunks if not all(key in chunk['metadata'] for key in ['manual_type', 'manu_type', 'section', 'source_url'])]
    print(f"   • 메타데이터 누락 청크 수: {len(missing_metadata_chunks)}")

    print(f"\n{'='*80}")
    print("✅ 검증 완료!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main() 