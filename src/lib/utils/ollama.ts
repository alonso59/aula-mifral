import { writable } from 'svelte/store';

export const ollamaAvailable = writable<boolean | null>(null);

/**
 * Detect Ollama availability with exponential backoff retries.
 * Updates the `ollamaAvailable` writable store with true/false.
 */
export async function detectOllamaWithRetry(retries = 3, delayMs = 1000) {
	for (let attempt = 0; attempt < retries; attempt++) {
		try {
			const res = await fetch('/ollama/api/version');
			if (res.ok) {
				ollamaAvailable.set(true);
				return;
			} else {
				ollamaAvailable.set(false);
			}
		} catch (e) {
			ollamaAvailable.set(false);
		}
		// wait with exponential backoff before next attempt
		await new Promise((r) => setTimeout(r, delayMs * Math.pow(2, attempt)));
	}
	// If all retries exhausted and none succeeded, ensure store is false
	ollamaAvailable.set(false);
}
