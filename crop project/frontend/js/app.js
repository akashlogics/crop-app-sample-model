/**
 * CropAI — Frontend Application Logic
 * Connects to Flask backend at localhost:5000
 */

const API = "http://localhost:5000";

const CROPS = [
  "rice", "maize", "chickpea", "kidneybeans", "pigeonpeas",
  "mothbeans", "mungbean", "blackgram", "lentil", "pomegranate",
  "banana", "mango", "grapes", "watermelon", "muskmelon",
  "apple", "orange", "papaya", "coconut", "cotton", "jute", "coffee"
];

// Soil type → typical NPK + pH values
const SOIL_NUTRITION = {
  "Alluvial Soil": { N: 90, P: 55, K: 40, ph: 7.0, desc: "Highly fertile, supports most crops" },
  "Black Soil": { N: 48, P: 24, K: 50, ph: 7.8, desc: "Rich in calcium & magnesium, ideal for cotton" },
  "Red Soil": { N: 20, P: 15, K: 20, ph: 6.0, desc: "Low nutrients, good for drought-resistant crops" },
  "Laterite Soil": { N: 10, P: 10, K: 15, ph: 5.5, desc: "Acidic, requires heavy fertilisation" },
  "Sandy Soil": { N: 15, P: 12, K: 25, ph: 6.2, desc: "Good drainage, needs frequent irrigation" },
  "Loamy Soil": { N: 60, P: 45, K: 43, ph: 6.8, desc: "Best balance of drainage and fertility" },
  "Clay Soil": { N: 40, P: 35, K: 30, ph: 7.2, desc: "High water retention, suited for paddy" },
};

// Crop emoji map (mirrors backend CROP_INFO)
const CROP_INFO = {
  rice: "🌾", maize: "🌽", chickpea: "🫘", kidneybeans: "🫘",
  pigeonpeas: "🌿", mothbeans: "🌱", mungbean: "🫘", blackgram: "🫘",
  lentil: "🫘", pomegranate: "🍎", banana: "🍌", mango: "🥭",
  grapes: "🍇", watermelon: "🍉", muskmelon: "🍈", apple: "🍏",
  orange: "🍊", papaya: "🍈", coconut: "🥥", cotton: "🌿",
  jute: "🌾", coffee: "☕"
};

// State
let npkOverrideActive = false;
let weatherLoaded = false;

// Persisted across recommendation result
let currentHistoryId   = null;
let currentSelectedCrop = null;

// ── Page Navigation ─────────────────────────────────────────────────────────
function showPage(name, elClicked) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));

  // Reset desktop nav
  document.querySelectorAll(".dh-nav-btn").forEach(b => b.classList.remove("active"));
  // Reset mobile nav
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  const page = document.getElementById(`page-${name}`);
  if (page) page.classList.add("active");

  // Activate nav buttons
  const dhBtn = document.getElementById(`dh-${name}`);
  if (dhBtn) dhBtn.classList.add("active");

  const mobileBtn = document.getElementById(`nav-${name}`);
  if (mobileBtn) mobileBtn.classList.add("active");

  // Side effects
  if (name === "history") { loadHistory(); loadInsights(); }
  if (name === "weather") {
    const loc = document.getElementById("location")?.value?.trim();
    if (loc && !weatherLoaded) fetchWeather(loc);
    // If a crop is already selected, load its water schedule
    if (currentSelectedCrop) {
      const weatherCity = document.getElementById("weatherSearchInput")?.value?.trim()
        || document.getElementById("location")?.value?.trim()
        || "Delhi";
      loadWaterSchedule(weatherCity, currentSelectedCrop);
    }
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Custom Dropdown ─────────────────────────────────────────────────────────
function toggleDropdown(dropdownId, boxEl) {
  const dropdown = document.getElementById(dropdownId);
  const isHidden = dropdown.classList.contains("hidden");

  // Close all
  document.querySelectorAll(".dropdown-menu").forEach(d => d.classList.add("hidden"));
  document.querySelectorAll(".select-box").forEach(b => b.classList.remove("open"));

  if (isHidden) {
    dropdown.classList.remove("hidden");
    boxEl.classList.add("open");
  }
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".select-box") && !e.target.closest(".dropdown-menu")) {
    document.querySelectorAll(".dropdown-menu").forEach(d => d.classList.add("hidden"));
    document.querySelectorAll(".select-box").forEach(b => b.classList.remove("open"));
  }
});

