/* GreenFlag - game level (Easy / Hard) and the Hard level quiz.
   Easy: word + definition on the board, the site gives explanations (works without JavaScript).
   Hard: only the definition is on the board; on the tile page the player types the word. */
(function () {
  "use strict";
  var KEY = "greenflag-level";
  var root = document.documentElement;

  function getLevel() {
    try { return localStorage.getItem(KEY); } catch (err) { return null; }
  }
  function setLevel(level) {
    try { localStorage.setItem(KEY, level); } catch (err) { /* private mode: level kept for this page only */ }
    root.setAttribute("data-level", level);
  }

  // A link such as contents.html?level=hard chooses the level.
  var fromUrl = new URLSearchParams(location.search).get("level");
  if (fromUrl === "easy" || fromUrl === "hard") setLevel(fromUrl);
  else root.setAttribute("data-level", getLevel() || "unset");

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
  function init() {
    // Level switch buttons (home, contents, tile pages)
    Array.prototype.forEach.call(document.querySelectorAll("[data-set-level]"), function (btn) {
      btn.addEventListener("click", function (ev) {
        var level = btn.getAttribute("data-set-level");
        setLevel(level);
        if (btn.tagName === "BUTTON") { ev.preventDefault(); resetQuiz(); }
      });
    });

    var quiz = document.getElementById("quiz");
    if (!quiz) return;
    var pageTitle = document.title;
    var form = quiz.querySelector("form");
    var input = quiz.querySelector("input");
    var result = quiz.querySelector(".quiz-result");
    var answers = JSON.parse(quiz.getAttribute("data-answers"));

    function hideTitle() {
      // Do not give the answer away in the browser tab.
      if (root.getAttribute("data-level") !== "easy" && !root.classList.contains("quiz-done")) {
        document.title = quiz.getAttribute("data-tab-title");
      } else {
        document.title = pageTitle;
      }
    }
    window.resetQuizTitle = hideTitle;
    hideTitle();

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (!input.value.trim()) { input.focus(); return; }
      var ok = isCorrect(input.value, answers);
      input.disabled = true;
      form.querySelector("button").disabled = true;
      result.className = "quiz-result " + (ok ? "is-right" : "is-wrong");
      var tpl = quiz.querySelector(ok ? "template.quiz-right" : "template.quiz-wrong");
      result.innerHTML = "";
      result.appendChild(tpl.content.cloneNode(true));
      result.hidden = false;
      root.classList.add("quiz-done");
      hideTitle();
      result.focus();
    });
  }
  function resetQuiz() {
    if (window.resetQuizTitle) window.resetQuizTitle();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
