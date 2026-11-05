import os
import sys
from playwright.sync_api import sync_playwright

html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>NEXUS WORK 전체 공격-탐지-대응 통합 아키텍처 (3대 머신 & 피드백 루프)</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700;800&display=swap');

  :root {
    --bg-main: #060911;
    --bg-card: rgba(13, 19, 35, 0.9);
    --bg-card-inner: rgba(26, 35, 54, 0.78);
    --border-color: rgba(255, 255, 255, 0.09);
    
    --accent-blue: #38BDF8;
    --accent-indigo: #818CF8;
    --accent-purple: #C084FC;
    --accent-emerald: #34D399;
    --accent-amber: #FBBF24;
    --accent-rose: #FB7185;
    --accent-cyan: #22D3EE;

    --ip-pfsense: #38BDF8;
    --ip-portal: #34D399;
    --ip-soc: #C084FC;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  body {
    background-color: var(--bg-main);
    color: #F8FAFC;
    width: 2400px;
    height: 1650px;
    padding: 28px 36px;
    overflow: hidden;
    position: relative;
    background-image: 
      radial-gradient(circle at 12% 10%, rgba(56, 189, 248, 0.09) 0%, transparent 45%),
      radial-gradient(circle at 88% 12%, rgba(192, 132, 252, 0.09) 0%, transparent 45%),
      radial-gradient(circle at 50% 90%, rgba(52, 211, 153, 0.07) 0%, transparent 50%),
      linear-gradient(to right, rgba(255, 255, 255, 0.015) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 100% 100%, 42px 42px, 42px 42px;
  }

  /* 헤더 */
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 18px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 18px;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .brand-logo {
    width: 58px;
    height: 58px;
    background: linear-gradient(135deg, #0284C7, #6366F1);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 24px rgba(2, 132, 199, 0.45);
    font-weight: 900;
    font-size: 26px;
    color: #FFF;
  }

  .header-titles h1 {
    font-size: 29px;
    font-weight: 800;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-titles h1 span.highlight {
    background: linear-gradient(90deg, #38BDF8, #A78BFA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .header-titles p {
    font-size: 14px;
    color: #94A3B8;
    margin-top: 4px;
    display: flex;
    gap: 14px;
  }

  /* 인프라 매핑 상단 배너 */
  .infra-flow-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 7px 14px;
    border-radius: 10px;
  }

  .infra-node {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
  }

  .ip-tag {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 11.5px;
    padding: 3px 8px;
    border-radius: 5px;
  }

  .tag-kali { background: rgba(244, 63, 94, 0.18); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.4); }
  .tag-pfsense { background: rgba(56, 189, 248, 0.18); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); }
  .tag-portal { background: rgba(52, 211, 153, 0.18); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.4); }
  .tag-soc { background: rgba(192, 132, 252, 0.18); color: #C084FC; border: 1px solid rgba(192, 132, 252, 0.4); }

  .flow-arrow {
    color: #64748B;
    font-weight: 800;
    font-size: 13px;
  }

  /* 그리드 컨테이너 */
  .grid-container {
    display: grid;
    grid-template-columns: 500px 1fr 520px;
    gap: 20px;
    height: 1035px;
    margin-bottom: 20px;
  }

  .section-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    backdrop-filter: blur(16px);
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.4);
    position: relative;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-color);
  }

  .card-title {
    font-size: 15.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  .pill {
    background: rgba(255, 255, 255, 0.06);
    color: #94A3B8;
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
  }

  /* 00 외부 공격 & 01 pfSense (좌측) */
  .col-pfsense { border-top: 4px solid var(--ip-pfsense); gap: 14px; }

  .kali-box {
    background: rgba(244, 63, 94, 0.08);
    border: 1px solid rgba(244, 63, 94, 0.35);
    border-radius: 12px;
    padding: 14px;
  }

  .kali-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }

  .kali-title {
    font-size: 14.5px;
    font-weight: 800;
    color: var(--accent-rose);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .kali-desc {
    font-size: 12px;
    color: #CBD5E1;
    line-height: 1.5;
  }

  .kali-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
  }

  .pfsense-box {
    background: var(--bg-card-inner);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 15px;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .pf-rule-row {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px;
  }

  .pf-rule-title {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--accent-cyan);
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .pf-rule-desc {
    font-size: 11.5px;
    color: #94A3B8;
    line-height: 1.45;
  }

  .feedback-alert-pill {
    background: rgba(239, 68, 68, 0.15);
    color: #FB7185;
    border: 1px dashed rgba(239, 68, 68, 0.4);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    line-height: 1.4;
    margin-top: auto;
  }

  /* 02 포털 코어 (중앙) */
  .col-core { border-top: 4px solid var(--ip-portal); gap: 14px; }

  .portal-shield-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }

  .portal-shield-box {
    background: var(--bg-card-inner);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 12px;
    border-left: 3.5px solid var(--accent-emerald);
  }

  .portal-shield-title {
    font-size: 13px;
    font-weight: 800;
    color: #FFF;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }

  .rule-badge {
    font-size: 10.5px;
    font-weight: 800;
    padding: 2px 5px;
    border-radius: 4px;
    background: rgba(52, 211, 153, 0.15);
    color: #34D399;
  }

  .portal-shield-desc {
    font-size: 11.5px;
    color: #94A3B8;
    line-height: 1.45;
  }

  .modules-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    flex-grow: 1;
  }

  .module-card {
    background: var(--bg-card-inner);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 14px;
    display: flex;
    flex-direction: column;
  }

  .module-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .module-title {
    font-size: 14.5px;
    font-weight: 700;
    color: #FFF;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .feature-list {
    list-style: none;
    font-size: 11.8px;
    color: #94A3B8;
    display: flex;
    flex-direction: column;
    gap: 5px;
    line-height: 1.4;
  }

  .feature-list li {
    position: relative;
    padding-left: 12px;
  }

  .feature-list li::before {
    content: "•";
    position: absolute;
    left: 0;
    color: var(--accent-emerald);
    font-weight: bold;
  }

  .ai-special-card {
    grid-column: span 2;
    background: linear-gradient(135deg, rgba(88, 28, 135, 0.25), rgba(30, 58, 138, 0.25));
    border: 1px solid rgba(192, 132, 252, 0.35);
    border-radius: 12px;
    padding: 14px;
  }

  .ai-spec-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
    margin-top: 8px;
  }

  .ai-spec-box {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 10px;
  }

  .ai-spec-box h5 {
    color: var(--accent-purple);
    font-size: 12px;
    margin-bottom: 4px;
    font-weight: 700;
  }

  .ai-spec-box p {
    color: #94A3B8;
    font-size: 11px;
    line-height: 1.4;
  }

  /* 03 데이터 계층 (우측) */
  .col-storage { border-top: 4px solid var(--ip-portal); gap: 14px; }

  .db-isolation-card {
    background: var(--bg-card-inner);
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: 12px;
    padding: 14px;
  }

  .db-schema-box {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px;
    margin-top: 8px;
  }

  .db-schema-title {
    font-size: 12.5px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 5px;
  }

  .schema-tables {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #94A3B8;
    line-height: 1.5;
  }

  .agent-box {
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 12px;
    padding: 12px;
  }

  .security-triggers-box {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 12px;
    padding: 12px;
    margin-top: auto;
  }

  .security-triggers-box h4 {
    color: var(--accent-rose);
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 5px;
  }

  .security-triggers-box ul {
    list-style: none;
    font-size: 11px;
    color: #94A3B8;
    line-height: 1.45;
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

  /* 하단: 03 Graylog + 04 n8n / AI-XDR SOAR (192.168.3.15) */
  .footer-soc-server {
    background: linear-gradient(180deg, rgba(24, 18, 43, 0.95), rgba(13, 10, 26, 0.98));
    border: 1.5px solid rgba(192, 132, 252, 0.4);
    border-top: 4px solid var(--ip-soc);
    border-radius: 16px;
    padding: 18px 22px;
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.45);
  }

  .soc-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }

  .soc-title {
    font-size: 17.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 12px;
    color: #FFF;
  }

  .soc-streams-grid {
    display: grid;
    grid-template-columns: 280px 320px 1fr 1fr 340px;
    gap: 14px;
    position: relative;
  }

  .stream-card {
    background: rgba(30, 27, 54, 0.65);
    border: 1px solid rgba(192, 132, 252, 0.25);
    border-radius: 10px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .stream-card::after {
    content: "➔";
    position: absolute;
    right: -12px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--accent-purple);
    font-size: 16px;
    font-weight: 900;
    z-index: 10;
  }

  .stream-card:last-child::after {
    display: none;
  }

  .stream-tag {
    font-size: 10.5px;
    font-weight: 800;
    color: var(--accent-purple);
    text-transform: uppercase;
    margin-bottom: 3px;
  }

  .stream-name {
    font-size: 13.5px;
    font-weight: 700;
    color: #FFF;
    margin-bottom: 6px;
  }

  .stream-body {
    font-size: 11.5px;
    color: #94A3B8;
    line-height: 1.45;
  }

  .stream-body b {
    color: #E2E8F0;
  }

  .feedback-loop-bar {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .loop-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    color: #CBD5E1;
  }

  .loop-badge {
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 800;
    font-size: 10.5px;
  }

  .lb-1 { background: rgba(56, 189, 248, 0.2); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); }
  .lb-2 { background: rgba(52, 211, 153, 0.2); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.4); }
  .lb-3 { background: rgba(251, 113, 133, 0.2); color: #FB7185; border: 1px solid rgba(251, 113, 133, 0.4); }
</style>
</head>
<body>

  <!-- 헤더 -->
  <header>
    <div class="header-left">
      <div class="brand-logo">NX</div>
      <div class="header-titles">
        <h1><span class="highlight">NEXUS WORK</span> 전체 공격-탐지-대응 통합 아키텍처 (3대 핵심 서버 & 차단 피드백 루프)</h1>
        <p>
          <span>🌐 <b>사내 업무 포털:</b> ERP + 그룹웨어 + 전자결재 + 생성형 AI 어시스턴트</span>
          <span>🛡️ <b>프로젝트:</b> 실전 AI Agent 보안 방어전 (App & DB 완벽 하드닝 및 하이브리드 능동 대응)</span>
        </p>
      </div>
    </div>
    
    <!-- 4단계 인프라 플로우 상단 바 -->
    <div class="infra-flow-bar">
      <div class="infra-node">
        <span class="ip-tag tag-kali">00. 외부 공격 (Kali)</span>
        <span>서른두 가지 실전 공격</span>
      </div>
      <span class="flow-arrow">➔</span>
      <div class="infra-node">
        <span class="ip-tag tag-pfsense">01. 192.168.3.10</span>
        <span><b>경계 방어</b> (이시헌)</span>
      </div>
      <span class="flow-arrow">➔</span>
      <div class="infra-node">
        <span class="ip-tag tag-portal">02. 192.168.3.14</span>
        <span><b>포털·DB 하드닝</b> (홍주형)</span>
      </div>
      <span class="flow-arrow">➔</span>
      <div class="infra-node">
        <span class="ip-tag tag-soc">03/04. 192.168.3.15</span>
        <span><b>통합 관제 & SOAR</b> (김태빈·진혜정)</span>
      </div>
    </div>
  </header>

  <!-- 3열 본문 그리드 -->
  <div class="grid-container">

    <!-- 1구역: 00 외부 공격 (Kali) & 01 pfSense 경계 방어 (이시헌) -->
    <div class="section-card col-pfsense">
      <div class="card-header">
        <div class="card-title">
          <span>🛡️ 00. 외부 공격 & 01. pfSense 경계 방어</span>
        </div>
        <span class="ip-tag tag-pfsense">HOST: 192.168.3.10 (이시헌)</span>
      </div>

      <!-- 00 외부 공격자 박스 -->
      <div class="kali-box">
        <div class="kali-header">
          <span class="kali-title">⚡ 외부 공격자 (Kali Linux) — 실전 침투 테스트</span>
          <span class="pill" style="color: var(--accent-rose); border-color: rgba(244,63,94,0.3);">32종 라이브 공격</span>
        </div>
        <p class="kali-desc">
          공개 도구 18종 + 진혜정 자체 제작 20종 등 총 32종의 실전 공격을 라이브 서버에 직접 실행.
        </p>
        <div class="kali-tags">
          <span class="pill" style="color: #FDA4AF;">R1 로그인 대입</span>
          <span class="pill" style="color: #FDA4AF;">R2 프롬프트 인젝션</span>
          <span class="pill" style="color: #FDA4AF;">R8 디코이 스캔</span>
          <span class="pill" style="color: #FDA4AF;">R9+R10 비인가 접근</span>
        </div>
      </div>

      <!-- 01 pfSense 경계 방어 박스 -->
      <div class="pfsense-box">
        <div style="font-size: 13.5px; font-weight: 800; color: #FFF; margin-bottom: 4px;">
          pfSense L3/L4 방화벽 & HAProxy 게이트웨이
        </div>

        <div class="pf-rule-row">
          <div class="pf-rule-title">
            <span>① GeoBlock · ntopng · pfBlockerNG</span>
            <span class="pill">상시 트래픽 모니터링</span>
          </div>
          <div class="pf-rule-desc">
            국가 단위(GeoIP) 악성 대역 선제 차단 및 실시간 트래픽 가시성 확보.
          </div>
        </div>

        <div class="pf-rule-row">
          <div class="pf-rule-title">
            <span>② XDR_BLOCKED_IPS (URL Table 피드)</span>
            <span class="pill" style="color: var(--accent-emerald);">포털 차단 피드</span>
          </div>
          <div class="pf-rule-desc">
            포털 14번 서버의 <code>blocked_ips</code> URL Table을 주기적으로 폴링해 L3/L4 드롭.
          </div>
        </div>

        <div class="pf-rule-row">
          <div class="pf-rule-title">
            <span>③ NEXUS_AUTO_BLOCK (n8n API 연동)</span>
            <span class="pill" style="color: var(--accent-purple);">n8n 실시간 API</span>
          </div>
          <div class="pf-rule-desc">
            n8n SOAR의 <code>/block</code> API 호출 수신 즉시 해당 IP 방화벽 테이블 등록.
          </div>
        </div>

        <div class="pf-rule-row">
          <div class="pf-rule-title">
            <span>④ Suricata IDS/IPS & HAProxy NAT</span>
            <span class="pill">패턴 탐지 ➔ 15번 전송</span>
          </div>
          <div class="pf-rule-desc">
            WAN:5070 패킷을 안전하게 LAN 포털(192.168.3.14:5070)로 포워딩. Suricata Alert 생성.
          </div>
        </div>

        <div class="feedback-alert-pill">
          ※ GeoBlock · XDR_BLOCKED_IPS · NEXUS_AUTO_BLOCK 3개 중 하나라도 걸리면 <b>즉시 Drop (로그만 보존)</b>
        </div>
      </div>
    </div>

    <!-- 2구역: 02 LAN 내부 — 포털 서버 방어선 (홍주형) -->
    <div class="section-card col-core">
      <div class="card-header">
        <div class="card-title">
          <span>⚡ 02. LAN 내부 포털 서버 방어선 (Flask + Waitress WSGI)</span>
        </div>
        <span class="ip-tag tag-portal">HOST: 192.168.3.14 (홍주형 / 포트 5070)</span>
      </div>

      <!-- 상단 4대 방어 모듈 (R1, R2, R8, R9+R10) -->
      <div class="portal-shield-grid">
        <div class="portal-shield-box">
          <div class="portal-shield-title">
            <span>로그인 · 세션</span>
            <span class="rule-badge">R1 검증</span>
          </div>
          <div class="portal-shield-desc">
            5회 실패 시 15분 즉시 잠금<br/>
            RBAC · IDOR · BOLA 철저 차단
          </div>
        </div>

        <div class="portal-shield-box">
          <div class="portal-shield-title">
            <span>AI 에이전트 · 챗봇</span>
            <span class="rule-badge">R2 검증</span>
          </div>
          <div class="portal-shield-desc">
            직접 Prompt Injection 즉시 차단<br/>
            AI 4중 캐스케이드 판정 0.5초
          </div>
        </div>

        <div class="portal-shield-box">
          <div class="portal-shield-title">
            <span>디코이 허니팟</span>
            <span class="rule-badge">R8 검증</span>
          </div>
          <div class="portal-shield-desc">
            /.env, /.git/config 미끼 경로<br/>
            접근 즉시 제 IP 등록 및 차단
          </div>
        </div>

        <div class="portal-shield-box">
          <div class="portal-shield-title">
            <span>관리자 · 기밀 경로</span>
            <span class="rule-badge">R9+R10 검증</span>
          </div>
          <div class="portal-shield-desc">
            /admin, /confidential, /finance<br/>
            비인가 접근 403 고정 차단
          </div>
        </div>
      </div>

      <!-- 핵심 비즈니스 모듈 -->
      <div class="modules-grid">
        <div class="module-card">
          <div class="module-header">
            <span class="module-title">📋 전자결재 엔진 (Approvals)</span>
            <span class="pill">app/approvals.py</span>
          </div>
          <ul class="feature-list">
            <li>최대 5단계 순차 결재선 및 결재 의견/반려 사유 강제</li>
            <li>지출결의서: 단가×수량 서버 재연산 + 일금 한글 금액 위변조 방지</li>
            <li>공문 양식 출력(@media print), 결재자별 단계별 첨부파일 보존</li>
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
            <li>인사관리: 사원/대리/과장/팀장/관리자 5단계 RBAC 세부 인가 통제</li>
            <li>실시간 침해 대응: blocked_ips 기반 즉시 403 차단 미들웨어</li>
          </ul>
        </div>

        <div class="module-card">
          <div class="module-header">
            <span class="module-title">💼 ERP & 업무·자원 관리 (Work & ERP)</span>
            <span class="pill">app/erp.py / work.py</span>
          </div>
          <ul class="feature-list">
            <li>업무 관리(할일/진행/완료), 칸반 상태 전이, 프로젝트 진척률</li>
            <li>월간 캘린더: 개인(비공개 관리자 열람불가)/팀/전사 일정 통제</li>
            <li>30분 단위 회의실/비품 예약: 자원 행 락을 통한 동시성 중복 방지</li>
            <li>자료실: 폴더형 4단계 구조, 파일 버전 이력 및 다운로드 전용 서빙</li>
          </ul>
        </div>

        <div class="module-card">
          <div class="module-header">
            <span class="module-title">🔒 시스템 관리 & 보안 대시보드</span>
            <span class="pill">app/admin.py / audit.py</span>
          </div>
          <ul class="feature-list">
            <li>사용자 생성 시 임시 비밀번호 1회 표시 (DB 해시만 저장)</li>
            <li>보안 대시보드: SVG 시계열 차트, 위협 지표 8종, IP/계정 랭킹</li>
            <li>감사 로그 스트림 + CSV 수식 주입 방어 내보내기</li>
            <li>최고관리자(admin, hongjh) DB 트리거 영구 고정 (강등 불가)</li>
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
              <h5>다중 LLM 4중 캐스케이드 (0.5초)</h5>
              <p>Groq (Llama-3.3-70b 클라우드), Ollama (폐쇄망), Gemini, 내장 룰 엔진 자동 폴백</p>
            </div>
            <div class="ai-spec-box">
              <h5>Security Gateway 도구 호출 통제</h5>
              <p>챗봇 권한은 사용자 권한 종속. Tool 호출 시 RBAC 재검증으로 기밀문서 비인가 유출 차단</p>
            </div>
            <div class="ai-spec-box">
              <h5>프롬프트 인젝션 방어 & 격리</h5>
              <p>시스템 프롬프트 탈취 방어, 응답 HTML 비실행 이스케이프, 8,000자 상한 필터링</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3구역: 데이터 계층 (MySQL 8.4) & Wazuh Agent -->
    <div class="section-card col-storage">
      <div class="card-header">
        <div class="card-title">
          <span>🗄️ 호스트 데이터 계층 (MySQL 8.4)</span>
        </div>
        <span class="ip-tag tag-portal">HOST: 192.168.3.14 (포트 3307)</span>
      </div>

      <div class="db-isolation-card">
        <div class="node-title" style="color: var(--accent-emerald); font-size: 13.5px; font-weight: 700;">이중 DB 계정 권한 물리적 분리 (Dual-Privilege)</div>
        
        <div class="db-schema-box">
          <div class="db-schema-title">
            <span>🔹 nexus_app (일반 비즈니스 계정)</span>
            <span class="pill" style="color: var(--accent-emerald);">한정적 UPDATE</span>
          </div>
          <div class="schema-tables">
            users, employees, documents, posts, approvals, tasks, events, reservations, library, chat_messages
          </div>
        </div>

        <div class="db-schema-box" style="border-color: rgba(251, 113, 133, 0.35);">
          <div class="db-schema-title">
            <span>🔒 nexus_conf (기밀 전용 계정)</span>
            <span class="pill" style="color: var(--accent-rose);">STRICT READ-ONLY</span>
          </div>
          <div class="schema-tables">
            confidential_documents, salaries, financial_reports<br/>
            ※ 팀장/관리자 인가 성공 시에만 세션 한정 격리 쿼리
          </div>
        </div>
      </div>

      <!-- Wazuh Agent 박스 -->
      <div class="agent-box">
        <div style="font-size: 13px; font-weight: 700; color: var(--accent-blue); margin-bottom: 4px;">
          📡 Wazuh Agent (nexus-board-14)
        </div>
        <p style="font-size: 11.5px; color: #94A3B8; line-height: 1.45;">
          • 14번 호스트의 <code>app/</code>, <code>scripts/</code>, <code>.env</code> 파일 무결성(FIM) 실시간 감시<br/>
          • <code>logs/security.jsonl</code> 보안 이벤트를 15번 매니저로 암호화 전송 (TCP 1514)
        </p>
      </div>

      <div class="security-triggers-box">
        <h4>🚨 DB 무결성 보호 트리거 (Database Triggers)</h4>
        <ul>
          <li><b>trg_users_pin_insert / update:</b> 최고관리자(admin, hongjh) 강등/잠금/삭제 차단</li>
          <li><b>trg_approvals_self_approve:</b> 기안자 셀프 결재 승인 DB 레벨 차단</li>
          <li><b>Check Constraints:</b> 결재 상태 불변성, 지출 금액 양수 검증</li>
        </ul>
      </div>
    </div>

  </div>

  <!-- 하단 전체: 03 통합 탐지 (Graylog) & 04 사건 정리 · 분석 · 대응 (n8n & AI-XDR) -->
  <div class="footer-soc-server">
    <div class="soc-header">
      <div class="soc-title">
        <span>🛡️ 03. 통합 탐지 (Graylog) & 04. 사건 정리 · 분석 · 대응 (n8n SOAR & AI-XDR)</span>
        <span class="ip-tag tag-soc">HOST: 192.168.3.15 (김태빈 담당 · 진혜정 n8n 기반 구축)</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <span class="pill" style="color: var(--accent-amber); border-color: rgba(251, 191, 36, 0.4);">주간: Discord 승인형 반자동</span>
        <span class="pill" style="color: var(--accent-rose); border-color: rgba(239, 68, 68, 0.4);">야간: 80점+ 완전 자동 격리</span>
      </div>
    </div>

    <!-- 5단계 가로 스트림 흐름 -->
    <div class="soc-streams-grid">
      <!-- 1. 수집 Input -->
      <div class="stream-card">
        <span class="stream-tag">Input & Parsing</span>
        <span class="stream-name">1. Graylog Input</span>
        <div class="stream-body">
          • <b>수집 소스:</b> Wazuh FIM, Suricata 로그, 포털 security.jsonl<br/>
          • <b>프로토콜:</b> GELF 12201 · Syslog 5140<br/>
          • <b>필드 정규화:</b> ts ➔ timestamp 통일
        </div>
      </div>

      <!-- 2. 3대 Stream 분기 -->
      <div class="stream-card">
        <span class="stream-tag">Stream Routing</span>
        <span class="stream-name">2. 3개 Stream 분기</span>
        <div class="stream-body">
          • <b>NEXUS_AUTH:</b> R1 · R5 · R6 · R7<br/>
          • <b>NEXUS_AI_SECURITY:</b> R2 · R3 · R4 · R11 · R12<br/>
          • <b>NEXUS_WEB:</b> R8 · R9 · R10 · FIM
        </div>
      </div>

      <!-- 3. R1~R12 Event & 증적 -->
      <div class="stream-card">
        <span class="stream-tag">Detection Rules</span>
        <span class="stream-name">3. R1~R12 이벤트 & 증적</span>
        <div class="stream-body">
          • <b>임계치 탐지:</b> 예) R8 60초 내 같은 IP 404 ≥30회<br/>
          • <b>Webhook 발송:</b> Graylog Event ➔ n8n POST<br/>
          • <b>증적 관리:</b> Positive/Negative 구분 기록, 비밀번호·토큰·원문 미기록 (pattern_id만)
        </div>
      </div>

      <!-- 4. AI-XDR & 승인 -->
      <div class="stream-card">
        <span class="stream-tag">AI Triage & Gate</span>
        <span class="stream-name">4. AI-XDR (Groq) & 승인</span>
        <div class="stream-body">
          • <b>n8n (SOAR):</b> 알림 자동 병합 & Ticket 연결<br/>
          • <b>AI-XDR:</b> 사건 맥락 분석, 위험도 · 근거 산출<br/>
          • <b>관리자 승인:</b> 정상 사용자 오탐 방지 (Human-in-the-Loop)
        </div>
      </div>

      <!-- 5. 상황판 & 능동 차단 -->
      <div class="stream-card">
        <span class="stream-tag">Enforcement & SOC</span>
        <span class="stream-name">5. 상황판 & 다계층 차단</span>
        <div class="stream-body">
          • <b>실시간 상황판:</b> 인시던트 현황 & 이력 표출<br/>
          • <b>① pfSense:</b> NEXUS_AUTO_BLOCK IP 드롭<br/>
          • <b>② 포털 웹:</b> blocked_ips 등록 & 세션 즉시 만료<br/>
          • <b>③ 호스트:</b> Wazuh FIM 프로세스 격리
        </div>
      </div>
    </div>

    <!-- 하단 피드백 루프 요약 바 -->
    <div class="feedback-loop-bar">
      <div class="loop-item">
        <span class="loop-badge lb-1">① n8n 자동 차단</span>
        <span>n8n /block API ➔ pfSense NEXUS_AUTO_BLOCK 테이블 즉시 등록</span>
      </div>
      <div class="loop-item">
        <span class="loop-badge lb-2">② 포털 차단 피드</span>
        <span>포털 14번 blocked_ips ➔ pfSense XDR_BLOCKED_IPS (URL Table 주기적 수신)</span>
      </div>
      <div class="loop-item">
        <span class="loop-badge lb-3">③ 포털 내부 세션 격리</span>
        <span>n8n DB/API 연동 ➔ 14번 포털 활성 세션 즉시 만료 및 로그인 잠금 집행</span>
      </div>
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
docs_html_path = os.path.abspath(r"docs\NEXUS_WORK_시스템_아키텍처_구조도.html")

with open(docs_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=edge_path)
    page = browser.new_page(viewport={"width": 2400, "height": 1650}, device_scale_factor=1.5)
    page.goto(f"file:///{temp_html_path}")
    page.wait_for_timeout(1000)
    page.screenshot(path=out_img_path, full_page=True)
    page.screenshot(path=docs_img_path, full_page=True)
    browser.close()

if os.path.exists(temp_html_path):
    os.remove(temp_html_path)

print(f"Images & HTML updated successfully:\n- {out_img_path}\n- {docs_img_path}\n- {docs_html_path}")
