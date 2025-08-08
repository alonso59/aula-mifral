import { writable } from 'svelte/store';

// Whether the Virtual Classroom feature is enabled (determined at runtime)
export const classroomEnabled = writable(false);