// ── Soil Type Selection → Auto-fill NPK ─────────────────────────────────────
function selectSoil(value, N, P, K, ph) {
  document.getElementById("soilType").value = value;

  // Update dropdown display
  const placeholder = document.getElementById("soilPlaceholder");
  placeholder.textContent = value;
  placeholder.classList.add("selected");
  document.getElementById("soilDropdown").classList.add("hidden");
  document.getElementById("soilBox").classList.remove("open");

  // Auto-fill NPK + pH from lookup table
  const nutrition = SOIL_NUTRITION[value] || { N, P, K, ph };
  fillNPK(nutrition.N, nutrition.P, nutrition.K, nutrition.ph);

  // Show NPK section & override toggle
  document.getElementById("npkSection").style.display = "block";
  document.getElementById("npkOverrideToggle").style.display = "block";

  // Reset to readonly mode when soil type changes
  npkOverrideActive = false;
  setNpkReadonly(true);
  const overrideBtn = document.querySelector(".override-btn");
  if (overrideBtn) overrideBtn.textContent = "✏️ Override soil nutrient values";

  // Update auto-note with soil description
  const note = document.querySelector(".auto-note");
  if (note && nutrition.desc) {
    note.textContent = `💡 ${nutrition.desc}. Values can be overridden with your soil test report.`;
  }

  updateProgress();
}

function fillNPK(N, P, K, ph) {
  document.getElementById("N").value = N;
  document.getElementById("P").value = P;
  document.getElementById("K").value = K;
  document.getElementById("ph").value = ph;
}

function setNpkReadonly(readonly) {
  ["N", "P", "K", "ph"].forEach(id => {
    const inp = document.getElementById(id);
    if (readonly) {
      inp.setAttribute("readonly", true);
    } else {
      inp.removeAttribute("readonly");
    }
  });

  document.querySelectorAll(".npk-cell").forEach(cell => {
    if (readonly) {
      cell.classList.add("readonly");
    } else {
      cell.classList.remove("readonly");
      cell.style.borderColor = "";
    }
  });
}

function toggleNpkOverride() {
  npkOverrideActive = !npkOverrideActive;
  setNpkReadonly(!npkOverrideActive);
  const btn = document.querySelector(".override-btn");
  if (btn) {
    btn.textContent = npkOverrideActive
      ? "🔒 Lock back to soil-type values"
      : "✏️ Override soil nutrient values";
  }
  if (!npkOverrideActive) {
    // Revert to soil type values
    const soilType = document.getElementById("soilType").value;
    const nutrition = SOIL_NUTRITION[soilType];
    if (nutrition) fillNPK(nutrition.N, nutrition.P, nutrition.K, nutrition.ph);
  }
}

// ── Irrigation Selection ────────────────────────────────────────────────────
function selectIrrig(value) {
  document.getElementById("irrigType").value = value;
  const placeholder = document.getElementById("irrigPlaceholder");
  placeholder.textContent = value;
  placeholder.classList.add("selected");
  document.getElementById("irrigDropdown").classList.add("hidden");
  document.getElementById("irrigBox").classList.remove("open");
}

// ── Progress Bar (2 required: location + soil type) ────────────────────────
function updateProgress() {
  const soilFilled     = !!document.getElementById("soilType").value;
  const locationFilled = !!document.getElementById("location").value.trim();

  const filled = [soilFilled, locationFilled].filter(Boolean).length;
  const pct    = Math.round((filled / 2) * 100);

  document.getElementById("progressFill").style.width = `${pct}%`;
  document.getElementById("progressText").textContent  = `${filled}/2 required`;
}

// ── Form Submission ─────────────────────────────────────────────────────────
document.getElementById("recommendForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await getRecommendation();
});

