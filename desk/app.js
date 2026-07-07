/* TaskMaster Desk — papers on a desk.
   Paper = List. board_order = position in the row; null board_order = put away.
   Mouse: pointer-event dragging. Keyboard: mirrors kantui (n/e/m/wasd/c) plus paper keys. */

import * as api from './api.js';

const ORDER_MIN = 1;              // mirror kanapi.py MIN_ORDER / MAX_ORDER
const ORDER_MAX = 2147483646;
const DEFAULT_CATEGORY = 1;       // same default as kantui
const DRAG_THRESHOLD = 5;         // px before a press becomes a drag
// fallback per-category colors when category_color is unset in the DB
const FALLBACK_COLORS = ['#4C8A64', '#5E7FB0', '#C08A3E', '#A05A6E', '#7A6AA8', '#688391'];

const state = {
    categories: new Map(),     // category_id -> Category
    papers: new Map(),         // list_id -> ListWithCards (on desk)
    drawer: [],                // away List rows (no cards)
    drawerCards: new Map(),    // list_id -> ListWithCards, lazily fetched for upsert "all"
    focus: { listId: null, cardId: null },
    picked: null,              // card_id picked up for keyboard moves
    printSelection: new Set(), // list_ids marked for printing
    lastCategory: DEFAULT_CATEGORY,
    drawerOpen: false,
};

const upsert = { query: '', scope: 'visible', results: [], sel: 0 };

const deskEl = document.getElementById('desk');
const drawerEl = document.getElementById('drawer');
const drawerTabsEl = document.getElementById('drawer-tabs');
const drawerEmptyEl = document.getElementById('drawer-empty');
const upsertInput = document.getElementById('upsert-input');
const upsertScopeBtn = document.getElementById('upsert-scope');
const upsertResultsEl = document.getElementById('upsert-results');
const awayDialog = document.getElementById('away-dialog');
const awayNameEl = document.getElementById('away-name');
const awayDateEl = document.getElementById('away-date');

let lastLoad = 0;
let awayTarget = null;

/* ---------- helpers ---------- */

async function guard(fn) {
    try {
        await fn();
    } catch (err) {
        console.error(err);
        alert(err.message);
        try { await reload(); } catch { /* server gone; alert already shown */ }
    }
}

function paperSortKey(list) {
    // null board_order (woken sleeper) sorts last, like the server
    return list.board_order === null ? ORDER_MAX + 1 : list.board_order;
}

function deskPapers() {
    return [...state.papers.values()].sort(
        (a, b) => paperSortKey(a) - paperSortKey(b) || a.list_id - b.list_id);
}

function currentPaper() {
    return state.papers.get(state.focus.listId) || deskPapers()[0] || null;
}

function categoryColor(categoryId) {
    const cat = state.categories.get(categoryId);
    return (cat && cat.category_color)
        || FALLBACK_COLORS[categoryId % FALLBACK_COLORS.length];
}

function isWoken(list) {
    return list.board_order === null && list.list_wakeup;
}

function upsertQuery() {
    return upsert.query.trim().toLowerCase();
}

/* ---------- data loading ---------- */

async function reload() {
    const [cats, onDesk, away] = await Promise.all(
        [api.getCategories(), api.getLists(false), api.getLists(true)]);
    state.categories = new Map(cats.map((c) => [c.category_id, c]));
    const full = await Promise.all(onDesk.map((l) => api.getList(l.list_id)));
    state.papers = new Map(full.map((l) => [l.list_id, l]));
    state.drawer = away;
    state.drawerCards.clear();
    for (const id of state.printSelection) {
        if (!state.papers.has(id)) state.printSelection.delete(id);
    }
    if (!state.papers.size && state.drawer.length) state.drawerOpen = true;
    lastLoad = Date.now();
    render();
}

async function refreshPapers(listIds) {
    const ids = [...new Set(listIds)].filter((id) => state.papers.has(id));
    const full = await Promise.all(ids.map((id) => api.getList(id)));
    for (const l of full) state.papers.set(l.list_id, l);
}

/* If a move left two adjacent cards with (nearly) no gap, re-space the list */
async function checkRebalance(listId) {
    const list = state.papers.get(listId);
    if (!list) return;
    const orders = list.cards.map((c) => c.list_order || 0);
    for (let i = 1; i < orders.length; i++) {
        if (orders[i] - orders[i - 1] <= 1) {
            await api.rebalance(listId);
            await refreshPapers([listId]);
            return;
        }
    }
}

