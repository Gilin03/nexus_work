/**
 * NEXUS WORK — AI-XDR 2차 판정 센터 클라이언트 스크립트
 * CSP(script-src 'self')를 준수하여 인라인 이벤트 없이 독립 스크립트로 동작합니다.
 */

(function () {
  'use strict';

  var currentFilter = 'all';
  var isLivePaused = false;
  var liveTimer = null;

  function getCsrfToken() {
    var container = document.getElementById('xdrContainer');
    if (container && container.dataset.csrf) {
      return container.dataset.csrf;
    }
    var input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  function applyFilter() {
    var rows = document.querySelectorAll('.xdr-row');
    rows.forEach(function (row) {
      if (currentFilter === 'all') {
        row.style.display = '';
      } else if (currentFilter === 'PENDING') {
        row.style.display = (row.dataset.status === 'PENDING') ? '' : 'none';
      } else {
        row.style.display = (row.dataset.verdict === currentFilter) ? '' : 'none';
      }
    });
  }

  function updateCounts() {
    var rows = Array.from(document.querySelectorAll('.xdr-row'));
    var allCount = rows.length;
    var malCount = rows.filter(function (r) { return r.dataset.verdict === 'MALICIOUS'; }).length;
    var susCount = rows.filter(function (r) { return r.dataset.verdict === 'SUSPICIOUS'; }).length;
    var penCount = rows.filter(function (r) { return r.dataset.status === 'PENDING'; }).length;

    var elAll = document.getElementById('cnt-all');
    var elMal = document.getElementById('cnt-malicious');
    var elSus = document.getElementById('cnt-suspicious');
    var elPen = document.getElementById('cnt-pending');

    if (elAll) elAll.textContent = allCount;
    if (elMal) elMal.textContent = malCount;
    if (elSus) elSus.textContent = susCount;
    if (elPen) elPen.textContent = penCount;
  }

  function filterXDR(type, targetBtn) {
    currentFilter = type;
    document.querySelectorAll('.filter-btn').forEach(function (b) {
      b.classList.remove('active');
    });
    if (targetBtn) {
      targetBtn.classList.add('active');
    }
    applyFilter();
  }

  function renderAssessmentRow(a) {
    var timeStr = (a.last_seen_kst || a.first_seen_kst || '').replace(' KST', '');
    var statusBadge = (a.status === 'PENDING')
      ? '<span class="xdr-tag tag-pending">⏳ 승인 대기</span>'
      : '<span class="xdr-tag tag-done">✓ ' + (a.status || '') + '</span>';

    var ticketStr = '';
    if (a.ticket_ids && a.ticket_ids.length) {
      ticketStr = '#' + a.ticket_ids.join(', ');
    } else if (a.incident_ticket_id) {
      ticketStr = '#NX-DB-' + String(a.incident_ticket_id).padStart(6, '0');
    }

    var userTags = '';
    if (a.user_names && a.user_names.length) {
      userTags = a.user_names.map(function (u) {
        return '<span class="xdr-tag tag-user">👤 ' + u + '</span>';
      }).join(' ');
    } else {
      userTags = '<span style="font-size: 0.78rem; color: #94a3b8;">(미인증 세션)</span>';
    }

    var ruleTags = (a.rule_ids || []).map(function (rid) {
      return '<span class="xdr-tag tag-rule">' + rid + '</span>';
    }).join(' ');

    var verdictTag = '';
    if (a.verdict === 'MALICIOUS') verdictTag = '<span class="xdr-tag tag-malicious">🚨 MALICIOUS (악성 침해)</span>';
    else if (a.verdict === 'SUSPICIOUS') verdictTag = '<span class="xdr-tag tag-suspicious">⚠️ SUSPICIOUS (의심)</span>';
    else if (a.verdict === 'BENIGN') verdictTag = '<span class="xdr-tag tag-benign">✅ BENIGN (정상 활동)</span>';
    else verdictTag = '<span class="xdr-tag tag-review">🔍 REVIEW (심층 검토)</span>';

    var score = a.threat_score || 0;
    var fillClass = (score >= 70) ? 'fill-high' : ((score >= 40) ? 'fill-mid' : 'fill-low');
    var scoreColor = (score >= 70) ? '#dc2626' : ((score >= 40) ? '#d97706' : '#16a34a');
    var confPct = Math.round((a.confidence || 0) * 100);

    var recHtml = '';
    if (a.recommended_actions && a.recommended_actions.length) {
      recHtml = a.recommended_actions.map(function (act) {
        if (act === 'block_ip') return '<span class="rec-chip">🚫 권고: IP 즉시 차단</span>';
        if (act === 'notify_only') return '<span class="rec-chip" style="background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe;">📢 권고: 관제 알림</span>';
        return '<span class="xdr-tag" style="background:#f8fafc; color:#475569;">권고: ' + act + '</span>';
      }).join(' ');
    }

    var autoCand = (a.response_result && a.response_result.auto_candidate)
      ? '<span class="xdr-tag" style="background:#fef2f2; color:#b91c1c; border: 1px solid #fecaca; font-size: 0.72rem;">⚡ 자동 차단 후보</span>'
      : '';

    var reasonCardClass = (a.verdict === 'MALICIOUS') ? 'is-malicious' : ((a.verdict === 'SUSPICIOUS') ? 'is-suspicious' : 'is-benign');

    var csrfToken = getCsrfToken();
    var actionHtml = '';
    if (a.status === 'PENDING') {
      var decideUrl = '/admin/xdr/assessments/' + encodeURIComponent(a.assessment_id) + '/decision';
      var blockBtn = (a.recommended_actions && a.recommended_actions.includes('block_ip'))
        ? '<button class="btn-xdr btn-xdr-block" name="decision" value="' + 'APPROVED_' + 'BLOCK_IP"' + (a.block_approval_error ? ' disabled title="' + a.block_approval_error + '"' : '') + '>🚫 IP 차단 승인</button>'
        : '';
      var rejectLabel = (a.recommended_actions && a.recommended_actions.includes('block_ip'))
        ? 'IP 차단 거부'
        : '평가 거부';

      actionHtml = '<form method="post" action="' + decideUrl + '" class="xdr-actions">' +
        '<input type="hidden" name="csrf_token" value="' + csrfToken + '">' +
        blockBtn +
        '<button class="btn-xdr btn-xdr-reject" name="decision" value="REJECTED">' + rejectLabel + '</button>' +
        '<button class="btn-xdr btn-xdr-fp" name="decision" value="FALSE_POSITIVE">🛡️ 오탐(False Positive) 예외</button>' +
        (a.block_approval_error ? '<div style="font-size: 0.72rem; color: #dc2626; margin-top: 2px;">⚠️ ' + a.block_approval_error + '</div>' : '') +
        '</form>';
    } else {
      actionHtml = '<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; font-size: 0.78rem;">' +
        '<div style="font-weight: 700; color: #334155;">✓ 처리 완료</div>' +
        '<div style="font-size: 0.72rem; color: #94a3b8; margin-top: 3px;">' + (a.decided_at || '자동/승인 처리됨') + '</div>' +
        '</div>';
    }

    var tr = document.createElement('tr');
    tr.className = 'xdr-row row-new-flash';
    tr.id = 'row-' + a.assessment_id;
    tr.dataset.id = a.assessment_id;
    tr.dataset.verdict = a.verdict || '';
    tr.dataset.status = a.status || '';

    tr.innerHTML =
      '<td class="col-time">' +
        '<div style="font-weight: 700; color: #0f172a; font-size: 0.84rem;">' + timeStr + '</div>' +
        '<div style="margin-top: 6px;">' + statusBadge + '</div>' +
        '<div style="margin-top: 6px; font-size: 0.74rem; color: #94a3b8; font-family: monospace;">' + ticketStr + '</div>' +
      '</td>' +
      '<td class="col-target">' +
        '<div style="font-family: ui-monospace, Consolas, monospace; font-weight: 800; color: #0f172a; font-size: 0.92rem; letter-spacing: -0.3px;">' + (a.src_ip || 'IP 미식별') + '</div>' +
        '<div style="margin-top: 6px;">' + userTags + '</div>' +
      '</td>' +
      '<td class="col-rule">' +
        '<div style="display: flex; gap: 4px; flex-wrap: wrap;">' + ruleTags + '</div>' +
        '<div style="margin-top: 6px; font-size: 0.82rem; font-weight: 600; color: #1e293b;">' + (a.event_types || []).join(', ') + '</div>' +
        '<div style="font-size: 0.74rem; color: #64748b; margin-top: 3px;">이벤트 누적 <strong>' + (a.event_count || 1) + '</strong>건</div>' +
      '</td>' +
      '<td class="col-ai">' +
        '<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">' +
          verdictTag +
          '<span class="threat-gauge">' +
            '<span class="gauge-track"><span class="gauge-fill ' + fillClass + '" style="width: ' + score + '%;"></span></span>' +
            '<span style="color: ' + scoreColor + ';">' + score + '점</span>' +
          '</span>' +
          '<span style="font-size: 0.76rem; color: #64748b;">(신뢰도 ' + confPct + '%)</span>' +
          recHtml + autoCand +
        '</div>' +
        '<div class="ai-reason-card ' + reasonCardClass + '">' +
          '<strong>💡 AI 판정 근거:</strong> ' + (a.reasoning || '') +
        '</div>' +
        '<div style="font-size: 0.72rem; color: #94a3b8; margin-top: 5px;">' +
          '정책 모드: <code>' + (a.policy_mode || '') + '</code> · 사유: ' + (a.policy_reason || '') +
        '</div>' +
      '</td>' +
      '<td class="col-action">' + actionHtml + '</td>';

    return tr;
  }

  function pollXDRFeed() {
    if (isLivePaused) return;

    fetch('/admin/xdr/feed?limit=50', { credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.assessments) return;

        var tbody = document.getElementById('xdrTableBody');
        var emptyRow = document.getElementById('emptyRow');
        var items = data.assessments;

        var existingIds = new Set();
        document.querySelectorAll('.xdr-row').forEach(function (r) {
          existingIds.add(r.dataset.id);
        });

        var newlyAdded = 0;
        for (var i = items.length - 1; i >= 0; i--) {
          var item = items[i];
          if (!existingIds.has(item.assessment_id)) {
            if (emptyRow) { emptyRow.remove(); emptyRow = null; }
            var newRow = renderAssessmentRow(item);
            tbody.insertBefore(newRow, tbody.firstChild);
            existingIds.add(item.assessment_id);
            newlyAdded++;
          } else {
            var row = document.getElementById('row-' + item.assessment_id);
            if (row && (row.dataset.status !== item.status || row.dataset.verdict !== item.verdict)) {
              row.dataset.status = item.status;
              row.dataset.verdict = item.verdict;
              var updatedRow = renderAssessmentRow(item);
              updatedRow.classList.remove('row-new-flash');
              row.replaceWith(updatedRow);
            }
          }
        }

        if (newlyAdded > 0) {
          updateCounts();
          applyFilter();
        }
      })
      .catch(function (err) {
        console.warn('XDR feed polling error:', err);
      });
  }

  // 초기화 및 이벤트 리스너 등록
  document.addEventListener('DOMContentLoaded', function () {
    // 1. 화면 가로 전폭 강제 보장
    var mainEl = document.querySelector('.main');
    if (mainEl) {
      mainEl.style.maxWidth = '100%';
      mainEl.style.width = '100%';
      mainEl.style.boxSizing = 'border-box';
      mainEl.style.overflowX = 'hidden';
    }

    // 2. 빠른 필터 버튼 클릭 리스너 등록 (CSP onclick 대체)
    var filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var filterType = btn.getAttribute('data-filter') || 'all';
        filterXDR(filterType, btn);
      });
    });

    // 3. 실시간 토글 버튼
    var toggleBtn = document.getElementById('xdr-toggle-btn');
    var liveBadge = document.getElementById('xdr-live-status');
    var liveText = document.getElementById('xdr-live-text');

    if (toggleBtn) {
      toggleBtn.addEventListener('click', function (e) {
        e.preventDefault();
        isLivePaused = !isLivePaused;
        if (isLivePaused) {
          if (liveBadge) liveBadge.classList.add('is-paused');
          if (liveText) liveText.textContent = '실시간 감시 일시정지';
          toggleBtn.textContent = '▶ 재개';
        } else {
          if (liveBadge) liveBadge.classList.remove('is-paused');
          if (liveText) liveText.textContent = '실시간 감시 중 (3초)';
          toggleBtn.textContent = '⏸ 일시정지';
          pollXDRFeed();
        }
      });
    }

    // 4. 3초 주기 자동 감시 타이머 가동
    liveTimer = setInterval(pollXDRFeed, 3000);
  });
})();