async function getRecommendation() {
  // Validate required fields
  const location = document.getElementById("location").value.trim();
  const soilType = document.getElementById("soilType").value;

  if (!location) { showToast("⚠️ Please enter a location", "warn"); return; }
  if (!soilType) { showToast("⚠️ Please select a Soil Type", "warn"); return; }

  // NPK + pH (auto-filled or overridden)
  const fields  = ["N", "P", "K", "ph", "temperature", "humidity", "rainfall"];
  const payload = { location, soil_type: soilType };

  for (const f of fields) {
    const val = document.getElementById(f)?.value?.toString().trim();
    if (!val && ["temperature", "humidity", "rainfall"].includes(f)) {
      showToast("⚠️ Weather data not loaded yet. Enter location & wait for auto-fetch.", "warn");
      return;
    }
    payload[f] = parseFloat(val) || 0;
  }

  payload.irrig_type = document.getElementById("irrigType").value || "Unknown";
  payload.land_size  = parseFloat(document.getElementById("landSize").value) || null;

  setLoading(true);

  try {
    const res  = await fetch(`${API}/recommend`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.error) { showToast(`❌ ${data.error}`, "error"); return; }

    // Store history ID for later crop selection
    currentHistoryId = data.history_id || null;

    renderResults(data);
    showToast("✅ Recommendation ready!", "success");
  } catch (err) {
    showToast("❌ Cannot connect to backend. Is Flask running?", "error");
    console.error(err);
  } finally {
    setLoading(false);
  }
}

// ── Render Results ──────────────────────────────────────────────────────────
function renderResults(data) {
  document.getElementById("resultsPlaceholder").style.display = "none";
  const section = document.getElementById("resultsSection");
  section.style.display = "block";

  const top = data.top_recommendation;

  document.getElementById("topEmoji").textContent     = top.emoji;
  document.getElementById("topCropName").textContent  = top.crop;
  document.getElementById("topCropDesc").textContent  = top.description;
  document.getElementById("topFertilizer").textContent = `🧪 Fertilizer: ${top.fertilizer}`;
  document.getElementById("topConfLabel").textContent  = `${top.confidence}%`;

  setTimeout(() => {
    document.getElementById("topConfBar").style.width = `${top.confidence}%`;
  }, 100);

  // Other crops grid (positions 2–5)
  const grid = document.getElementById("resultsGrid");
  grid.innerHTML = "";
  const others = data.all_recommendations.slice(1);
  others.forEach((item, i) => {
    const div = document.createElement("div");
    div.className = "result-item";
    div.style.animationDelay = `${i * 80}ms`;
    div.innerHTML = `
      <div class="result-emoji">${item.emoji}</div>
      <div class="result-name">${item.crop}</div>
      <div class="result-bar-wrap">
        <div class="result-bar-bg">
          <div class="result-bar-fill" style="width:0%" data-width="${item.confidence}%"></div>
        </div>
      </div>
      <div class="result-conf">${item.confidence}% match</div>
    `;
    grid.appendChild(div);
  });

  setTimeout(() => {
    grid.querySelectorAll(".result-bar-fill").forEach(bar => {
      bar.style.width = bar.dataset.width;
    });
  }, 200);

  // Farm advisory
  if (data.advisory?.length) {
    const box  = document.getElementById("advisoryBox");
    const list = document.getElementById("advisoryList");
    list.innerHTML = data.advisory.map(a => `<li>${a}</li>`).join("");
    box.style.display = "block";
  }

  // Render crop selector (best + 4 related)
  renderCropSelector(data.all_recommendations);

  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Crop Selector ───────────────────────────────────────────────────────────
function renderCropSelector(recommendations) {
  const section = document.getElementById("cropSelectorSection");
  const grid    = document.getElementById("cropSelectorGrid");
  if (!section || !grid) return;

  // Reset banner
  const banner = document.getElementById("cropSelectedBanner");
  if (banner) banner.style.display = "none";

  grid.innerHTML = recommendations.map((crop, i) => `
    <div class="crop-select-card ${i === 0 ? "best" : ""}" id="csc-${crop.crop}" onclick="selectCropToGrow('${crop.crop}', '${crop.emoji}')">
      <div class="csc-badge">${i === 0 ? "✨ Best Match" : "🌿 Related"}</div>
      <div class="csc-emoji">${crop.emoji}</div>
      <div class="csc-name">${crop.crop.charAt(0).toUpperCase() + crop.crop.slice(1)}</div>
      <div class="csc-conf">${crop.confidence}% match</div>
      <button class="csc-select-btn">Select to Grow</button>
    </div>
  `).join("");

  section.style.display = "block";
}

async function selectCropToGrow(cropName, cropEmoji) {
  // Highlight selected card
  document.querySelectorAll(".crop-select-card").forEach(c => c.classList.remove("active"));
  const card = document.getElementById(`csc-${cropName}`);
  if (card) card.classList.add("active");

  currentSelectedCrop = cropName;

  // Show confirmation banner
  const banner = document.getElementById("cropSelectedBanner");
  const emojiEl = document.getElementById("cropSelectedEmoji");
  const textEl  = document.getElementById("cropSelectedText");
  if (banner) {
    emojiEl.textContent = cropEmoji || CROP_INFO[cropName] || "🌱";
    textEl.textContent  = `${cropName.charAt(0).toUpperCase() + cropName.slice(1)} selected for planting!`;
    banner.style.display = "flex";
  }

  showToast(`✅ ${cropName.charAt(0).toUpperCase() + cropName.slice(1)} selected!`, "success");

  // Save to backend DB
  if (currentHistoryId) {
    try {
      await fetch(`${API}/select-crop`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ history_id: currentHistoryId, selected_crop: cropName })
      });
    } catch (e) {
      console.warn("Could not save crop selection to backend:", e);
    }
  }

  // Store in localStorage so weather page picks it up across navigations
  localStorage.setItem("cropai_selected_crop", cropName);
  localStorage.setItem("cropai_selected_emoji", cropEmoji || CROP_INFO[cropName] || "🌱");

  // Pre-load water schedule in background so it's ready when user switches tabs
  const weatherCity = document.getElementById("weatherSearchInput")?.value?.trim()
    || document.getElementById("location")?.value?.trim()
    || "Delhi";
  loadWaterSchedule(weatherCity, cropName);
}