async function doMoveCard(cardId, payload, listIds) {
    await api.moveCard(cardId, payload);
    await refreshPapers(listIds);
    for (const id of new Set(listIds)) await checkRebalance(id);
    render();
}

/* ---------- paper ordering ---------- */

function orderAtEnd() {
    const orders = deskPapers().map((p) => p.board_order).filter((o) => o !== null);
    if (!orders.length) return Math.floor((ORDER_MIN + ORDER_MAX) / 2);
    return Math.floor((Math.max(...orders) + ORDER_MAX) / 2);
}

/* Persist a paper's position given the full desired row of list_ids */
async function placePaperAt(listId, rowIds) {
    const idx = rowIds.indexOf(listId);
    const orderOf = (id) => {
        const p = state.papers.get(id);
        return p ? p.board_order : null;
    };
    let prev = null;
    for (let i = idx - 1; i >= 0; i--) {
        if (orderOf(rowIds[i]) !== null) { prev = orderOf(rowIds[i]); break; }
    }
    let next = null;
    for (let i = idx + 1; i < rowIds.length; i++) {
        if (orderOf(rowIds[i]) !== null) { next = orderOf(rowIds[i]); break; }
    }
    const lo = prev === null ? ORDER_MIN : prev;
    const hi = next === null ? ORDER_MAX : next;
    if (hi - lo <= 1) {
        // gap exhausted: renumber the whole row (papers are few)
        const step = Math.floor((ORDER_MAX - ORDER_MIN) / (rowIds.length + 1));
        for (let i = 0; i < rowIds.length; i++) {
            const order = ORDER_MIN + (i + 1) * step;
            const updated = await api.patchList(rowIds[i], { board_order: order });
            if (state.papers.has(rowIds[i])) state.papers.set(rowIds[i], { ...state.papers.get(rowIds[i]), ...updated });
        }
    } else {
        const updated = await api.patchList(listId, { board_order: Math.floor((lo + hi) / 2) });
        state.papers.set(listId, { ...state.papers.get(listId), ...updated });
    }
    render();
}

/* ---------- rendering ---------- */

function render() {
    deskEl.textContent = '';
    const q = upsertQuery();
    for (const list of deskPapers()) deskEl.append(paperEl(list, q));
    renderDrawer();
    restoreFocus();
}

function restoreFocus() {
    const active = document.activeElement;
    if (active && active !== document.body && !deskEl.contains(active)) return;
    const { listId, cardId } = state.focus;
    let el = null;
    if (cardId !== null) el = deskEl.querySelector(`.card[data-card-id="${cardId}"]`);
    if (!el && listId !== null) el = deskEl.querySelector(`.paper[data-list-id="${listId}"] h2`);
    if (el) {
        el.focus({ preventScroll: true });
        el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }
}

function paperEl(list, q) {
    const el = document.createElement('article');
    el.className = 'paper';
    el.dataset.listId = list.list_id;
    el.style.setProperty('--tilt', `${(((list.list_id * 7) % 5) - 2) * 0.4}deg`);

    const header = document.createElement('header');
    const h2 = document.createElement('h2');
    h2.textContent = list.list_name;
    h2.tabIndex = 0;
    h2.addEventListener('dblclick', () => renamePaper(list));
    header.append(h2);

    const tools = document.createElement('span');
    tools.className = 'tools';
    const printSel = document.createElement('input');
    printSel.type = 'checkbox';
    printSel.title = 'Include in print';
    printSel.checked = state.printSelection.has(list.list_id);
    printSel.addEventListener('change', () => togglePrintSelection(list));
    const printBtn = toolButton('\u{1F5A8}', 'Print this paper', () => {
        state.printSelection = new Set([list.list_id]);
        render();
        window.print();
    });
    const awayBtn = toolButton('\u{1F5C4}', 'Put away (z)', () => putAwayDialog(list));
    tools.append(printSel, printBtn, awayBtn);
    header.append(tools);
    el.append(header);

    const ul = document.createElement('ul');
    ul.className = 'cards';
    let anyMatch = false;
    for (const card of list.cards) {
        const li = cardEl(card, list, q);
        if (q && li.classList.contains('match')) anyMatch = true;
        ul.append(li);
    }
    el.append(ul);

    const blank = document.createElement('div');
    blank.className = 'blank-lines';
    blank.title = 'Add a task (n)';
    blank.addEventListener('click', () => newCard(list));
    el.append(blank);

    if (q && !anyMatch) el.classList.add('dimmed');

    if (isWoken(list)) {
        el.classList.add('woken');
        el.title = 'Woke up — click to keep on the desk';
        el.addEventListener('pointerdown', () => guard(async () => {
            const updated = await api.patchList(list.list_id,
                { board_order: orderAtEnd(), list_wakeup: null });
            state.papers.set(list.list_id, { ...state.papers.get(list.list_id), ...updated });
            render();
        }), { once: true });
    }

    setupPaperDrag(el, header, list);
    return el;
}

