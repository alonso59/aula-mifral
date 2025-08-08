// @ts-nocheck
// Simple Svelte store to control visibility of the document panel
import { writable } from 'svelte/store';

// Whether the left document/classroom navigation panel is shown
export const showDocumentPanel = writable(false);

// Whether the right course workspace panel is shown
export const showCourseWorkspace = writable(false);

// Currently selected course context for the workspace panel
export const documentPanelCourse = writable(null);

// Helper to toggle visibility (persists to localStorage)
export function toggleDocumentPanel(forceValue = null) {
	if (forceValue === true || forceValue === false) {
		showDocumentPanel.set(forceValue);
		try { localStorage.setItem('showDocumentPanel', JSON.stringify(forceValue)); } catch {}
		return;
	}
	let next;
	showDocumentPanel.update((v) => {
		next = !v;
		return next;
	});
	try { localStorage.setItem('showDocumentPanel', JSON.stringify(next)); } catch {}
}

// Helper to set course for the panel
export function setDocumentPanelCourse(course) {
	documentPanelCourse.set(course || null);
}

// Initialize from localStorage on import
try {
	const raw = localStorage.getItem('showDocumentPanel');
	if (raw !== null) {
		const v = JSON.parse(raw);
		if (typeof v === 'boolean') showDocumentPanel.set(v);
	}
} catch {}

// Toggle and bootstrap persistence for right course workspace
export function toggleCourseWorkspace(forceValue = null) {
	if (forceValue === true || forceValue === false) {
		showCourseWorkspace.set(forceValue);
		try {
			localStorage.setItem('showCourseWorkspace', JSON.stringify(forceValue));
		} catch {}
		return;
	}
	let next;
	showCourseWorkspace.update((v) => {
		next = !v;
		return next;
	});
	try {
		localStorage.setItem('showCourseWorkspace', JSON.stringify(next));
	} catch {}
}

try {
	const raw = localStorage.getItem('showCourseWorkspace');
	if (raw !== null) {
		const v = JSON.parse(raw);
		if (typeof v === 'boolean') showCourseWorkspace.set(v);
	}
} catch {}
