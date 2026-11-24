/* GreenFlag - game phase (Phase 1 / Phase 2), the Phase 2 quiz and the Joker.
   Phase 1: words + definitions on the board, the site gives explanations (works without JavaScript).
   Phase 2: the board is flipped, only the definitions are shown; on the tile page the player types
   the word. Right word on a bonus tile = bonus, on a penalty tile = penalty avoided.
   Joker: won by the first player to finish phase 1, one per game, remembered on this phone. */
(function () {
  "use strict";
  var PHASE_KEY = "greenflag-phase";
  var JOKER_KEY = "greenflag-joker-used";
  var root = document.documentElement;

  function load(key) {
    try { return localStorage.getItem(key); } catch (err) { return null; }
  }
  function save(key, value) {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (err) { /* private mode: kept for this page only */ }
  }
  function setPhase(phase) {
    save(PHASE_KEY, phase);
    root.setAttribute("data-phase", phase);
  }
  function jokerUsed() { return load(JOKER_KEY) === "1"; }
  function showJoker() { root.classList.toggle("joker-used", jokerUsed()); }

  // A link such as contents.html?phase=2 chooses the phase. ?new=1 starts a new game (Joker back).
  var params = new URLSearchParams(location.search);
  if (params.get("new") === "1") save(JOKER_KEY, null);
  var fromUrl = params.get("phase");
  if (fromUrl === "1" || fromUrl === "2") setPhase(fromUrl);
  else root.setAttribute("data-phase", load(PHASE_KEY) || "unset");
  showJoker();

  /* ---------- Tolerant answer check ---------- */
  function normalize(s) {
    s = s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    s = s.replace(/['’`]/g, "").replace(/&/g, " and ").replace(/[^a-z0-9]+/g, " ").trim();
    return s.replace(/^(the|a|an) /, "");
  }
  function distance(a, b) {
    var prev = [], cur, i, j;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      cur = [i];
      for (j = 1; j <= b.length; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[b.length];
  }
  function isCorrect(given, answers) {
    var g = normalize(given), gs = g.replace(/ /g, "");
    if (!g) return false;
    return answers.some(function (ans) {
      var a = normalize(ans), as = a.replace(/ /g, "");
      if (g === a || gs === as) return true;
      // Small typos are fine: 1 letter for words of 5+ letters, 2 letters for 10+.
      var allowed = as.length >= 10 ? 2 : as.length >= 5 ? 1 : 0;
      return allowed > 0 && distance(gs, as) <= allowed;
    });
  }

  /* ---------- Page behaviour ---------- */
  var updateTitle = function () {};

  function init() {
    // Phase buttons and links (home, contents, tile pages)
    Array.prototype.forEach.call(document.querySelectorAll("[data-set-phase]"), function (el) {
      el.addEventListener("click", function (ev) {
        setPhase(el.getAttribute("data-set-phase"));
        if (el.tagName === "BUTTON") { ev.preventDefault(); updateTitle(); }
      });
    });
    // "Give the Joker back" (contents page): new game on this phone
    Array.prototype.forEach.call(document.querySelectorAll("[data-reset-joker]"), function (btn) {
      btn.addEventListener("click", function () { save(JOKER_KEY, null); showJoker(); });
    });

    var quiz = document.getElementById("quiz");
    if (!quiz) return;
    var pageTitle = document.title;
    var form = quiz.querySelector("form");
    var input = quiz.querySelector("input");
    var result = quiz.querySelector(".quiz-result");
    var jokerBtn = quiz.querySelector(".joker-button");
    var answers = JSON.parse(quiz.getAttribute("data-answers"));

    updateTitle = function () {
      // Do not give the answer away in the browser tab.
      var hide = root.getAttribute("data-phase") !== "1" && !root.classList.contains("quiz-done");
      document.title = hide ? quiz.getAttribute("data-tab-title") : pageTitle;
    };
    updateTitle();

    function show(kind) {
      input.disabled = true;
      form.querySelector("button").disabled = true;
      result.className = "quiz-result is-" + kind;
      result.innerHTML = "";
      result.appendChild(quiz.querySelector("template.quiz-" + kind).content.cloneNode(true));
      result.hidden = false;
      root.classList.add("quiz-done");
      quiz.classList.toggle("can-use-joker", kind === "wrong");
      updateTitle();
      result.focus();
    }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (!input.value.trim()) { input.focus(); return; }
      show(isCorrect(input.value, answers) ? "right" : "wrong");
    });

    if (jokerBtn) {
      jokerBtn.addEventListener("click", function () {
        if (jokerUsed()) return;
        save(JOKER_KEY, "1");
        showJoker();
        quiz.classList.remove("can-use-joker");
        show("joker");
      });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