// ── 4-Day Water Schedule ──────────────────────────────────────────────────────
async function loadWaterSchedule(city, crop) {
  const panel = document.getElementById("waterSchedulePanel");
  const grid  = document.getElementById("waterDayGrid");
  const label = document.getElementById("waterScheduleCropLabel");
  const note  = document.getElementById("waterNextCallNote");
  if (!panel || !grid) return;

  const emoji = localStorage.getItem("cropai_selected_emoji") || CROP_INFO[crop] || "🌱";
  if (label) label.textContent = `${emoji} ${crop.charAt(0).toUpperCase() + crop.slice(1)}`;

  // Show loading state
  grid.innerHTML = `<div class="ws-loading">⏳ Building your irrigation schedule…</div>`;
  panel.style.display = "block";

  try {
    const res  = await fetch(`${API}/water-schedule?city=${encodeURIComponent(city)}&crop=${encodeURIComponent(crop)}`);
    const data = await res.json();

    if (data.error) {
      grid.innerHTML = `<p class="muted-hint">⚠️ ${data.error}</p>`;
      return;
    }

    if (note) note.textContent = data.next_call_note || "Return after Day 4 for an updated plan.";

    grid.innerHTML = data.schedule.map(day => `
      <div class="ws-day-card">
        <div class="ws-day-header">
          <span class="ws-day-num">Day ${day.day_num}</span>
          <span class="ws-day-icon">${day.icon}</span>
        </div>
        <div class="ws-date">${day.weekday}</div>
        <div class="ws-date-full">${day.date}</div>
        <div class="ws-weather-desc">${day.weather_desc}</div>
        <div class="ws-water-amount ${day.recommended_water_L === 0 ? "skip" : ""}">
          ${day.recommended_water_L === 0
            ? "⏭️ Skip"
            : `💧 ${day.recommended_water_L} L`}
        </div>
        <div class="ws-sub">per plant</div>
        <div class="ws-rain-info">🌧️ ${day.rainfall_mm} mm rain · 💦 ${day.humidity_pct}% humidity</div>
        <div class="ws-note">${day.note}</div>
      </div>
    `).join("");

  } catch (e) {
    grid.innerHTML = `<p class="muted-hint">⚠️ Could not load water schedule.</p>`;
    console.error(e);
  }
}

