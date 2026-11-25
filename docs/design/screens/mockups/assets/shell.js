// 공통 앱 틀(타이틀바 · 상단 바 · 사이드바)을 그린다.  화면 정의서: docs/design/screens/README.md "공통 레이아웃"
// 사용: <div class="win" data-title="Klover" data-nav="inbox" data-search="..."> ... </div>
(function () {
  const win = document.querySelector(".win");
  if (!win) return;
  const nav = win.dataset.nav || "";
  const noSidebar = win.dataset.nosidebar === "1";
  const searchText = win.dataset.search;
  const empty = win.dataset.empty === "1";
  const titlebar = `
  <div class="titlebar"><img src="../../brand/klover-app-icon.svg" alt=""><span>${win.dataset.title || "Klover"}</span><span class="sp"></span>
    <span class="wc"><svg viewBox="0 0 10 10"><path d="M0 5h10" stroke="currentColor"/></svg></span>
    <span class="wc"><svg viewBox="0 0 10 10"><rect x=".5" y=".5" width="9" height="9" fill="none" stroke="currentColor"/></svg></span>
    <span class="wc"><svg viewBox="0 0 10 10"><path d="M0 0l10 10M10 0L0 10" stroke="currentColor"/></svg></span></div>`;
  const topbar = win.dataset.notop === "1" ? "" : `
  <div class="topbar">
    <div class="brand"><img src="../../brand/klover-logo.svg" alt="Klover"></div>
    <div class="search ${searchText ? "focus" : ""}"><i data-i="search"></i><span>${searchText || "무엇이든 물어보세요. 예: 지난주 영업기획팀이 보낸 예산 관련 메일"}</span><kbd>Ctrl K</kbd></div>
    <div class="right">
      <span class="iconbtn"><i data-i="bell"></i>${empty ? "" : `<span class="badge">3</span>`}</span>
      <span>hong.gildong@gmail.com</span><span class="avatar">홍</span>
    </div>
  </div>`;
  const item = (key, icon, label, cnt) =>
    `<div class="nav ${nav === key ? "on" : ""}"><i data-i="${icon}"></i>${label}${cnt !== undefined && !empty ? `<span class="cnt">${cnt}</span>` : ""}</div>`;
  const cat = (key, d, label, cnt) =>
    `<div class="nav ${nav === key ? "on" : ""}"><span class="dot ${d}"></span>${label}${empty ? "" : `<span class="cnt">${cnt}</span>`}</div>`;
  const sidebar = noSidebar ? "" : `
  <aside class="sidebar">
    <div class="newbtn"><span class="btn btn-primary btn-block"><i data-i="pen"></i>새 메일</span></div>
    ${item("inbox", "inbox", "받은편지함", 59)}
    ${item("sent", "send", "보낸편지함")}
    ${item("draft", "file", "임시보관함", 2)}
    ${item("archive", "archive", "보관함", 312)}
    ${item("spam", "ban", "스팸·휴지통")}
    <div class="navlabel">스마트 보기</div>
    ${item("reply", "reply", "회신 필요", 7)}
    ${item("due", "clock", "마감 임박", 3)}
    ${item("todo", "todo", "할 일", 5)}
    <div class="navlabel">AI 카테고리</div>
    ${cat("c1", "d-work", "업무 요청", 12)}
    ${cat("c2", "d-meeting", "회의·일정", 5)}
    ${cat("c3", "d-approval", "결재·승인", 3)}
    ${cat("c4", "d-report", "보고·공유", 8)}
    ${cat("c5", "d-notice", "공지", 4)}
    ${cat("c6", "d-external", "외부·고객", 6)}
    ${cat("c7", "d-news", "뉴스레터·광고", 21)}
    <div class="navlabel">도구</div>
    ${item("report", "report", "주간 보고")}
    ${item("settings", "settings", "설정")}
  </aside>`;
  const content = win.innerHTML;
  win.innerHTML = titlebar + topbar + `<div class="body">${sidebar}${content}</div>`;
})();
