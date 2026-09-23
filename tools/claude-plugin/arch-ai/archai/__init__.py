"""archai — 건축 AI 공통 도구 모음.

모듈:
  law        국가법령정보센터 Open API로 건축 관련 법령 검색/조문 조회
  dxf_tools  DXF 도면 해석(레이어/문자/치수/면적) 및 평면도 작도
  ifc_tools  IFC(BIM) 모델 조회/검증/속성 수정/물량 추출
  structure  하중조합, 보 해석, RC 보 휨·전단 검토, 최소두께 검토
  bom        건축 BOM(자재/단가/조립체) SQLite DB 구축과 물량·비용 산출
  spec       KCS 형식 시방서 골격 생성과 시방서-BOM 교차검토
  kcsc       국가건설기준센터 API로 KDS·KCS·전문시방서 원문 조회
  price      조달청 가격정보 API 조회와 BOM 단가 연계

각 모듈은 `python -m archai.<module> --help`로 CLI 실행이 가능하고,
archai.mcp_server가 같은 기능을 MCP 도구로 노출한다.
"""

__version__ = "0.2.0"