function cardEl(card, list, q) {
    const li = document.createElement('li');
    li.className = 'card';
    li.dataset.cardId = card.card_id;
    li.tabIndex = 0;
    li.style.setProperty('--cat-color', categoryColor(card.category_id));

    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = card.card_name;
    name.addEventListener('dblclick', () => editCard(card, list));
    li.append(name);

    if (card.card_due) {
        const due = document.createElement('span');
        due.className = 'due';
        due.textContent = card.card_due;
        li.append(due);
    }

    const cat = document.createElement('span');
    cat.className = 'cat'; // shown only in print
    const category = state.categories.get(card.category_id);
    cat.textContent = category ? category.category_name : '';
    li.append(cat);

    li.append(toolButton('✎', 'Edit (e)', () => editCard(card, list)));
    li.append(toolButton('✓', 'Done (c)', () => doCloseCard(card, list)));

    if (state.picked === card.card_id) li.classList.add('picked');
    if (q) li.classList.add(card.card_name.toLowerCase().includes(q) ? 'match' : 'dimmed');

    li.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.target === li) editCard(card, list);
    });

    setupCardDrag(li, card, list);
    return li;
}

function toolButton(glyph, title, onClick) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = glyph;
    btn.title = title;
    btn.tabIndex = -1;
    btn.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
    return btn;
}

function renderDrawer() {
    drawerEl.hidden = !state.drawerOpen;
    drawerTabsEl.textContent = '';
    drawerEmptyEl.hidden = state.drawer.length > 0;
    for (const list of state.drawer) {
        const li = document.createElement('li');
        li.tabIndex = 0;
        li.textContent = list.list_name;
        if (list.list_wakeup) {
            const wake = document.createElement('span');
            wake.className = 'wake';
            wake.textContent = `wakes ${list.list_wakeup}`;
            li.append(wake);
        }
        const pull = () => guard(() => pullOut(list.list_id));
        li.addEventListener('click', pull);
        li.addEventListener('keydown', (e) => { if (e.key === 'Enter') pull(); });
        drawerTabsEl.append(li);
    }
}

/* ---------- paper actions ---------- */

function newPaper() {
    guard(async () => {
        const created = await api.createList(
            { list_name: 'Untitled', board_order: orderAtEnd() });
        state.papers.set(created.list_id, { ...created, cards: [] });
        state.focus = { listId: created.list_id, cardId: null };
        render();
        renamePaper(state.papers.get(created.list_id));
    });
}

function renamePaper(list) {
    const h2 = deskEl.querySelector(`.paper[data-list-id="${list.list_id}"] h2`);
    if (!h2) return;
    h2.textContent = '';
    h2.append(inlineForm({
        value: list.list_name === 'Untitled' ? '' : list.list_name,
        onCommit: (v) => guard(async () => {
            const updated = await api.patchList(list.list_id, { list_name: v.name });
            state.papers.set(list.list_id, { ...state.papers.get(list.list_id), ...updated });
            render();
        }),
        onCancel: render,
    }));
}

function putAwayDialog(list) {
    awayTarget = list;
    awayNameEl.textContent = list.list_name;
    awayDateEl.value = '';
    awayDialog.showModal();
}

awayDialog.addEventListener('close', () => {
    const list = awayTarget;
    awayTarget = null;
    if (awayDialog.returnValue !== 'ok' || !list) return;
    const wakeup = awayDateEl.value || null;
    guard(async () => {
        await api.patchList(list.list_id, { board_order: null, list_wakeup: wakeup });
        state.focus = { listId: null, cardId: null };
        await reload();
    });
});

