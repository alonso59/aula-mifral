<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext('i18n');

	export let showWelcome = false;
</script>

<div class="flex flex-col items-center justify-center py-8 px-4 text-center">
	{#if showWelcome && $user}
		<div class="mb-6">
			<div class="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
				<Plus className="w-8 h-8 text-gray-400" />
			</div>
			<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
				{$i18n.t('Welcome, {{name}}!', { name: $user.name || $user.email || 'User' })}
			</h3>
			<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
				{$i18n.t('Get started by creating your first chat conversation.')}
			</p>
		</div>
	{:else}
		<div class="mb-6">
			<div class="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-3">
				<Plus className="w-6 h-6 text-gray-400" />
			</div>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('No conversations yet')}
			</p>
		</div>
	{/if}

	<a
		href="/"
		class="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
	>
		<Plus className="w-4 h-4 mr-2" />
		{$i18n.t('Start New Chat')}
	</a>
</div>