// ── Weather ──────────────────────────────────────────────────────────────────
async function searchWeather() {
  const city = document.getElementById("weatherSearchInput").value.trim();
  if (!city) { showToast("⚠️ Enter a city name", "warn"); return; }
  await fetchWeather(city);
  await loadForecast(city);

  // Reload water schedule for current city if crop selected
  const crop = currentSelectedCrop || localStorage.getItem("cropai_selected_crop");
  if (crop) loadWaterSchedule(city, crop);
}

async function fetchWeather(city) {
  try {
    const res  = await fetch(`${API}/weather?city=${encodeURIComponent(city)}`);
    const data = await res.json();
    if (data.error) { showToast(`Weather error: ${data.error}`, "error"); return; }

    // Hidden form fields (used by the backend recommendation)
    document.getElementById("temperature").value = data.temperature;
    document.getElementById("humidity").value    = data.humidity;
    document.getElementById("rainfall").value    = data.rainfall;

    // Weather page stat tiles
    document.getElementById("weatherLocation").textContent = data.city || city;
    document.getElementById("weatherIcon").textContent     = data.icon || "⛅";
    document.getElementById("weatherTemp").textContent     = `${data.temperature}°C`;
    document.getElementById("weatherDesc").textContent     = data.description || "—";
    document.getElementById("wHumidity").textContent       = `${data.humidity}%`;
    document.getElementById("wRainfall").textContent       = `${data.rainfall} mm`;
    document.getElementById("wWind").textContent    = data.wind_speed ? `${data.wind_speed} km/h` : "-- km/h";
    document.getElementById("wPressure").textContent = data.pressure  ? `${data.pressure} hPa`  : "-- hPa";

    // Sync weather search input
    const wsInput = document.getElementById("weatherSearchInput");
    if (wsInput) wsInput.value = city;

    // Sync location field in recommend form
    const locInput = document.getElementById("location");
    if (locInput && !locInput.value.trim()) locInput.value = city;

    // Show Today's Farming Advisory on weather page
    if (data.advisory && data.advisory.length) {
      const advisoryCard = document.getElementById("advisoryCard");
      const advisoryList = document.getElementById("weatherAdvisoryList");
      if (advisoryCard && advisoryList) {
        advisoryList.innerHTML = data.advisory.map(tip => `<li>${tip}</li>`).join("");
        advisoryCard.style.display = "block";
      }
    }

    // Update weather status banner on recommend page
    weatherLoaded = true;
    const banner = document.getElementById("weatherBanner");
    if (banner) {
      banner.classList.add("loaded");
      document.getElementById("wsbIcon").textContent  = "✅";
      document.getElementById("wsbTitle").textContent = `Weather loaded for ${data.city || city}`;
      document.getElementById("wsbSub").textContent   =
        `${data.temperature}°C · ${data.humidity}% humidity · ${data.rainfall} mm rainfall`;
    }

    const badge = data.source === "live" ? "🟢 Live" : "🟡 Demo";
    showToast(`${badge} Weather loaded for ${data.city || city}`, "success");

    // Also load forecast so water schedule has data
    loadForecast(city);

  } catch (err) {
    showToast("❌ Weather service unavailable", "error");
  }
}

// ── 4-Day Forecast ────────────────────────────────────────────────────────────
async function loadForecast(city) {
  const grid = document.getElementById("forecastGrid");
  const hint = document.getElementById("forecastHint");
  if (!grid) return;

  try {
    const res  = await fetch(`${API}/forecast?city=${encodeURIComponent(city)}`);
    const days = await res.json();

    if (days.error || !days.length) {
      if (hint) hint.style.display = "block";
      return;
    }

    if (hint) hint.style.display = "none";
    grid.innerHTML = days.map(d => `
      <div class="forecast-day-card">
        <span class="fdc-day">${d.day}</span>
        <span class="fdc-icon">${d.icon}</span>
        <span class="fdc-temp">${d.temp_min}° – ${d.temp_max}°C</span>
        <span class="fdc-desc">${d.description}</span>
        <div class="fdc-details">
          <span class="fdc-detail">💧 ${d.humidity}%</span>
          <span class="fdc-detail">🌧️ ${d.rainfall}mm</span>
        </div>
      </div>
    `).join("");
  } catch {
    if (hint) { hint.textContent = "Forecast unavailable."; hint.style.display = "block"; }
  }
}