async function pullOut(listId) {
    await api.patchList(listId, { board_order: orderAtEnd(), list_wakeup: null });
    await reload();
    state.focus = { listId, cardId: null };
    restoreFocus();
}

function movePaper(list, dir) {
    const ids = deskPapers().map((p) => p.list_id);
    const i = ids.indexOf(list.list_id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    ids.splice(i, 1);
    ids.splice(j, 0, list.list_id);
    state.focus.listId = list.list_id;
    guard(() => placePaperAt(list.list_id, ids));
}

/* ---------- card actions ---------- */

function newCard(list) {
    const ul = deskEl.querySelector(`.paper[data-list-id="${list.list_id}"] .cards`);
    if (!ul || ul.querySelector('.inline-form')) return;
    const li = document.createElement('li');
    li.append(inlineForm({
        withCategory: true,
        categoryId: state.lastCategory,
        onCommit: (v) => guard(async () => {
            state.lastCategory = v.categoryId;
            const created = await api.createCard(list.list_id,
                { card_name: v.name, category_id: v.categoryId });
            state.focus = { listId: list.list_id, cardId: created.card_id };
            await refreshPapers([list.list_id]);
            render();
            newCard(state.papers.get(list.list_id)); // rapid entry until Escape
        }),
        onCancel: render,
    }));
    ul.append(li);
    li.querySelector('input[type="text"]').focus();
}

function editCard(card, list) {
    const li = deskEl.querySelector(`.card[data-card-id="${card.card_id}"]`);
    if (!li) return;
    li.textContent = '';
    li.append(inlineForm({
        value: card.card_name,
        withDate: true,
        date: card.card_due,
        onCommit: (v) => guard(async () => {
            await api.patchCard(card.card_id, { card_name: v.name, card_due: v.date });
            await refreshPapers([list.list_id]);
            render();
        }),
        onCancel: render,
    }));
    li.querySelector('input[type="text"]').focus();
}

function doCloseCard(card, list) {
    guard(async () => {
        await api.closeCard(card.card_id);
        if (state.focus.cardId === card.card_id) state.focus.cardId = null;
        if (state.picked === card.card_id) state.picked = null;
        // refresh the source and any on-desk "closed" paper the card landed on
        const affected = [list.list_id,
            ...deskPapers().filter((p) => p.list_closed).map((p) => p.list_id)];
        await refreshPapers(affected);
        render();
    });
}

/* ---------- inline editing ---------- */

function inlineForm({ value = '', date = null, categoryId = DEFAULT_CATEGORY,
                      withDate = false, withCategory = false, onCommit, onCancel }) {
    const form = document.createElement('form');
    form.className = 'inline-form';
    let done = false;

    const name = document.createElement('input');
    name.type = 'text';
    name.value = value;
    form.append(name);

    let dateInput = null;
    if (withDate) {
        dateInput = document.createElement('input');
        dateInput.type = 'date';
        dateInput.value = date || '';
        form.append(dateInput);
    }

    let catSelect = null;
    if (withCategory) {
        catSelect = document.createElement('select');
        for (const cat of state.categories.values()) {
            const opt = document.createElement('option');
            opt.value = cat.category_id;
            opt.textContent = cat.category_name;
            opt.selected = cat.category_id === categoryId;
            catSelect.append(opt);
        }
        form.append(catSelect);
    }

    const finish = (commit) => {
        if (done) return;
        done = true;
        if (commit) {
            onCommit({
                name: name.value.trim(),
                date: dateInput ? (dateInput.value || null) : undefined,
                categoryId: catSelect ? Number(catSelect.value) : undefined,
            });
        } else {
            onCancel();
        }
    };

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        finish(Boolean(name.value.trim()));
    });
    form.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { e.stopPropagation(); finish(false); }
    });
    form.addEventListener('focusout', (e) => {
        if (!form.contains(e.relatedTarget)) finish(Boolean(name.value.trim()));
    });
    return form;
}

/* ---------- drag & drop (pointer events) ---------- */

