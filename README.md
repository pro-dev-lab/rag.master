# RAG Master

## 프로젝트 개요
RAG Master는 LangChain을 활용하여 정보 검색 및 생성(Retrieval-Augmented Generation) 작업을 수행하는 종합적인 프로젝트입니다. 다양한 데이터 소스에서 문서를 로드하고, 벡터 저장소에 저장하여 효율적인 검색과 AI 기반 질의응답을 지원합니다.

## 주요 기능
- **문서 처리**: 다양한 형식(PDF, TXT, JSON, CSV, Excel)의 문서 로드 및 처리
- **텍스트 분할**: 문서를 의미 있는 청크 단위로 분할하여 저장
- **벡터화**: OpenAI, HuggingFace 등 다양한 임베딩 모델을 통한 텍스트 벡터화
- **벡터 저장소**: ChromaDB, FAISS를 활용한 벡터 데이터 저장 및 검색
- **검색 엔진**: 유사도 기반 검색 및 하이브리드 검색 지원
- **AI 응답 생성**: 검색된 문서를 바탕으로 정확한 답변 생성
- **평가 시스템**: RAG 시스템의 성능 평가 및 개선

## 프로젝트 구조

```
RAG_Master/
├── LangChain/                          # LangChain 학습 및 실습 노트북
│   ├── data/                          # 샘플 데이터 파일들
│   │   ├── Rivian_EN.txt
│   │   ├── Tesla_EN.txt
│   │   ├── final_docs.jsonl
│   │   ├── kakao_chat.jsonl
│   │   └── ...
│   ├── LangChain_001_SimpleRAG.ipynb      # 기본 RAG 구현
│   ├── LangChain_002_SimpleRAG_LCEL.ipynb # LCEL을 활용한 RAG
│   ├── LangChain_003_Data_Processing.ipynb # 데이터 처리 및 청킹
│   ├── LangChain_004_Vectorstore_Retrieval.ipynb # 벡터 저장소 검색
│   ├── LangChain_005_Advanced_Retrieval.ipynb   # 고급 검색 기법
│   └── LangChain_006_Generation_Evaluation.ipynb # 생성 및 평가
├── TKS_Q&A_Chatbot/                   # 실제 챗봇 구현
│   ├── chroma_db/                     # ChromaDB 벡터 저장소
│   ├── Data_Processing.ipynb          # 데이터 전처리
│   ├── Data_Vectorlizing.ipynb        # 벡터화 처리
│   ├── LangChain_DataProcessing.ipynb # LangChain 데이터 처리
│   └── LangChain_manual_Searching.ipynb # 매뉴얼 검색 시스템
├── vector.db/                         # 벡터 데이터베이스
├── langchain_env/                     # Python 가상환경
├── requirements.txt                    # 프로젝트 의존성
└── README.md                          # 프로젝트 문서
```

## 설치 및 설정 방법

### 1. 저장소 클론
```bash
git clone https://github.com/pro-dev-lab/rag.master.git
cd RAG_Master
```

### 2. 가상환경 설정
```bash
# conda 환경 활성화
conda activate langchain_conda

# 또는 새로운 환경 생성
conda create -n rag_env python=3.11
conda activate rag_env
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
echo "ANTHROPIC_API_KEY=your-anthropic-api-key-here" >> .env
```

## 사용 방법

### LangChain 학습 노트북
1. **기본 RAG 구현** (`LangChain_001_SimpleRAG.ipynb`)
   - LangChain의 기본적인 RAG 파이프라인 구현
   - 문서 로딩, 청킹, 임베딩, 검색, 생성 과정 학습

2. **LCEL 활용** (`LangChain_002_SimpleRAG_LCEL.ipynb`)
   - LangChain Expression Language를 활용한 체인 구성
   - 모듈화된 RAG 시스템 구현

3. **데이터 처리** (`LangChain_003_Data_Processing.ipynb`)
   - 다양한 형식의 문서 처리
   - 텍스트 분할 및 전처리 기법

4. **벡터 저장소 검색** (`LangChain_004_Vectorstore_Retrieval.ipynb`)
   - ChromaDB, FAISS 등 벡터 저장소 활용
   - 다양한 검색 전략 구현

5. **고급 검색** (`LangChain_005_Advanced_Retrieval.ipynb`)
   - 하이브리드 검색, 재순위화 등 고급 기법
   - 검색 성능 최적화

6. **평가 및 생성** (`LangChain_006_Generation_Evaluation.ipynb`)
   - RAG 시스템 성능 평가
   - 답변 품질 측정 및 개선

### TKS Q&A 챗봇
1. **데이터 처리** (`Data_Processing.ipynb`)
   - 매뉴얼 데이터 전처리 및 정제

2. **벡터화** (`Data_Vectorlizing.ipynb`)
   - 문서 벡터화 및 ChromaDB 저장

3. **검색 시스템** (`LangChain_manual_Searching.ipynb`)
   - 실제 매뉴얼 검색 챗봇 구현

## 주요 기술 스택

### LangChain Ecosystem
- **langchain**: 0.2.16 - 핵심 프레임워크
- **langchain-community**: 0.2.16 - 커뮤니티 통합
- **langchain-openai**: 0.1.23 - OpenAI 통합
- **langchain-chroma**: 0.1.3 - ChromaDB 통합

### AI/ML 라이브러리
- **transformers**: 4.44.2 - HuggingFace 모델
- **sentence-transformers**: 3.1.0 - 임베딩 모델
- **torch**: 2.2.1 - 딥러닝 프레임워크
- **faiss-cpu**: 1.8.0.post1 - 벡터 검색

### 데이터 처리
- **pandas**: 2.2.3 - 데이터 분석
- **pypdf**: 4.3.1 - PDF 처리
- **openpyxl**: 3.1.5 - Excel 파일 처리

### 웹 인터페이스
- **gradio**: 4.44.0 - 웹 UI
- **streamlit**: 1.28.0+ - 대시보드

## 환경 요구사항

- **Python**: 3.11.12 (권장)
- **운영체제**: macOS, Linux, Windows
- **메모리**: 최소 8GB RAM (대용량 데이터 처리 시 16GB+ 권장)
- **API 키**: OpenAI, Anthropic 등 (선택사항)

## 주의사항

1. **API 키 관리**: `.env` 파일을 통해 API 키를 안전하게 관리하세요
2. **가상환경**: 프로젝트별 가상환경 사용을 권장합니다
3. **데이터 용량**: 벡터 저장소는 상당한 디스크 공간을 사용할 수 있습니다
4. **버전 호환성**: Python 3.11 환경에서 테스트되었습니다

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 문의사항

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해 주세요.