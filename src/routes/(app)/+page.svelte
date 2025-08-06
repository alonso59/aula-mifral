<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user, chats } from '$lib/stores';
	import Chat from '$lib/components/chat/Chat.svelte';
	import WelcomePage from '$lib/components/layout/WelcomePage.svelte';
	import { getChatList } from '$lib/apis/chats';
	
	const i18n = getContext('i18n');
	
	let hasContent = false;
	let loading = true;
	
	onMount(async () => {
		try {
			// Check if user has any chats or courses
			const userChats = await getChatList(localStorage.getItem('token'), 1).catch(() => []);
			
			// For now, we'll just check if there are chats
			// In the future, we could also check for courses here
			hasContent = userChats && userChats.length > 0;
			
		} catch (error) {
			console.error('Error checking user content:', error);
			hasContent = false;
		}
		
		loading = false;
	});
</script>

{#if loading}
	<div class="w-full h-full flex items-center justify-center">
		<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
	</div>
{:else if hasContent}
	<Chat />
{:else}
	<WelcomePage />
{/if}

