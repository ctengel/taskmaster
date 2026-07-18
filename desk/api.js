/* Thin fetch wrapper over the TaskMaster KanBan API (same origin). */

async function api(method, path, body) {
    const opts = { method };
    if (body !== undefined) {
        opts.headers = { 'Content-Type': 'application/json' };
        opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    if (!res.ok) {
        throw new Error(`${method} ${path} failed (${res.status})`);
    }
    return res.json();
}

export const getCategories = () => api('GET', '/categories/');
export const getLists = (away) => api('GET', away === undefined ? '/lists/' : `/lists/?away=${away}`);
export const getList = (listId) => api('GET', `/lists/${listId}`);
export const createList = (data) => api('POST', '/lists/', data);
export const patchList = (listId, data) => api('PATCH', `/lists/${listId}`, data);
export const createCard = (listId, data) => api('POST', `/lists/${listId}/cards/`, data);
export const patchCard = (cardId, data) => api('PATCH', `/cards/${cardId}`, data);
export const moveCard = (cardId, data) => api('POST', `/cards/${cardId}/move`, data);
export const closeCard = (cardId) => api('POST', `/cards/${cardId}/close`, {});
export const rebalance = (listId) => api('POST', `/lists/${listId}/rebalance`, {});
