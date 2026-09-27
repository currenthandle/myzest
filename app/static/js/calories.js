// ============================================
// CALORIES.JS — Weekly Calorie Intake Tracking
// ============================================

import * as state from './state.js';
import { authFetch } from './api.js';

let weekOffset = 0;     // 0 = current week, -1 = previous week, +1 = next week
let weekEntries = [];   // Entries for the currently displayed week

function _todayIso() {
    const d = new Date();
    const tz = d.getTimezoneOffset() * 60000;
    return new Date(d - tz).toISOString().slice(0, 10);
}

// Monday of the week `offset` weeks away from the current one, as "YYYY-MM-DD".
function _weekStartForOffset(offset) {
    const today = new Date();
    const dayIndex = (today.getDay() + 6) % 7; // Monday = 0 ... Sunday = 6
    const monday = new Date(today);
    monday.setDate(today.getDate() - dayIndex + offset * 7);
    const tz = monday.getTimezoneOffset() * 60000;
    return new Date(monday - tz).toISOString().slice(0, 10);
}

export async function loadCalories() {
    const dateField = document.getElementById('calorieEntryDate');
    if (dateField && !dateField.value) dateField.value = _todayIso();
    weekOffset = 0;
    await loadWeeklySummary();
}

export function shiftCalorieWeek(delta) {
    weekOffset += delta;
    loadWeeklySummary();
}

async function loadWeeklySummary() {
    try {
        const weekStart = _weekStartForOffset(weekOffset);
        const res = await authFetch(`${state.API_URL}/calories/weekly?week_start=${weekStart}`);
        if (!res.ok) return;
        const summary = await res.json();
        weekEntries = summary.entries || [];
        renderWeeklySummary(summary);
        renderCalorieEntries();
    } catch (e) { console.error('Error loading weekly calorie summary:', e); }
}

function renderWeeklySummary(summary) {
    document.getElementById('calorieWeekTotal').textContent = summary.total_calories;
    document.getElementById('calorieWeekAverage').textContent = summary.average_daily;
    document.getElementById('calorieWeekDays').textContent = `${summary.days_logged}/7`;

    const start = formatDate(summary.week_start);
    const end = formatDate(summary.week_end);
    document.getElementById('calorieWeekRange').textContent =
        weekOffset === 0 ? `This week · ${start} - ${end}` : `${start} - ${end}`;
}

function renderCalorieEntries() {
    const list = document.getElementById('calorieEntriesList');
    const empty = document.getElementById('calorieEntriesEmpty');

    if (!weekEntries.length) {
        list.innerHTML = '';
        list.classList.add('hidden');
        empty.classList.remove('hidden');
        return;
    }

    list.classList.remove('hidden');
    empty.classList.add('hidden');

    const sorted = [...weekEntries].sort((a, b) => b.entry_date.localeCompare(a.entry_date));
    list.innerHTML = sorted.map(e => `
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700 last:border-0">
            <div class="min-w-0">
                <p class="font-bold text-gray-800 dark:text-white">${formatDate(e.entry_date)}</p>
                ${e.note ? `<p class="text-xs text-gray-400 mt-0.5 truncate">${e.note}</p>` : ''}
            </div>
            <div class="flex items-center gap-4 shrink-0">
                <span class="font-bold text-orange-500">${e.calories} kcal</span>
                <button onclick="deleteCalorieEntry(${e.id})" class="text-gray-400 hover:text-red-500 transition-colors">
                    <i class="ph-bold ph-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

export async function saveCalorieEntry() {
    const entryDate = document.getElementById('calorieEntryDate').value || _todayIso();
    const caloriesRaw = document.getElementById('calorieEntryCalories').value;
    const calories = parseInt(caloriesRaw, 10);
    const note = document.getElementById('calorieEntryNote').value.trim();

    if (caloriesRaw === '' || isNaN(calories) || calories < 0) {
        alert('Enter a valid calorie count');
        return;
    }

    try {
        const res = await authFetch(`${state.API_URL}/calories/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entry_date: entryDate, calories, note })
        });
        if (res.ok) {
            document.getElementById('calorieEntryCalories').value = '';
            document.getElementById('calorieEntryNote').value = '';
            weekOffset = 0;
            await loadWeeklySummary();
        } else {
            const err = await res.json();
            alert(err.detail || 'Error saving calorie entry');
        }
    } catch (e) {
        console.error('Error saving calorie entry:', e);
        alert('Connection error');
    }
}

export async function deleteCalorieEntry(id) {
    if (!confirm('Delete this entry?')) return;
    try {
        const res = await authFetch(`${state.API_URL}/calories/${id}`, { method: 'DELETE' });
        if (res.ok) await loadWeeklySummary();
    } catch (e) { console.error('Error deleting calorie entry:', e); }
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr + 'T00:00:00');
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch (e) { return dateStr; }
}

// --- Window Exposure ---
window.loadCalories = loadCalories;
window.shiftCalorieWeek = shiftCalorieWeek;
window.saveCalorieEntry = saveCalorieEntry;
window.deleteCalorieEntry = deleteCalorieEntry;