// ── History ──────────────────────────────────────────────────────────────────
async function loadHistory() {
  const wrap = document.getElementById("historyCards");
  if (!wrap) return;

  try {
    const res  = await fetch(`${API}/history`);
    const rows = await res.json();

    if (!rows.length) {
      wrap.innerHTML = `
        <div class="empty-state-card">
          <div class="rp-icon">📜</div>
          <p>No history yet. Make your first recommendation!</p>
        </div>`;
      return;
    }

    wrap.innerHTML = rows.map((r, idx) => {
      const emoji   = CROP_INFO[r.top_crop] || "🌱";
      const allRes  = safeParseJson(r.all_results);
      const advisory = buildAdvisory(r.temperature, r.humidity, r.rainfall, r.soil_type);

      // Fertilizer quick lookup
      const fertMap = {
        rice:"Urea + DAP", maize:"NPK 20-20-20", chickpea:"SSP + MOP",
        kidneybeans:"DAP + Potash", pigeonpeas:"Phosphorus-rich", mothbeans:"Low nitrogen",
        mungbean:"DAP", blackgram:"NPK blend", lentil:"SSP", pomegranate:"MOP + Urea",
        banana:"NPK 10-10-10", mango:"NPK 12-12-12", grapes:"Potassium-rich",
        watermelon:"Calcium + Boron", muskmelon:"NPK 13-0-46", apple:"Calcium Nitrate",
        orange:"Citrus NPK blend", papaya:"Urea + MOP", coconut:"NPK + Mg",
        cotton:"Urea + DAP", jute:"Nitrogen-heavy", coffee:"NPK 17-17-17"
      };
      const fert = fertMap[r.top_crop] || "General NPK";

      // Selected crop tag
      const selectedTag = r.selected_crop
        ? `<span class="hist-tag selected-crop-tag">🌱 Growing: ${r.selected_crop}</span>`
        : "";

      return `
      <div class="hist-card" style="animation-delay:${idx * 60}ms">
        <div class="hist-card-header">
          <span class="hist-crop-emoji">${emoji}</span>
          <div class="hist-crop-info">
            <div class="hist-crop-name">${r.top_crop}</div>
            <div class="hist-crop-sub">${fert ? '🧪 ' + fert : ''}</div>
          </div>
          <div class="hist-conf-badge">
            <span class="hist-conf-val">${r.confidence}%</span>
            <div class="hist-conf-bar-bg">
              <div class="hist-conf-bar-fill" style="width:${r.confidence}%"></div>
            </div>
          </div>
        </div>

        <div class="hist-card-body">
          <!-- Meta tags -->
          <div class="hist-meta-row">
            ${r.location ? `<span class="hist-tag">📍 ${r.location}</span>` : ""}
            ${r.soil_type ? `<span class="hist-tag soil">🏔️ ${r.soil_type}</span>` : ""}
            ${r.irrigation && r.irrigation !== "Unknown" ? `<span class="hist-tag irrig">💧 ${r.irrigation}</span>` : ""}
            ${selectedTag}
          </div>

          <!-- Soil Nutrients -->
          <div>
            <div class="hist-section-title">🌍 Soil Nutrients</div>
            <div class="hist-npk-row">
              <div class="hist-npk-cell"><div class="hist-npk-key">N mg/kg</div><div class="hist-npk-val">${r.nitrogen || "—"}</div></div>
              <div class="hist-npk-cell"><div class="hist-npk-key">P mg/kg</div><div class="hist-npk-val">${r.phosphorus || "—"}</div></div>
              <div class="hist-npk-cell"><div class="hist-npk-key">K mg/kg</div><div class="hist-npk-val">${r.potassium || "—"}</div></div>
              <div class="hist-npk-cell"><div class="hist-npk-key">pH</div><div class="hist-npk-val">${r.ph || "—"}</div></div>
            </div>
          </div>

          <!-- Weather Conditions -->
          <div>
            <div class="hist-section-title">⛅ Weather at Time of Recommendation</div>
            <div class="hist-weather-row">
              <div class="hist-wx-cell"><div class="hist-wx-key">🌡️ Temp</div><div class="hist-wx-val">${r.temperature != null ? r.temperature + "°C" : "—"}</div></div>
              <div class="hist-wx-cell"><div class="hist-wx-key">💧 Humidity</div><div class="hist-wx-val">${r.humidity != null ? r.humidity + "%" : "—"}</div></div>
              <div class="hist-wx-cell"><div class="hist-wx-key">🌧️ Rainfall</div><div class="hist-wx-val">${r.rainfall != null ? r.rainfall + " mm" : "—"}</div></div>
            </div>
          </div>

          <!-- Other Crops -->
          ${allRes.length > 1 ? `
          <div>
            <div class="hist-section-title">🌾 Other Suggested Crops</div>
            <div class="hist-meta-row">
              ${allRes.slice(1, 4).map(c =>
        `<span class="hist-tag">${CROP_INFO[c.crop] || "🌱"} ${c.crop} (${c.confidence}%)</span>`
      ).join("")}
            </div>
          </div>` : ""}

          <!-- Farming Advisory -->
          ${advisory.length ? `
          <div>
            <div class="hist-section-title">💡 Farming Advisory</div>
            <div class="hist-advisory">
              ${advisory.map(a => `<div class="hist-advisory-item">${a}</div>`).join("")}
            </div>
          </div>` : ""}
        </div>

        <div class="hist-card-footer">
          <span>🕐 ${formatDate(r.timestamp)}</span>
          <span>#${rows.length - idx}</span>
        </div>
      </div>`;
    }).join("");

    // Animate confidence bars
    setTimeout(() => {
      wrap.querySelectorAll(".hist-conf-bar-fill").forEach(bar => {
        const w = bar.style.width; bar.style.width = "0"; setTimeout(() => bar.style.width = w, 50);
      });
    }, 100);

  } catch (e) {
    showToast("❌ Cannot load history", "error");
    console.error(e);
  }
}

