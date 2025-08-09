import { chats, currentChatPage } from '$lib/stores';
import { get } from 'svelte/store';
import { getChatList } from '$lib/apis/chats';

let fetching = false;

/**
 * Refresh chats list with optional page reset.
 * Prevents overlapping fetches.
 */
export async function refreshChats(reset = true) {
  if (fetching) return;
  fetching = true;
  try {
    if (reset) currentChatPage.set(1);
    chats.set(await getChatList(localStorage.token, get(currentChatPage)));
  } catch (e) {
    console.error('Error refreshing chats', e);
  } finally {
    fetching = false;
  }
}
