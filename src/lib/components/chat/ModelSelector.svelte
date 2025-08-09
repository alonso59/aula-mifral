<script lang="ts">
	import { settings, user, mobile, config, models } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Selector from './ModelSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import { updateUserSettings } from '$lib/apis/users';
	import { getModelsConfig } from '$lib/apis/configs';
	const i18n = getContext('i18n');

	export let selectedModels = [''];
	export let disabled = false;
	export let showSetDefault = true;

	const pinModelHandler = async (modelId) => {
		let pinnedModels = $settings?.pinnedModels ?? [];

		if (pinnedModels.includes(modelId)) {
			pinnedModels = pinnedModels.filter((id) => id !== modelId);
		} else {
			pinnedModels = [...new Set([...pinnedModels, modelId])];
		}

		settings.set({ ...$settings, pinnedModels: pinnedModels });
		await updateUserSettings(localStorage.getItem('token'), { ui: $settings });
	};

	let defaultModelsConfig = null;

	// Load default models configuration and apply for non-admin users
	const loadDefaultModels = async () => {
		try {
			defaultModelsConfig = await getModelsConfig(localStorage.getItem('token'));
			if (defaultModelsConfig?.DEFAULT_MODELS) {
				const defaultModelIds = defaultModelsConfig.DEFAULT_MODELS.split(',').filter((id) => id.trim());
				if (defaultModelIds.length > 0) {
					// For non-admin users, always use admin-configured default models
					if ($user?.role !== 'admin') {
						selectedModels = defaultModelIds;
						// Also save this selection to user settings to persist it
						settings.set({ ...$settings, models: defaultModelIds });
						await updateUserSettings(localStorage.getItem('token'), { ui: { ...$settings, models: defaultModelIds } });
					} else if (selectedModels.length === 1 && selectedModels[0] === '') {
						// If admin has no selection, use defaults as starting point
						selectedModels = defaultModelIds;
					}
				}
			} else if ($user?.role !== 'admin') {
				// If no default models are configured and user is not admin, show error
				toast.error($i18n.t('No models have been assigned by your administrator. Please contact support.'));
			}
		} catch (error) {
			console.warn('Could not load default models config:', error);
			if ($user?.role !== 'admin') {
				toast.error($i18n.t('Unable to load model configuration. Please contact your administrator.'));
			}
		}
	};

	const saveDefaultModel = async () => {
		const hasEmptyModel = selectedModels.filter((it) => it === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}

		// For admin users, save both personal preference and system defaults
		if ($user?.role === 'admin') {
			// Save personal preference
			settings.set({ ...$settings, models: selectedModels });
			await updateUserSettings(localStorage.getItem('token'), { ui: $settings });
			
			// Also save as system default for all users
			try {
				const { setModelsConfig } = await import('$lib/apis/configs');
				await setModelsConfig(localStorage.getItem('token'), {
					DEFAULT_MODELS: selectedModels.join(',')
				});
				toast.success($i18n.t('Default models updated for all users'));
			} catch (error) {
				console.error('Failed to set system default models:', error);
				toast.error($i18n.t('Failed to set system default models'));
			}
		} else {
			// For regular users, just save personal preference
			settings.set({ ...$settings, models: selectedModels });
			await updateUserSettings(localStorage.getItem('token'), { ui: $settings });
			toast.success($i18n.t('Default model updated'));
		}
	};

	onMount(() => {
		loadDefaultModels();
	});

	// Reactive statement to reload models when user changes
	$: if ($user) {
		loadDefaultModels();
	}

	$: if (selectedModels.length > 0 && $models.length > 0) {
		selectedModels = selectedModels.map((model) =>
			$models.map((m) => m.id).includes(model) ? model : ''
		);
	}
</script>

<div class="flex flex-col w-full items-start">
{#if $models.length === 0}
	<div class="text-lg text-gray-500 dark:text-gray-400 mb-4">No models available. Please add a model in the workspace.</div>
{:else if $user?.role === 'admin'}
	<!-- Admin users see the full model selector -->
	{#each selectedModels as selectedModel, selectedModelIdx}
		<div class="flex w-full max-w-fit">
			<div class="overflow-hidden w-full">
				<div class="max-w-full {($settings?.highContrastMode ?? false) ? 'm-1' : 'mr-1'}">
					<Selector
						id={`${selectedModelIdx}`}
						placeholder={$i18n.t('Select a model')}
						items={$models.map((model) => ({
							value: model.id,
							label: model.name,
							model: model
						}))}
						showTemporaryChatControl={$user?.role === 'user'
							? ($user?.permissions?.chat?.temporary ?? true) &&
								!($user?.permissions?.chat?.temporary_enforced ?? false)
							: true}
						{pinModelHandler}
						bind:value={selectedModel}
					/>
				</div>
			</div>

			{#if $user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true)}
				{#if selectedModelIdx === 0}
					<div
						class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]"
					>
						<Tooltip content={$i18n.t('Add Model')}>
							<button
								class=" "
								{disabled}
								on:click={() => {
									selectedModels = [...selectedModels, ''];
								}}
								aria-label="Add Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3.5"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{:else}
					<div
						class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]"
					>
						<Tooltip content={$i18n.t('Remove Model')}>
							<button
								{disabled}
								on:click={() => {
									selectedModels.splice(selectedModelIdx, 1);
									selectedModels = selectedModels;
								}}
								aria-label="Remove Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{/if}
			{/if}
		</div>
	{/each}
{:else}
	<!-- Regular users see a read-only display of assigned models -->
	<div class="flex flex-col w-full">
		<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
			{$i18n.t('Assigned Models')}:
		</div>
		{#if selectedModels.length > 0 && selectedModels[0] !== ''}
			{#each selectedModels as selectedModel}
				{#if selectedModel && $models.find(m => m.id === selectedModel)}
					<div class="flex items-center py-2 px-3 rounded bg-gray-100 dark:bg-gray-800 mb-2 max-w-fit">
						<span class="text-sm font-medium">
							{$models.find(m => m.id === selectedModel)?.name || selectedModel}
						</span>
					</div>
				{/if}
			{/each}
		{:else}
			<div class="text-sm text-gray-500 dark:text-gray-400 p-3 border border-dashed border-gray-300 dark:border-gray-600 rounded">
				{$i18n.t('No models assigned. Please contact your administrator.')}
			</div>
		{/if}
	</div>
{/if}
</div>

{#if showSetDefault && $user?.role === 'admin'}
	<div
		class="absolute text-left mt-[1px] ml-1 text-[0.7rem] text-gray-600 dark:text-gray-400 font-primary"
	>
		<button on:click={saveDefaultModel}> {$i18n.t('Set as default for all users')}</button>
	</div>
{/if}