// ── Helpers for history cards ─────────────────────────────────────────────────
function safeParseJson(str) {
  try { return JSON.parse(str) || []; } catch { return []; }
}

function buildAdvisory(temp, humidity, rainfall, soilType) {
  const tips = [];
  if (temp > 35) tips.push("⚠️ High temperature — ensure adequate irrigation.");
  else if (temp < 15) tips.push("❄️ Low temperature — consider frost-tolerant varieties.");
  if (humidity > 85) tips.push("💧 High humidity — watch for fungal diseases.");
  if (rainfall < 50) tips.push("🏜️ Low rainfall — supplemental irrigation recommended.");
  else if (rainfall > 250) tips.push("🌧️ Heavy rainfall — ensure proper field drainage.");
  const soilTips = {
    "Alluvial Soil":  "🌱 Alluvial soil is highly fertile — excellent for most crops.",
    "Black Soil":     "🌿 Black soil retains moisture well — ideal for cotton.",
    "Red Soil":       "🧪 Red soil is low in nutrients — apply NPK fertilizers.",
    "Laterite Soil":  "⚗️ Laterite soil is acidic — apply lime before planting.",
    "Sandy Soil":     "💦 Sandy soil drains fast — frequent irrigation needed.",
    "Loamy Soil":     "✨ Loamy soil has great structure — minimal amendments needed.",
    "Clay Soil":      "🏗️ Clay soil retains water — ensure proper drainage.",
  };
  if (soilType && soilTips[soilType]) tips.push(soilTips[soilType]);
  return tips;
}

// ── Insights ─────────────────────────────────────────────────────────────────
async function loadInsights() {
  try {
    const res  = await fetch(`${API}/feature-importance`);
    const data = await res.json();
    const wrap = document.getElementById("featureChart");
    wrap.innerHTML = data.map(f => `
      <div class="feature-row">
        <span class="feature-name">${f.feature}</span>
        <div class="feature-bar-bg">
          <div class="feature-bar-fill" style="width:0%" data-w="${f.importance}%"></div>
        </div>
        <span class="feature-pct">${f.importance}%</span>
      </div>
    `).join("");

    setTimeout(() => {
      wrap.querySelectorAll(".feature-bar-fill").forEach(b => {
        b.style.width = b.dataset.w;
      });
    }, 150);
  } catch {
    document.getElementById("featureChart").innerHTML =
      `<p class="muted-hint">Start the backend server to view insights.</p>`;
  }
}

