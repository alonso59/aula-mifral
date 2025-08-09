import { writable } from 'svelte/store';

// Whether the Virtual Classroom feature is enabled (determined at runtime)
export const classroomEnabled = writable(false);

// User preference: embed classroom panel inside chat (admins/teachers only)
export const classroomEmbedInChat = writable(false);

// Persist preference to localStorage
if (typeof window !== 'undefined') {
	classroomEmbedInChat.subscribe((val: boolean) => {
		try { localStorage.setItem('classroom:embed', String(val)); } catch {}
	});
}