function setupPaperDrag(el, header, list) {
    header.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        if (e.target.closest('button, input, select, .inline-form')) return;
        const startX = e.clientX;
        const startY = e.clientY;
        let dragging = false;

        const onMove = (ev) => {
            if (!dragging) {
                if (Math.hypot(ev.clientX - startX, ev.clientY - startY) < DRAG_THRESHOLD) return;
                dragging = true;
                el.classList.add('drag');
            }
            const siblings = [...deskEl.querySelectorAll('.paper')].filter((p) => p !== el);
            let before = null;
            for (const sib of siblings) {
                const r = sib.getBoundingClientRect();
                if (ev.clientX < r.left + r.width / 2) { before = sib; break; }
            }
            if (before) deskEl.insertBefore(el, before);
            else deskEl.append(el);
        };
        const onUp = () => {
            document.removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerup', onUp);
            document.removeEventListener('pointercancel', onUp);
            if (!dragging) {
                state.focus = { listId: list.list_id, cardId: null };
                header.querySelector('h2')?.focus();
                return;
            }
            el.classList.remove('drag');
            const rowIds = [...deskEl.querySelectorAll('.paper')]
                .map((p) => Number(p.dataset.listId));
            state.focus = { listId: list.list_id, cardId: null };
            guard(() => placePaperAt(list.list_id, rowIds));
        };
        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
    });
}

function setupCardDrag(li, card, list) {
    li.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        if (e.target.closest('button, input, select, .inline-form')) return;
        const startX = e.clientX;
        const startY = e.clientY;
        const originListId = list.list_id;
        const originPrev = li.previousElementSibling;
        let dragging = false;
        let clone = null;

        const onMove = (ev) => {
            if (!dragging) {
                if (Math.hypot(ev.clientX - startX, ev.clientY - startY) < DRAG_THRESHOLD) return;
                dragging = true;
                clone = li.cloneNode(true);
                clone.id = 'drag-clone';
                document.body.append(clone);
                li.classList.add('drop-slot');
            }
            clone.style.left = `${ev.clientX + 8}px`;
            clone.style.top = `${ev.clientY - 12}px`;
            const under = document.elementFromPoint(ev.clientX, ev.clientY);
            const paper = under && under.closest('.paper');
            if (!paper) return;
            const ul = paper.querySelector('.cards');
            let before = null;
            for (const sib of ul.children) {
                if (sib === li || !sib.classList.contains('card')) continue;
                const r = sib.getBoundingClientRect();
                if (ev.clientY < r.top + r.height / 2) { before = sib; break; }
            }
            if (before) ul.insertBefore(li, before);
            else ul.append(li);
        };
        const onUp = () => {
            document.removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerup', onUp);
            document.removeEventListener('pointercancel', onUp);
            if (!dragging) {
                li.focus();
                return;
            }
            clone.remove();
            li.classList.remove('drop-slot');
            const destPaper = li.closest('.paper');
            const destListId = Number(destPaper.dataset.listId);
            if (destListId === originListId && li.previousElementSibling === originPrev) {
                li.focus();
                return; // dropped back where it started
            }
            const prev = li.previousElementSibling;
            const next = li.nextElementSibling;
            const payload = { list_id: destListId };
            if (prev && prev.classList.contains('card')) {
                payload.after_card = Number(prev.dataset.cardId);
            } else if (next && next.classList.contains('card')) {
                payload.before_card = Number(next.dataset.cardId);
            }
            state.focus = { listId: destListId, cardId: card.card_id };
            guard(() => doMoveCard(card.card_id, payload, [originListId, destListId]));
        };
        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
    });
}

/* ---------- keyboard ---------- */

function navigate(key) {
    if (state.picked !== null) { movePicked(key); return; }
    const papers = deskPapers();
    if (!papers.length) return;
    const list = currentPaper();
    const cards = list.cards;
    const idx = cards.findIndex((c) => c.card_id === state.focus.cardId);
    if (key === 's') {
        if (idx < cards.length - 1) {
            state.focus = { listId: list.list_id, cardId: cards[idx + 1].card_id };
        }
    } else if (key === 'w') {
        if (idx > 0) {
            state.focus = { listId: list.list_id, cardId: cards[idx - 1].card_id };
        } else {
            state.focus = { listId: list.list_id, cardId: null }; // up to the header
        }
    } else {
        const pi = papers.indexOf(list);
        const target = papers[pi + (key === 'd' ? 1 : -1)];
        if (!target) return;
        state.focus = {
            listId: target.list_id,
            cardId: target.cards.length ? target.cards[0].card_id : null,
        };
    }
    restoreFocus();
}