// ── Example Data ─────────────────────────────────────────────────────────────
function fillExample() {
  const examples = [
    { location: "Punjab, India",   soil: "Alluvial Soil", N: 90, P: 42, K: 43, ph: 6.5 },
    { location: "Madhya Pradesh",  soil: "Black Soil",    N: 48, P: 24, K: 50, ph: 7.8 },
    { location: "Karnataka",       soil: "Red Soil",      N: 20, P: 15, K: 20, ph: 6.0 },
    { location: "Rajasthan",       soil: "Sandy Soil",    N: 15, P: 12, K: 25, ph: 6.2 },
  ];
  const ex = examples[Math.floor(Math.random() * examples.length)];

  document.getElementById("location").value = ex.location;

  // Simulate soil selection
  selectSoil(ex.soil, ex.N, ex.P, ex.K, ex.ph);

  updateProgress();

  // Auto-load weather for the example location
  fetchWeather(ex.location);

  showToast(`📋 Example loaded: ${ex.soil} in ${ex.location}`, "success");
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setLoading(on) {
  const btn  = document.getElementById("submitBtn");
  const text = btn.querySelector(".btn-text");
  const load = btn.querySelector(".btn-loader");
  const dot  = btn.querySelector(".btn-dot");
  btn.disabled      = on;
  text.style.display = on ? "none" : "";
  load.style.display = on ? "" : "none";
  if (dot) dot.style.display = on ? "none" : "";
}

function formatDate(ts) {
  if (!ts) return "—";
  const d = new Date(ts + (ts.includes("Z") ? "" : "Z"));
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) +
    " " + d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimeout;
function showToast(msg, type = "success") {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.style.cssText = `
      position:fixed;bottom:80px;left:50%;transform:translateX(-50%) translateY(12px);
      z-index:9999;padding:11px 20px;border-radius:12px;font-size:0.84rem;
      font-weight:600;font-family:Inter,sans-serif;max-width:340px;width:max-content;
      transition:all 0.3s;opacity:0;border:1px solid;backdrop-filter:blur(14px);
      text-align:center;white-space:nowrap;
    `;
    document.body.appendChild(toast);
  }
  const styles = {
    success: { bg: "rgba(14,34,22,0.96)", border: "#22c55e", color: "#4ade80" },
    warn:    { bg: "rgba(40,30,8,0.96)",  border: "#fbbf24", color: "#fde68a" },
    error:   { bg: "rgba(40,8,8,0.96)",   border: "#ef4444", color: "#fca5a5" },
  };
  const s = styles[type] || styles.success;
  toast.style.background  = s.bg;
  toast.style.borderColor = s.border;
  toast.style.color       = s.color;
  toast.textContent       = msg;
  toast.style.opacity     = "1";
  toast.style.transform   = "translateX(-50%) translateY(0)";

  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.style.opacity   = "0";
    toast.style.transform = "translateX(-50%) translateY(12px)";
  }, 3500);
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  // Crop chips
  const chips = document.getElementById("cropChips");
  if (chips) chips.innerHTML = CROPS.map(c => `<span class="crop-chip">${c}</span>`).join("");

  // Keyboard shortcuts
  const wsInput  = document.getElementById("weatherSearchInput");
  const locInput = document.getElementById("location");
  if (wsInput)  wsInput.addEventListener("keydown",  e => { if (e.key === "Enter") searchWeather(); });
  if (locInput) locInput.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); if (locInput.value.trim()) fetchWeather(locInput.value.trim()); }
  });

  // Auto-detect location change and update progress
  if (locInput) locInput.addEventListener("input", updateProgress);

  // Restore selected crop from localStorage (so water schedule shows on reload)
  const savedCrop  = localStorage.getItem("cropai_selected_crop");
  const savedEmoji = localStorage.getItem("cropai_selected_emoji");
  if (savedCrop) {
    currentSelectedCrop = savedCrop;
    const label = document.getElementById("waterScheduleCropLabel");
    if (label) label.textContent = `${savedEmoji || "🌱"} ${savedCrop.charAt(0).toUpperCase() + savedCrop.slice(1)}`;
  }
});
