<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import { slide } from 'svelte/transition';

	import { onDestroy, onMount, tick } from 'svelte';
	import { mobile, showControls, showCallOverlay, showOverview, showArtifacts } from '$lib/stores';

	import Controls from './Controls/Controls.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import Drawer from '../common/Drawer.svelte';
	import Overview from './Overview.svelte';
	import Artifacts from './Artifacts.svelte';

	export let history;
	export let models = [];

	export let chatId = null;

	export let chatFiles = [];
	export let params = {};

	export let eventTarget: EventTarget;
	export let submitPrompt: Function;
	export let stopResponse: Function;
	export let showMessage: Function;
	export let files;
	export let modelId;

	let mediaQuery;
	let largeScreen = false;

	onMount(() => {
		mediaQuery = window.matchMedia('(min-width: 1024px)');
		const handler = (e) => (largeScreen = e.matches);
		mediaQuery.addEventListener('change', handler);
		largeScreen = mediaQuery.matches;
	});

	onDestroy(() => {
		showControls.set(false);
		mediaQuery?.removeEventListener('change', () => {});
	});

	const closeHandler = () => {
		showControls.set(false);
		showOverview.set(false);
		showArtifacts.set(false);

		if ($showCallOverlay) {
			showCallOverlay.set(false);
		}
	};

	$: if (!chatId) {
		closeHandler();
	}
</script>


<SvelteFlowProvider>
	{#if !largeScreen}
		{#if $showControls}
			<Drawer
				show={$showControls}
				onClose={() => {
					showControls.set(false);
				}}
			>
				<div
					class=" {$showCallOverlay || $showOverview || $showArtifacts
						? ' h-screen  w-full'
						: 'px-6 py-4'} h-full"
				>
					{#if $showCallOverlay}
						<div
							class=" h-full max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
						>
							<CallOverlay
								bind:files
								{submitPrompt}
								{stopResponse}
								{modelId}
								{chatId}
								{eventTarget}
								on:close={() => {
									showControls.set(false);
								}}
							/>
						</div>
					{:else if $showArtifacts}
						<Artifacts {history} />
					{:else if $showOverview}
						<Overview
							{history}
							on:nodeclick={(e) => {
								showMessage(e.detail.node.data.message);
							}}
							on:close={() => {
								showControls.set(false);
							}}
						/>
					{:else}
						<Controls
							on:close={() => {
								showControls.set(false);
							}}
							{models}
							bind:chatFiles
							bind:params
						/>
					{/if}
				</div>
			</Drawer>
		{/if}
	{:else}
		{#if $showControls}
			<div class="relative z-10 max-w-xs w-[350px] h-full flex flex-col border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg">
				<div class="flex-1 overflow-y-auto scrollbar-hidden px-4 py-4">
					{#if $showCallOverlay}
						<CallOverlay
							bind:files
							{submitPrompt}
							{stopResponse}
							{modelId}
							{chatId}
							{eventTarget}
							on:close={() => { showControls.set(false); }}
						/>
					{:else if $showArtifacts}
						<Artifacts {history} />
					{:else if $showOverview}
						<Overview
							{history}
							on:nodeclick={(e) => { showMessage(e.detail.node.data.message); }}
							on:close={() => { showControls.set(false); }}
						/>
					{:else}
						<Controls
							on:close={() => { showControls.set(false); }}
							{models}
							bind:chatFiles
							bind:params
						/>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</SvelteFlowProvider>