function movePicked(key) {
    const list = state.papers.get(state.focus.listId);
    if (!list) return;
    const cards = list.cards;
    const idx = cards.findIndex((c) => c.card_id === state.picked);
    if (idx < 0) return;
    let payload = null;
    let affected = [list.list_id];
    if (key === 'w' && idx > 0) {
        payload = { list_id: list.list_id, before_card: cards[idx - 1].card_id };
    } else if (key === 's' && idx < cards.length - 1) {
        payload = { list_id: list.list_id, after_card: cards[idx + 1].card_id };
    } else if (key === 'a' || key === 'd') {
        const papers = deskPapers();
        const target = papers[papers.indexOf(list) + (key === 'd' ? 1 : -1)];
        if (!target) return;
        payload = { list_id: target.list_id };
        affected = [list.list_id, target.list_id];
        state.focus.listId = target.list_id;
    }
    if (!payload) return;
    state.focus.cardId = state.picked;
    guard(() => doMoveCard(state.picked, payload, affected));
}

function pickDrop() {
    if (state.picked !== null) {
        state.picked = null;
    } else if (state.focus.cardId !== null) {
        state.picked = state.focus.cardId;
    }
    render();
}

function togglePrintSelection(list) {
    if (state.printSelection.has(list.list_id)) state.printSelection.delete(list.list_id);
    else state.printSelection.add(list.list_id);
    render();
}

function toggleDrawer() {
    state.drawerOpen = !state.drawerOpen;
    renderDrawer();
}

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return;
    if (e.target.closest('input, textarea, select')) return;
    if (awayDialog.open) return;
    const list = currentPaper();
    const card = list && list.cards.find((c) => c.card_id === state.focus.cardId);
    switch (e.key) {
        case 'w': case 's': case 'a': case 'd': navigate(e.key); break;
        case 'n': if (list) newCard(list); break;
        case 'e': case 'Enter':
            if (card) editCard(card, list);
            else if (e.key === 'Enter' && list && e.target.tagName === 'H2') renamePaper(list);
            else return;
            break;
        case 'm': pickDrop(); break;
        case 'c': if (card) doCloseCard(card, list); break;
        case 'N': newPaper(); break;
        case 'A': if (list) movePaper(list, -1); break;
        case 'D': if (list) movePaper(list, 1); break;
        case 'r': if (list) renamePaper(list); break;
        case 'z': if (list) putAwayDialog(list); break;
        case 'b': toggleDrawer(); break;
        case '/': case 'u': upsertInput.focus(); upsertInput.select(); break;
        case 'p': if (list) togglePrintSelection(list); break;
        case 'P': window.print(); break;
        case 'g': guard(reload); break;
        case 'Escape':
            if (state.picked !== null) { state.picked = null; render(); }
            else if (upsert.query) clearUpsert();
            else if (state.drawerOpen) toggleDrawer();
            break;
        default: return;
    }
    e.preventDefault();
});

document.addEventListener('focusin', (e) => {
    const cardLi = e.target.closest('.card');
    const paper = e.target.closest('.paper');
    if (cardLi) {
        state.focus = {
            listId: Number(paper.dataset.listId),
            cardId: Number(cardLi.dataset.cardId),
        };
    } else if (paper) {
        state.focus = { listId: Number(paper.dataset.listId), cardId: null };
    }
});

/* ---------- upsert: search that becomes creation ---------- */

function upsertMatches() {
    const q = upsertQuery();
    const out = [];
    if (!q) return out;
    for (const l of deskPapers()) {
        for (const c of l.cards) {
            if (c.card_name.toLowerCase().includes(q)) out.push({ card: c, list: l, away: false });
        }
    }
    if (upsert.scope === 'all') {
        for (const l of state.drawerCards.values()) {
            for (const c of l.cards) {
                if (c.card_name.toLowerCase().includes(q)) out.push({ card: c, list: l, away: true });
            }
        }
    }
    return out.slice(0, 12);
}

function upsertTarget() {
    return currentPaper();
}

