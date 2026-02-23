const state = {
  employees: [],
  attendance: [],
};

const el = {
  navButtons: [...document.querySelectorAll(".nav-btn")],
  views: {
    dashboard: document.getElementById("dashboard-view"),
    employees: document.getElementById("employees-view"),
    attendance: document.getElementById("attendance-view"),
  },
  title: document.getElementById("view-title"),
  todayLabel: document.getElementById("today-label"),
  banner: document.getElementById("banner"),
  employeeForm: document.getElementById("employee-form"),
  attendanceForm: document.getElementById("attendance-form"),
  employeeSelect: document.getElementById("employee-select"),
  employeesTableBody: document.querySelector("#employees-table tbody"),
  attendanceTableBody: document.querySelector("#attendance-table tbody"),
  employeesState: document.getElementById("employees-state"),
  attendanceState: document.getElementById("attendance-state"),
  refreshEmployees: document.getElementById("refresh-employees"),
  filterDate: document.getElementById("filter-date"),
  filterBtn: document.getElementById("filter-btn"),
  clearFilterBtn: document.getElementById("clear-filter-btn"),
  attendanceDate: document.getElementById("attendance-date"),
  dashboard: {
    employeeCount: document.getElementById("employee-count"),
    presentCount: document.getElementById("present-count"),
    absentCount: document.getElementById("absent-count"),
    attendanceCount: document.getElementById("attendance-count"),
  },
};

const today = new Date().toISOString().slice(0, 10);
el.attendanceDate.value = today;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function showBanner(message, type = "success") {
  el.banner.textContent = message;
  el.banner.classList.remove("hidden", "success", "error");
  el.banner.classList.add(type);
  setTimeout(() => el.banner.classList.add("hidden"), 2400);
}

function setView(viewName) {
  el.navButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });

  Object.entries(el.views).forEach(([name, node]) => {
    node.classList.toggle("active", name === viewName);
  });

  el.title.textContent = viewName.charAt(0).toUpperCase() + viewName.slice(1);
}

function renderEmployeeSelect() {
  if (!state.employees.length) {
    el.employeeSelect.innerHTML = `<option value="">No employees available</option>`;
    return;
  }

  const options = state.employees
    .map(
      (emp) =>
        `<option value="${emp.employeeId}">${emp.employeeId} - ${emp.fullName}</option>`
    )
    .join("");
  el.employeeSelect.innerHTML = options;
}

function renderEmployees() {
  if (!state.employees.length) {
    el.employeesState.textContent = "No employees added yet.";
    el.employeesTableBody.innerHTML = "";
    return;
  }

  el.employeesState.textContent = "";
  el.employeesTableBody.innerHTML = state.employees
    .map(
      (emp) => `
      <tr>
        <td>${emp.employeeId}</td>
        <td>${emp.fullName}</td>
        <td>${emp.email}</td>
        <td>${emp.department}</td>
        <td>${emp.presentDays}</td>
        <td><button class="danger-btn" data-id="${emp.employeeId}">Delete</button></td>
      </tr>
    `
    )
    .join("");
}

function renderAttendance() {
  if (!state.attendance.length) {
    el.attendanceState.textContent = "No attendance records found.";
    el.attendanceTableBody.innerHTML = "";
    return;
  }

  el.attendanceState.textContent = "";
  el.attendanceTableBody.innerHTML = state.attendance
    .map(
      (rec) => `
      <tr>
        <td>${rec.date}</td>
        <td>${rec.employeeId}</td>
        <td>${rec.fullName}</td>
        <td>
          <span class="status-pill ${rec.status.toLowerCase()}">${rec.status}</span>
        </td>
      </tr>
    `
    )
    .join("");
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  el.dashboard.employeeCount.textContent = data.employeeCount;
  el.dashboard.presentCount.textContent = data.attendanceToday.present;
  el.dashboard.absentCount.textContent = data.attendanceToday.absent;
  el.dashboard.attendanceCount.textContent = data.totalAttendanceRecords;
  el.todayLabel.textContent = `Today: ${data.today}`;
}

async function loadEmployees() {
  el.employeesState.textContent = "Loading employees...";
  const data = await api("/api/employees");
  state.employees = data.employees;
  renderEmployees();
  renderEmployeeSelect();
}

async function loadAttendance(filterDate = "") {
  el.attendanceState.textContent = "Loading attendance...";
  const query = filterDate ? `?date=${encodeURIComponent(filterDate)}` : "";
  const data = await api(`/api/attendance${query}`);
  state.attendance = data.attendance;
  renderAttendance();
}

async function initialize() {
  try {
    await Promise.all([loadDashboard(), loadEmployees(), loadAttendance()]);
  } catch (error) {
    showBanner(error.message, "error");
  }
}

el.navButtons.forEach((btn) => {
  btn.addEventListener("click", () => setView(btn.dataset.view));
});

el.employeeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(el.employeeForm);
  const payload = Object.fromEntries(form.entries());

  try {
    await api("/api/employees", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    el.employeeForm.reset();
    showBanner("Employee added successfully.");
    await Promise.all([loadEmployees(), loadDashboard()]);
  } catch (error) {
    showBanner(error.message, "error");
  }
});

el.refreshEmployees.addEventListener("click", async () => {
  try {
    await loadEmployees();
  } catch (error) {
    showBanner(error.message, "error");
  }
});

el.employeesTableBody.addEventListener("click", async (event) => {
  const target = event.target;
  if (!target.matches(".danger-btn")) return;

  const employeeId = target.dataset.id;
  try {
    await api(`/api/employees/${encodeURIComponent(employeeId)}`, { method: "DELETE" });
    showBanner("Employee deleted successfully.");
    await Promise.all([loadEmployees(), loadDashboard(), loadAttendance(el.filterDate.value)]);
  } catch (error) {
    showBanner(error.message, "error");
  }
});

el.attendanceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(el.attendanceForm);
  const payload = Object.fromEntries(form.entries());

  try {
    await api("/api/attendance", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showBanner("Attendance marked successfully.");
    await Promise.all([loadAttendance(el.filterDate.value), loadEmployees(), loadDashboard()]);
  } catch (error) {
    showBanner(error.message, "error");
  }
});

el.filterBtn.addEventListener("click", async () => {
  try {
    await loadAttendance(el.filterDate.value);
  } catch (error) {
    showBanner(error.message, "error");
  }
});

el.clearFilterBtn.addEventListener("click", async () => {
  el.filterDate.value = "";
  try {
    await loadAttendance();
  } catch (error) {
    showBanner(error.message, "error");
  }
});

initialize();
