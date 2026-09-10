const $ = (selector) => document.querySelector(selector);
const API_BASE = (window.FAIRSEAT_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);
let applicants = [];
let activeId = null;
let currentInterview = null;

const toast = (message) => {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 3000);
};
const api = async (url, options = {}) => {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Something went wrong");
  return data;
};

function switchView(view) {
  document
    .querySelectorAll(".tab")
    .forEach((tab) =>
      tab.classList.toggle("active", tab.dataset.view === view),
    );
  document
    .querySelectorAll(".view")
    .forEach((section) =>
      section.classList.toggle("active", section.id === view),
    );
  if (view === "interview") refreshApplicants();
}
document
  .querySelectorAll(".tab")
  .forEach((tab) =>
    tab.addEventListener("click", () => switchView(tab.dataset.view)),
  );
document
  .querySelectorAll("[data-go]")
  .forEach((button) =>
    button.addEventListener("click", () => switchView(button.dataset.go)),
  );

async function refreshApplicants() {
  applicants = await api("/api/applicants");
  const picker = $("#candidate-picker");
  picker.innerHTML = applicants
    .map(
      (person) =>
        `<button class="candidate ${person.id === activeId ? "selected" : ""}" data-id="${person.id}">${person.name}<small>${person.interview_complete ? "Interview complete" : person.skill}</small></button>`,
    )
    .join("");
  picker
    .querySelectorAll(".candidate")
    .forEach((button) =>
      button.addEventListener("click", () =>
        selectApplicant(button.dataset.id),
      ),
    );
  if (!activeId || !applicants.some((person) => person.id === activeId))
    showInterviewEmpty();
}

function showInterviewEmpty() {
  $("#interview-empty").classList.remove("hidden");
  $("#interview-card").classList.add("hidden");
  $("#complete-card").classList.add("hidden");
}
const escapeHtml = (text) =>
  text.replace(
    /[&<>'"]/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        char
      ],
  );
function message(role, text) {
  const isUser = role === "user";
  return `<div class="message ${isUser ? "you" : ""}">${!isUser ? '<div class="interviewer-avatar">f</div>' : ""}<div class="message-copy"><div class="message-label">${isUser ? "YOU" : "FAIRSEAT"}</div><div class="bubble">${escapeHtml(text)}</div></div></div>`;
}
function showQuestion(data) {
  currentInterview = data;
  $("#interview-empty").classList.add("hidden");
  $("#complete-card").classList.add("hidden");
  $("#interview-card").classList.remove("hidden");
  $("#answer-form").classList.remove("hidden");
  $("#model-status").innerHTML = data.ai_assisted
    ? "<i></i> AI interview assistant"
    : data.ai_available
      ? "<i></i> AI ready for next turn"
      : "<i></i> Guided & evidence-led";
  $("#question-count").textContent =
    `${String(data.answered + 1).padStart(2, "0")} / ${String(data.total).padStart(2, "0")}`;
  $("#chat-thread").innerHTML = (data.messages || [])
    .map((entry) => message(entry.role, entry.content))
    .join("");
  $("#chat-thread").scrollTop = $("#chat-thread").scrollHeight;
  $("#answer").value = "";
  $("#answer").focus();
}
function showComplete(data) {
  currentInterview = data;
  $("#interview-empty").classList.add("hidden");
  $("#interview-card").classList.remove("hidden");
  $("#answer-form").classList.add("hidden");
  $("#complete-card").classList.remove("hidden");
  $("#model-status").innerHTML = "<i></i> Interview complete";
  $("#question-count").textContent = "06 / 06";
  $("#chat-thread").innerHTML = (data.messages || [])
    .map((entry) => message(entry.role, entry.content))
    .join("");
  $("#chat-thread").scrollTop = $("#chat-thread").scrollHeight;
  refreshApplicants();
}

async function selectApplicant(id) {
  activeId = id;
  await refreshApplicants();
  const data = await api(`/api/interviews/${id}`);
  data.complete ? showComplete(data) : showQuestion(data);
}

$("#application-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const data = await api("/api/applicants", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(form)),
    });
    activeId = data.id;
    event.currentTarget.reset();
    toast(data.message);
    switchView("interview");
    await selectApplicant(activeId);
  } catch (error) {
    toast(error.message);
  }
});

$("#answer-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api(`/api/interviews/${activeId}/answers`, {
      method: "POST",
      body: JSON.stringify({ answer: $("#answer").value }),
    });
    data.complete ? showComplete(data) : showQuestion(data);
  } catch (error) {
    toast(error.message);
  }
});

function personCard(person) {
  const badgeClass =
    person.decision === "Waitlist"
      ? "wait"
      : person.guaranteed_job
        ? "guarantee"
        : "";
  const summary = person.ai_summary
    ? `<p class="ai-summary">✦ ${escapeHtml(person.ai_summary)}</p>`
    : "";
  return `<article class="person"><div class="person-top"><span class="person-name">${person.name}</span><span class="badge ${badgeClass}">${person.decision}</span></div><div class="person-skill">${person.skill}</div><p>${person.reason}</p>${summary}</article>`;
}
async function review() {
  try {
    const result = await api("/api/selection", {
      method: "POST",
      body: JSON.stringify({ seats: 5 }),
    });
    if (!result.assessed) {
      $("#review-empty").classList.remove("hidden");
      $("#review-result").classList.add("hidden");
      return;
    }
    const guaranteed = result.placements.filter(
      (person) => person.guaranteed_job,
    );
    const training = result.placements.filter(
      (person) => !person.guaranteed_job,
    );
    $("#review-empty").classList.add("hidden");
    $("#review-result").classList.remove("hidden");
    $("#review-note").textContent =
      `${result.assessed} completed interview${result.assessed === 1 ? "" : "s"} assessed. ${result.note}`;
    $("#job-guarantees").innerHTML = guaranteed.length
      ? guaranteed.map(personCard).join("")
      : '<p class="person">No job guarantees can be awarded until an interview is complete.</p>';
    $("#training-placements").innerHTML = training.length
      ? training.map(personCard).join("")
      : '<p class="person">No additional training places awarded.</p>';
    $("#waitlist").innerHTML = result.waitlist.length
      ? result.waitlist.map(personCard).join("")
      : '<p class="person">No completed applicants are on the waitlist.</p>';
  } catch (error) {
    toast(error.message);
  }
}
$("#review-button").addEventListener("click", review);
$("#demo-button").addEventListener("click", async () => {
  try {
    const result = await api("/api/demo", { method: "POST" });
    toast(result.message);
    activeId = null;
    await refreshApplicants();
    await review();
  } catch (error) {
    toast(error.message);
  }
});
refreshApplicants().catch(() => toast("Could not connect to the app."));