function renderUpsert() {
    const q = upsert.query.trim();
    upsertResultsEl.textContent = '';
    upsertResultsEl.hidden = !q;
    render(); // applies match/dim highlighting from the current query
    if (!q) return;
    upsert.results = upsertMatches();
    upsert.sel = Math.min(upsert.sel, upsert.results.length);
    upsert.results.forEach((r, i) => {
        const li = document.createElement('li');
        if (i === upsert.sel) li.classList.add('selected');
        const name = document.createElement('span');
        name.textContent = r.card.card_name;
        const where = document.createElement('span');
        where.className = 'where';
        where.textContent = r.list.list_name + (r.away ? ' (drawer)' : '');
        li.append(name, where);
        li.addEventListener('click', () => activateResult(r));
        upsertResultsEl.append(li);
    });
    const target = upsertTarget();
    const create = document.createElement('li');
    create.className = 'create';
    if (upsert.sel === upsert.results.length) create.classList.add('selected');
    create.textContent = target
        ? `✚ Add “${q}” to ${target.list_name}`
        : 'No papers on the desk — create one first (N)';
    if (target) create.addEventListener('click', createFromUpsert);
    upsertResultsEl.append(create);
}

function activateResult(r) {
    if (r.away) {
        guard(async () => {
            await pullOut(r.list.list_id);
            clearUpsert();
            state.focus = { listId: r.list.list_id, cardId: r.card.card_id };
            restoreFocus();
        });
    } else {
        clearUpsert();
        state.focus = { listId: r.list.list_id, cardId: r.card.card_id };
        restoreFocus();
    }
}

function createFromUpsert() {
    const target = upsertTarget();
    const cardName = upsert.query.trim();
    if (!target || !cardName) return;
    guard(async () => {
        const created = await api.createCard(target.list_id,
            { card_name: cardName, category_id: state.lastCategory });
        state.focus = { listId: target.list_id, cardId: created.card_id };
        await refreshPapers([target.list_id]);
        clearUpsert();
        restoreFocus();
    });
}

function clearUpsert() {
    upsertInput.value = '';
    upsert.query = '';
    upsert.results = [];
    upsert.sel = 0;
    upsertResultsEl.hidden = true;
    upsertInput.blur();
    render();
}

upsertInput.addEventListener('input', () => {
    upsert.query = upsertInput.value;
    upsert.sel = 0;
    renderUpsert();
});

upsertInput.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
        upsert.sel = Math.min(upsert.sel + 1, upsert.results.length);
    } else if (e.key === 'ArrowUp') {
        upsert.sel = Math.max(upsert.sel - 1, 0);
    } else if (e.key === 'Enter') {
        if (upsert.sel < upsert.results.length) activateResult(upsert.results[upsert.sel]);
        else createFromUpsert();
        return;
    } else if (e.key === 'Escape') {
        clearUpsert();
        return;
    } else {
        return;
    }
    e.preventDefault();
    renderUpsert();
});

upsertScopeBtn.addEventListener('click', () => {
    guard(async () => {
        if (upsert.scope === 'visible') {
            upsert.scope = 'all';
            const full = await Promise.all(state.drawer.map((l) => api.getList(l.list_id)));
            state.drawerCards = new Map(full.map((l) => [l.list_id, l]));
        } else {
            upsert.scope = 'visible';
        }
        upsertScopeBtn.textContent = upsert.scope;
        renderUpsert();
        upsertInput.focus();
    });
});

/* ---------- printing ---------- */

window.addEventListener('beforeprint', () => {
    if (!state.printSelection.size) {
        document.body.classList.add('print-all');
    } else {
        for (const p of deskEl.querySelectorAll('.paper')) {
            p.classList.toggle('print-selected',
                state.printSelection.has(Number(p.dataset.listId)));
        }
    }
});

window.addEventListener('afterprint', () => {
    document.body.classList.remove('print-all');
    for (const p of deskEl.querySelectorAll('.print-selected')) {
        p.classList.remove('print-selected');
    }
});

/* ---------- toolbar & init ---------- */

document.getElementById('new-paper-btn').addEventListener('click', newPaper);
document.getElementById('drawer-btn').addEventListener('click', toggleDrawer);
document.getElementById('print-btn').addEventListener('click', () => window.print());
document.getElementById('refresh-btn').addEventListener('click', () => guard(reload));

window.addEventListener('focus', () => {
    if (Date.now() - lastLoad > 5000 && !document.querySelector('.inline-form')) {
        guard(reload);
    }
});

guard(reload);
