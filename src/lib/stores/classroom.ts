import { writable } from 'svelte/store';

// Whether the Virtual Classroom feature is enabled (determined at runtime)
export const classroomEnabled = writable(false);

// User preference: embed classroom panel inside chat (admins/teachers only)
export const classroomEmbedInChat = writable(true);

// UI toggles for classroom layout
export const showCourseList = writable(false);
export const showRightPanel = writable(false);

// Persist preference to localStorage
if (typeof window !== 'undefined') {
	classroomEmbedInChat.subscribe((val: boolean) => {
		try { localStorage.setItem('classroom:embed', String(val)); } catch {}
	});

	// initialize default based on viewport width
	try {
		const w = window.innerWidth;
		// lg+ (1024px) show both panels
		showCourseList.set(w >= 1024);
		showRightPanel.set(w >= 1024);
	} catch {}
}
