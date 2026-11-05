import os
import sys
from playwright.sync_api import sync_playwright

html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>NEXUS WORK 시스템 구조 및 엔터프라이즈 보안 아키텍처</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');

  :root {
    --bg-main: #0B0F19;
    --bg-card: rgba(17, 24, 39, 0.85);
    --bg-card-inner: rgba(30, 41, 59, 0.7);
    --border-color: rgba(255, 255, 255, 0.08);
    --border-accent: rgba(56, 189, 248, 0.3);
    
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    
    --accent-blue: #38BDF8;
    --accent-indigo: #818CF8;
    --accent-purple: #C084FC;
    --accent-emerald: #34D399;
    --accent-amber: #FBBF24;
    --accent-rose: #FB7185;
    --accent-cyan: #22D3EE;
    
    --badge-blue: rgba(56, 189, 248, 0.15);
    --badge-emerald: rgba(52, 211, 153, 0.15);
    --badge-rose: rgba(251, 113, 133, 0.15);
    --badge-amber: rgba(251, 191, 36, 0.15);
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  body {
    background-color: var(--bg-main);
    color: var(--text-primary);
    width: 2400px;
    height: 1650px;
    padding: 36px 44px;
    overflow: hidden;
    position: relative;
    background-image: 
      radial-gradient(circle at 10% 15%, rgba(56, 189, 248, 0.07) 0%, transparent 40%),
      radial-gradient(circle at 90% 20%, rgba(129, 140, 248, 0.07) 0%, transparent 40%),
      radial-gradient(circle at 50% 85%, rgba(52, 211, 153, 0.05) 0%, transparent 45%),
      linear-gradient(to right, rgba(255, 255, 255, 0.02) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 100% 100%, 48px 48px, 48px 48px;
  }

  /* 헤더 영역 */
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 24px;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .brand-logo {
    width: 58px;
    height: 58px;
    background: linear-gradient(135deg, #0284C7, #6366F1);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 24px rgba(2, 132, 199, 0.4);
    font-weight: 900;
    font-size: 28px;
    letter-spacing: -1px;
    color: #FFF;
  }

  .header-titles h1 {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .header-titles h1 span.highlight {
    background: linear-gradient(90deg, #38BDF8, #818CF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .header-titles p {
    font-size: 15px;
    color: var(--text-secondary);
    margin-top: 4px;
    display: flex;
    gap: 16px;
  }

  .header-titles p span {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .header-badges {
    display: flex;
    gap: 12px;
  }

  .badge {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1px solid transparent;
  }

  .badge-blue { background: var(--badge-blue); color: var(--accent-blue); border-color: rgba(56, 189, 248, 0.3); }
  .badge-emerald { background: var(--badge-emerald); color: var(--accent-emerald); border-color: rgba(52, 211, 153, 0.3); }
  .badge-rose { background: var(--badge-rose); color: var(--accent-rose); border-color: rgba(251, 113, 133, 0.3); }
  .badge-amber { background: var(--badge-amber); color: var(--accent-amber); border-color: rgba(251, 191, 36, 0.3); }

  /* 메인 그리드 레이아웃 */
  .grid-container {
    display: grid;
    grid-template-columns: 460px 1fr 520px;
    gap: 24px;
    height: 1040px;
    margin-bottom: 24px;
  }

  /* 카드 공통 스타일 */
  .section-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 22px;
    display: flex;
    flex-direction: column;
    backdrop-filter: blur(16px);
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
    position: relative;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }

  .card-title {
    font-size: 18px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .card-title .icon-box {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
  }

  .tag {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 4px 8px;
    border-radius: 6px;
    letter-spacing: 0.5px;
  }

  /* 컬럼 1: 클라이언트 & 접근 계층 */
  .col-access {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .node-block {
    background: var(--bg-card-inner);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    position: relative;
    transition: all 0.2s ease;
  }

  .node-block.border-blue { border-left: 4px solid var(--accent-blue); }
  .node-block.border-indigo { border-left: 4px solid var(--accent-indigo); }
  .node-block.border-rose { border-left: 4px solid var(--accent-rose); }
  .node-block.border-emerald { border-left: 4px solid var(--accent-emerald); }

  .node-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .node-title {
    font-size: 15px;
    font-weight: 700;
    color: #FFF;
  }

  .node-desc {
    font-size: 12.5px;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .tech-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }

  .pill {
    background: rgba(255, 255, 255, 0.06);
    color: var(--text-secondary);
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
  }

  /* 네트워크 게이트웨이 & L3/L4 */
  .gateway-banner {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(99, 102, 241, 0.12));
    border: 1px dashed rgba(56, 189, 248, 0.4);
    border-radius: 12px;
    padding: 14px;
    text-align: center;
    margin-top: auto;
  }

  .gateway-banner h4 {
    color: var(--accent-cyan);
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .gateway-banner p {
    font-size: 12px;
    color: var(--text-secondary);
  }

  /* 컬럼 2: 코어 포털 & 비즈니스 모듈 (중앙 대형) */
  .col-core {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .sec-shield-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 12px;
    padding: 12px;
  }

  .shield-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12.5px;
  }

  .shield-icon {
    font-size: 18px;
    color: var(--accent-cyan);
  }

  .shield-text b {
    display: block;
    color: #FFF;
    font-size: 12.5px;
  }

  .shield-text span {
    color: var(--text-muted);
    font-size: 11px;
  }

  .modules-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    flex-grow: 1;
  }

  .module-card {
    background: var(--bg-card-inner);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
  }

  .module-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .module-title {
    font-size: 15px;
    font-weight: 700;
    color: #FFF;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .feature-list {
    list-style: none;
    font-size: 12px;
    color: var(--text-secondary);
    display: flex;
    flex-direction: column;
    gap: 6px;
    line-height: 1.45;
  }

  .feature-list li {
    position: relative;
    padding-left: 14px;
  }

  .feature-list li::before {
    content: "•";
    position: absolute;
    left: 0;
    color: var(--accent-blue);
    font-weight: bold;
  }

  .ai-special-card {
    grid-column: span 2;
    background: linear-gradient(135deg, rgba(88, 28, 135, 0.2), rgba(30, 58, 138, 0.25));
    border: 1px solid rgba(192, 132, 252, 0.3);
    border-radius: 12px;
    padding: 16px;
  }

  .ai-spec-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    margin-top: 10px;
  }

  .ai-spec-box {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 10px;
    font-size: 12px;
  }

  .ai-spec-box h5 {
    color: var(--accent-purple);
    font-size: 12px;
    margin-bottom: 4px;
    font-weight: 700;
  }

  .ai-spec-box p {
    color: var(--text-secondary);
    font-size: 11px;
    line-height: 1.4;
  }

  /* 컬럼 3: DB & 격리 스토리지 계층 */
  .col-storage {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .db-isolation-card {
    background: var(--bg-card-inner);
    border: 1px solid rgba(52, 211, 153, 0.25);
    border-radius: 12px;
    padding: 18px;
    position: relative;
  }

  .db-schema-box {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
    margin-top: 12px;
  }

  .db-schema-title {
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .schema-badge-green { color: var(--accent-emerald); font-size: 11px; font-weight: 600; }
  .schema-badge-red { color: var(--accent-rose); font-size: 11px; font-weight: 600; }

  .schema-tables {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    color: var(--text-secondary);
    line-height: 1.6;
  }

  .file-storage-box {
    background: var(--bg-card-inner);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
  }

  .security-triggers-box {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 12px;
    padding: 14px;
    margin-top: auto;
  }

  .security-triggers-box h4 {
    color: var(--accent-rose);
    font-size: 13.5px;
    font-weight: 700;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .security-triggers-box ul {
    list-style: none;
    font-size: 11.5px;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .security-triggers-box ul li {
    padding-left: 12px;
    position: relative;
  }

  .security-triggers-box ul li::before {
    content: "🔒";
    position: absolute;
    left: 0;
    font-size: 9px;
  }

  /* 하단 전체 영역: AI-XDR 보안 관제 & SOAR 자동대응 파이프라인 */
  .footer-pipeline {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(11, 15, 25, 0.98));
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
  }

  .pipeline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .pipeline-title {
    font-size: 17px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #FFF;
  }

  .pipeline-steps {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    position: relative;
  }

  .pipeline-step {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 14px;
    position: relative;
    display: flex;
    flex-direction: column;
  }

  .pipeline-step::after {
    content: "➔";
    position: absolute;
    right: -14px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--accent-cyan);
    font-size: 18px;
    font-weight: 900;
    z-index: 10;
  }

  .pipeline-step:last-child::after {
    display: none;
  }

  .step-num {
    font-size: 11px;
    font-weight: 800;
    color: var(--accent-cyan);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  .step-name {
    font-size: 14px;
    font-weight: 700;
    color: #FFF;
    margin-bottom: 8px;
  }

  .step-content {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.45;
  }

  .step-content b {
    color: #E2E8F0;
  }

  /* 반응/상태 강조 태그 */
  .tag-semi {
    background: rgba(251, 191, 36, 0.15);
    color: var(--accent-amber);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10.5px;
    font-weight: 700;
  }

  .tag-auto {
    background: rgba(239, 68, 68, 0.15);
    color: var(--accent-rose);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10.5px;
    font-weight: 700;
  }

  .footer-sub {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
</head>
<body>

  <!-- 헤더 영역 -->
  <header>
    <div class="header-left">
      <div class="brand-logo">NX</div>
      <div class="header-titles">
        <h1><span class="highlight">NEXUS WORK</span> 엔터프라이즈 시스템 구조 & 차세대 보안 아키텍처</h1>
        <p>
          <span>🌐 <b>플랫폼:</b> 사내 업무 포털 (ERP + 그룹웨어 + 전자결재 + 생성형 AI 어시스턴트)</span>
          <span>🛡️ <b>프로젝트:</b> 실전 AI Agent 보안 방어전 (App & DB 완벽 하드닝 및 차세대 AI-XDR)</span>
          <span>⚙️ <b>기술스택:</b> Python Flask · MySQL 8.4 (Docker) · Waitress WSGI · Socket.IO · Playwright</span>
        </p>
      </div>
    </div>
    <div class="header-badges">
      <div class="badge badge-emerald">● Zero Vulnerability Design</div>
      <div class="badge badge-blue">● Dual DB Privilege Isolation</div>
      <div class="badge badge-rose">● AI-XDR Hybrid SOAR Active Defense</div>
      <div class="badge badge-amber">● Production Waitress WSGI</div>
    </div>
  </header>

  <!-- 상단/중단 3열 그리드 컨테이너 -->
  <div class="grid-container">

    <!-- 1. 클라이언트 및 진입 계층 -->
    <div class="section-card col-access">
      <div class="card-header">
        <div class="card-title">
          <div class="icon-box" style="background: rgba(56, 189, 248, 0.15); color: var(--accent-blue);">🖥️</div>
          클라이언트 및 인프라 진입 계층
        </div>
        <span class="tag badge-blue">Layer 1: Edge & Ingress</span>
      </div>

      <div class="node-block border-blue">
        <div class="node-header">
          <span class="node-title">웹 브라우저 사용자</span>
          <span class="pill">HTTP/1.1 · HTTPS</span>
        </div>
        <p class="node-desc">
          사원/팀장/임원/관리자 웹 UI 접속.<br/>
          엄격한 CSP(Content Security Policy) 적용으로 외부 스크립트·인라인 스타일 차단.
        </p>
        <div class="tech-pills">
          <span class="pill">Chrome</span>
          <span class="pill">Edge</span>
          <span class="pill">Strict CSP</span>
          <span class="pill">SameSite=Lax</span>
        </div>
      </div>

      <div class="node-block border-indigo">
        <div class="node-header">
          <span class="node-title">nexus-messenger 네이티브 앱</span>
          <span class="pill">REST + WebSocket</span>
        </div>
        <p class="node-desc">
          Flutter 기반 데스크톱 & 모바일 메신저 클라이언트.<br/>
          토큰 기반 인증(Bearer API Token) + Socket.IO 실시간 메시징 송수신.
        </p>
        <div class="tech-pills">
          <span class="pill">/api/v1/*</span>
          <span class="pill">Socket.IO</span>
          <span class="pill">Bearer Auth</span>
        </div>
      </div>

      <div class="node-block border-rose">
        <div class="node-header">
          <span class="node-title">외부 공격자 & 취약점 스캐너</span>
          <span class="pill" style="color: var(--accent-rose);">Threat Vector</span>
        </div>
        <p class="node-desc">
          SQLi, XSS, SSRF, 프롬프트 인젝션, 무차별 대입(Brute-force), L4 DoS 및 허니팟 경로 스캔 시도.
        </p>
        <div class="tech-pills">
          <span class="pill">Decoy Canaries</span>
          <span class="pill">IP Rate Limit</span>
          <span class="pill">Lockout 15min</span>
        </div>
      </div>

      <div class="node-block border-emerald">
        <div class="node-header">
          <span class="node-title">보안관제 센터 & 오케스트레이션</span>
          <span class="pill">SOC / Admin</span>
        </div>
        <p class="node-desc">
          Wazuh EDR, Graylog 로그 수집기, n8n SOAR 워크플로우 엔진, Discord 관제 채널 승인 인터페이스.
        </p>
        <div class="tech-pills">
          <span class="pill">Graylog GELF</span>
          <span class="pill">Wazuh FIM</span>
          <span class="pill">n8n Webhook</span>
        </div>
      </div>

      <div class="gateway-banner">
        <h4>🛡️ pfSense L3/L4 경계 방화벽 & HAProxy</h4>
        <p>192.168.3.10:5070 경유 접속만 강제 (직접 접속 5070 차단)<br/>
        Alias API 연동을 통한 실시간 공격자 IP 블랙홀 드롭</p>
      </div>
    </div>

    <!-- 2. 코어 애플리케이션 계층 (중앙) -->
    <div class="section-card col-core">
      <div class="card-header">
        <div class="card-title">
          <div class="icon-box" style="background: rgba(129, 140, 248, 0.15); color: var(--accent-indigo);">⚡</div>
          NEXUS WORK 코어 서비스 계층 (Flask + Waitress WSGI)
        </div>
        <span class="tag badge-emerald">Layer 2: Core Application</span>
      </div>

      <!-- 상단 방어 쉴드 바 -->
      <div class="sec-shield-bar">
        <div class="shield-item">
          <div class="shield-icon">🛡️</div>
          <div class="shield-text">
            <b>AST 정적 SQL 파라미터화</b>
            <span>SQL 인젝션 원천 차단</span>
          </div>
        </div>
        <div class="shield-item">
          <div class="shield-icon">🔑</div>
          <div class="shield-text">
            <b>Argon2id + Pinning</b>
            <span>고정 관리자/5회 실패 잠금</span>
          </div>
        </div>
        <div class="shield-item">
          <div class="shield-icon">🧹</div>
          <div class="shield-text">
            <b>RichText HTML Sanitizer</b>
            <span>28종 태그/클래스 살균 XSS 방어</span>
          </div>
        </div>
        <div class="shield-item">
          <div class="shield-icon">🪤</div>
          <div class="shield-text">
            <b>Decoy Canaries 허니팟</b>
            <span>/.env, /.git 접근 즉시 탐지</span>
          </div>
        </div>
      </div>

      <!-- 모듈 그리드 -->
      <div class="modules-grid">
        <div class="module-card">
          <div class="module-header">
            <span class="module-title">📋 전자결재 엔진 (Approvals)</span>
            <span class="pill">app/approvals.py</span>
          </div>
          <ul class="feature-list">
            <li>최대 5단계 순차 결재선 및 결재 의견/반려 사유 강제</li>
            <li>지출결의서: 단가×수량 서버 검증 + 일금 한글 금액 위변조 방지</li>
            <li>공문 양식 출력(@media print), 첨부파일 이력 단계별 관리</li>
            <li>종결 문서(승인/반려/철회) DB 행 락 및 상태 불변성 보장</li>
          </ul>
        </div>

        <div class="module-card">
          <div class="module-header">
            <span class="module-title">🏢 그룹웨어 & 포털 (Portal & HR)</span>
            <span class="pill">app/portal.py / hr.py</span>
          </div>
          <ul class="feature-list">
            <li>대시보드: 출퇴근 체크, 결재 대기 배지, 내 업무 요약</li>
            <li>공지사항 및 자유게시판: 이미지/PDF 안전 붙여넣기 및 미리보기</li>
            <li>인사관리: 인사카드, 근태 현황, 연차/휴가 결재 연동</li>
            <li>권한 매트릭스(사원/대리/과장/팀장/관리자) 세부 인가 통제</li>
          </ul>
        </div>

        <div class="module-card">
          <div class="module-header">
            <span class="module-title">💼 ERP & 업무·자원 관리 (Work & ERP)</span>
            <span class="pill">app/erp.py / work.py</span>
          </div>
          <ul class="feature-list">
            <li>업무 관리(할일/진행/완료), 칸반 상태 전이, 프로젝트 진척률</li>
            <li>월간 캘린더: 개인(비공개 관리자도 열람불가)/팀/전사 일정</li>
            <li>30분 단위 회의실/비품 예약: 자원 행 락을 통한 중복 예약 원천 방지</li>
            <li>자료실: 폴더형 4단계 구조, 버전 이력 및 다운로드 전용 서빙</li>
          </ul>
        </div>

        <div class="module-card">
          <div class="module-header">
            <span class="module-title">🔒 시스템 관리 & 보안 대시보드</span>
            <span class="pill">app/admin.py / audit.py</span>
          </div>
          <ul class="feature-list">
            <li>사용자 계정 생성 시 임시 비밀번호 1회 표시 (화면/로그 미저장)</li>
            <li>보안 대시보드: SVG 시계열 차트, 위협 지표 8종, IP/계정 랭킹</li>
            <li>감사 로그 읽기 전용 스트림(4MB 상한) + CSV 공식 주입 방어 내보내기</li>
            <li>최고관리자(admin, hongjh) DB 트리거 고정으로 권한 강등 원천 불가</li>
          </ul>
        </div>

        <!-- AI 어시스턴트 카드 -->
        <div class="ai-special-card">
          <div class="module-header">
            <span class="module-title" style="color: var(--accent-purple);">🤖 생성형 AI 어시스턴트 & 시큐리티 게이트웨이 (AI Agent Engine)</span>
            <span class="pill" style="border-color: rgba(192, 132, 252, 0.4);">app/ai.py / chat.py</span>
          </div>
          <div class="ai-spec-grid">
            <div class="ai-spec-box">
              <h5>다중 LLM 프로바이더</h5>
              <p>Groq (Llama-3.3-70b 초고속 클라우드), Ollama (로컬 폐쇄망), Google Gemini 선택적 스위칭 지원</p>
            </div>
            <div class="ai-spec-box">
              <h5>Security Gateway 도구 호출 통제</h5>
              <p>챗봇 권한은 사용자 권한 종속. Tool 호출 시 RBAC 재검증, 기밀문서 비인가 열람 및 유출 원천 차단</p>
            </div>
            <div class="ai-spec-box">
              <h5>프롬프트 인젝션 방어 & 격리</h5>
              <p>시스템 프롬프트 탈취 시도 방어, 응답 HTML 비실행 이스케이프, 8,000자 상한 및 제어문자 제거</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 데이터 계층 & 격리 스토리지 (우측) -->
    <div class="section-card col-storage">
      <div class="card-header">
        <div class="card-title">
          <div class="icon-box" style="background: rgba(52, 211, 153, 0.15); color: var(--accent-emerald);">🗄️</div>
          데이터 계층 & 권한 격리 (MySQL 8.4)
        </div>
        <span class="tag badge-emerald">Layer 3: Storage & DB</span>
      </div>

      <div class="db-isolation-card">
        <div class="node-title" style="color: var(--accent-emerald);">이중 데이터베이스 계정 권한 분리 (Dual-Privilege)</div>
        <p class="node-desc" style="margin-top: 4px;">
          최소 권한 원칙(Principle of Least Privilege)에 의거하여 기밀 데이터와 일반 비즈니스 데이터를 물리적 DB 권한 수준에서 엄격 격리.
        </p>

        <div class="db-schema-box">
          <div class="db-schema-title">
            <span>🔹 nexus_app (일반 비즈니스 계정)</span>
            <span class="schema-badge-green">SELECT · INSERT · 한정적 UPDATE</span>
          </div>
          <div class="schema-tables">
            users, employees, documents, posts, approvals, tasks, events, reservations, library, chat_messages, messenger_messages
          </div>
        </div>

        <div class="db-schema-box" style="border-color: rgba(251, 113, 133, 0.3);">
          <div class="db-schema-title">
            <span>🔒 nexus_conf (기밀 전용 계정)</span>
            <span class="schema-badge-red">STRICT READ-ONLY (SELECT Only)</span>
          </div>
          <div class="schema-tables">
            confidential_documents, salaries, financial_reports<br/>
            ※ 팀장/관리자 인가 성공 시에만 세션 한정 격리 쿼리 실행
          </div>
        </div>
      </div>

      <div class="file-storage-box">
        <div class="node-title" style="color: var(--accent-blue);">웹루트 외 격리 파일 스토리지</div>
        <p class="node-desc" style="margin-top: 6px;">
          • 저장 경로: <code style="color: var(--accent-cyan);">instance/uploads/</code> (웹 직접 접근 불가)<br/>
          • 파일명: 무작위 UUID 변환 저장으로 Path Traversal 방어<br/>
          • 서빙 정책: Content-Disposition attachment 강제, 이미지/PDF 전용 격리 CSP 서빙
        </p>
      </div>

      <div class="security-triggers-box">
        <h4>🚨 DB 무결성 보호 트리거 (Database Triggers)</h4>
        <ul>
          <li><b>trg_users_pin_insert / update:</b> 최고관리자(admin, hongjh) 계정의 강등, 잠금, 삭제 원천 차단 (Root 계정도 수정 불가)</li>
          <li><b>trg_approvals_self_approve:</b> 기안자 본인의 셀프 결재 승인 DB 레벨 차단</li>
          <li><b>Check Constraints:</b> 결재 문서 종결 불변성, 지출 금액 양수 검증</li>
        </ul>
      </div>
    </div>

  </div>

  <!-- 하단 전체: AI-XDR 보안 관제 & 하이브리드 대응 파이프라인 -->
  <div class="footer-pipeline">
    <div class="pipeline-header">
      <div class="pipeline-title">
        <span>🛡️ NEXUS AI-XDR 실시간 관제 및 하이브리드 능동 대응 파이프라인 (Hybrid SOC Workflow)</span>
      </div>
      <div style="display: flex; gap: 10px;">
        <span class="tag-semi">주간 (08~20시): 반자동 Human-in-the-Loop</span>
        <span class="tag-auto">야간 (20~08시): 완전 자동 Zero-Touch</span>
      </div>
    </div>

    <div class="pipeline-steps">
      <!-- 1단계 -->
      <div class="pipeline-step">
        <span class="step-num">Step 1. Telemetry Ingestion</span>
        <span class="step-name">실시간 텔레메트리 수집</span>
        <div class="step-content">
          • <b>pfSense:</b> 방화벽 허용/차단 패킷 & HAProxy 로그<br/>
          • <b>NEXUS App:</b> 보안 로그(JSON Lines GELF 실시간 전송)<br/>
          • <b>Wazuh Agent:</b> 웹루트 및 핵심 설정 파일 FIM 감시
        </div>
      </div>

      <!-- 2단계 -->
      <div class="pipeline-step">
        <span class="step-num">Step 2. Fast Rule Filtering</span>
        <span class="step-name">룰셋 1차 고속 필터링</span>
        <div class="step-content">
          • <b>Graylog Stream:</b> 룰셋 R1~R12 기반 이벤트 분류<br/>
          • <b>로그인 무차별 대입:</b> 5회 이상 실패 탐지 (R1/R5)<br/>
          • <b>디코이 센서:</b> /.env 및 허니팟 접근자 즉시 선별
        </div>
      </div>

      <!-- 3단계 -->
      <div class="pipeline-step">
        <span class="step-num">Step 3. AI Deep Triage</span>
        <span class="step-name">AI 심층 위협 판정 엔진</span>
        <div class="step-content">
          • <b>Groq / Ollama LLM:</b> 공격 킬체인 및 행위 문맥 분석<br/>
          • <b>정상 오탐 배제:</b> 단순 오타/정상 네트워크 오류 필터링<br/>
          • <b>위협 점수 산출:</b> 0~100 Threat Score 및 대응 권고
        </div>
      </div>

      <!-- 4단계 -->
      <div class="pipeline-step">
        <span class="step-num">Step 4. Hybrid Time Gate</span>
        <span class="step-name">시간대별 대응 모드 분기</span>
        <div class="step-content">
          • <b>주간 (08~20시):</b> Discord 승인형 티켓 발송 (1클릭 승인)<br/>
          • <b>야간/부재 (20~08시):</b> 80점 이상 위협 즉시 자동 격리<br/>
          • <b>n8n SOAR:</b> 상태 추적 및 이벤트 오케스트레이션
        </div>
      </div>

      <!-- 5단계 -->
      <div class="pipeline-step">
        <span class="step-num">Step 5. Multi-Tier Response</span>
        <span class="step-name">다계층 통합 능동 차단</span>
        <div class="step-content">
          • <b>pfSense L3/L4:</b> 방화벽 Alias API로 IP 즉시 블랙홀 차단<br/>
          • <b>NEXUS Web:</b> blocked_ips 등록 및 활성 세션 즉시 만료<br/>
          • <b>Wazuh EDR:</b> 감염/악성 프로세스 강제 종료 및 격리
        </div>
      </div>
    </div>

    <div class="footer-sub">
      <span>Designed by NEXUS WORK Security & Architecture Team (Role A 홍주형)</span>
      <span>Enterprise Architecture Specification v2.0 • Confidential & Defense Ready</span>
      <span>Validated with 1,200+ Automated Tests & Zero Hardening Bypass</span>
    </div>
  </div>

</body>
</html>
"""

temp_html_path = os.path.abspath("temp_arch_diagram.html")
with open(temp_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"HTML written to {temp_html_path}")

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
out_img_path = os.path.abspath("NEXUS_WORK_시스템_아키텍처_구조도.png")
docs_img_path = os.path.abspath(r"docs\NEXUS_WORK_시스템_아키텍처_구조도.png")

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=edge_path)
    page = browser.new_page(viewport={"width": 2400, "height": 1650}, device_scale_factor=1.5)
    page.goto(f"file:///{temp_html_path}")
    page.wait_for_timeout(1000)  # 폰트 렌더링 대기
    page.screenshot(path=out_img_path, full_page=True)
    page.screenshot(path=docs_img_path, full_page=True)
    browser.close()

print(f"Images created:\n- {out_img_path}\n- {docs_img_path}")
