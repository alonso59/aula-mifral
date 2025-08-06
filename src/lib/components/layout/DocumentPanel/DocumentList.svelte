<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import Plus from '../../icons/Plus.svelte';
	import DocumentIcon from '../../icons/DocumentIcon.svelte';
	import { createPicker } from '$lib/utils/google-drive-picker';
	import { toast } from 'svelte-sonner';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let documents = [];
	export let canManageDocuments = false;

	let showUploadModal = false;
	let selectedCategory = 'all';
	let searchTerm = '';
	let isGoogleDriveAvailable = false;
	let uploadType = 'local'; // 'local' or 'google-drive'
	
	// Check if Google Drive integration is available
	import { onMount } from 'svelte';
	import { getRAGConfig } from '$lib/apis/retrieval';
	
	onMount(async () => {
		try {
			// Check if Google Drive integration is enabled
			const config = await getRAGConfig(localStorage.getItem('token'));
			isGoogleDriveAvailable = config?.ENABLE_GOOGLE_DRIVE_INTEGRATION || false;
		} catch (error) {
			console.error('Error checking Google Drive availability:', error);
		}
	});

	// Filter documents based on category and search
	$: filteredDocuments = documents.filter(doc => {
		const matchesCategory = selectedCategory === 'all' || doc.category === selectedCategory;
		const matchesSearch = doc.title.toLowerCase().includes(searchTerm.toLowerCase());
		return matchesCategory && matchesSearch;
	});

	const categories = [
		{ value: 'all', label: 'All Documents' },
		{ value: 'fundamentals', label: 'Fundamentals' },
		{ value: 'design', label: 'RTL Design' },
		{ value: 'verification', label: 'Verification' },
		{ value: 'tapeout', label: 'Tapeout' }
	];

	const handleDocumentClick = (document) => {
		dispatch('documentSelected', document);
	};

	const handleUpload = () => {
		showUploadModal = true;
	};
	
	const handleGoogleDriveImport = async () => {
		try {
			const fileData = await createPicker();
			if (fileData) {
				// Create File object from the downloaded data
				const file = new File([fileData.blob], fileData.name, {
					type: fileData.blob.type || 'application/octet-stream'
				});
				
				// Process the file (you would integrate with your existing RAG processing here)
				toast.success($i18n.t('Document imported successfully from Google Drive'));
				dispatch('documentUpload');
				showUploadModal = false;
			}
		} catch (error) {
			console.error('Google Drive import error:', error);
			toast.error($i18n.t('Failed to import from Google Drive: {{error}}', { 
				error: error.message || 'Unknown error' 
			}));
		}
	};

	const getDocumentIcon = (type) => {
		switch (type) {
			case 'reference':
				return '📚';
			case 'tutorial':
				return '🎓';
			case 'checklist':
				return '✅';
			case 'code':
				return '💻';
			default:
				return '📄';
		}
	};

	const getStatusColor = (category) => {
		switch (category) {
			case 'fundamentals':
				return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
			case 'design':
				return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
			case 'verification':
				return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
			case 'tapeout':
				return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
			default:
				return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
		}
	};
</script>

<div class="space-y-4">
	<!-- Header with Upload Button -->
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-medium text-gray-900 dark:text-white">
			{$i18n.t('Documents')}
		</h3>
		{#if canManageDocuments}
			<div class="flex space-x-2">
				{#if isGoogleDriveAvailable}
					<button
						on:click={() => {
							uploadType = 'google-drive';
							showUploadModal = true;
						}}
						class="flex items-center space-x-1 px-2 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors"
						title={$i18n.t('Import from Google Drive')}
					>
						<svg class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
							<path d="M14.9 9.6L9 3.8l1.8-3.1c.2-.2.5-.2.8 0l8.5 14.6H24l-9.1-5.7z" />
							<path d="M9 3.8L2.1 15.3 0 18.4l3.7 2.3c.2.1.5.1.7-.1l5.4-9.1L9 3.8z" />
							<path d="M14.9 20.7c.2.3.5.3.7.1l3.7-2.3-1.3-2.3H8.9L3.8 20.7h11.1z" />
						</svg>
						<span>{$i18n.t('Drive')}</span>
					</button>
				{/if}
				<button
					on:click={() => {
						uploadType = 'local';
						handleUpload();
					}}
					class="flex items-center space-x-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
					title={$i18n.t('Upload document')}
				>
					<Plus className="w-3 h-3" />
					<span>{$i18n.t('Upload')}</span>
				</button>
			</div>
		{/if}
	</div>

	<!-- Search Bar -->
	<div class="relative">
		<input
			type="text"
			bind:value={searchTerm}
			placeholder={$i18n.t('Search documents...')}
			class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
		/>
		<svg class="absolute right-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
		</svg>
	</div>

	<!-- Category Filter -->
	<div class="flex flex-wrap gap-1">
		{#each categories as category}
			<button
				on:click={() => selectedCategory = category.value}
				class="px-2 py-1 text-xs rounded-full transition-colors {selectedCategory === category.value 
					? 'bg-blue-600 text-white' 
					: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
			>
				{$i18n.t(category.label)}
			</button>
		{/each}
	</div>

	<!-- Documents List -->
	<div class="space-y-2 max-h-96 overflow-y-auto">
		{#if filteredDocuments.length === 0}
			<div class="text-center py-8 text-gray-500 dark:text-gray-400">
				<DocumentIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
				<p class="text-sm">
					{searchTerm || selectedCategory !== 'all' 
						? $i18n.t('No documents match your filters') 
						: $i18n.t('No documents available')}
				</p>
			</div>
		{:else}
			{#each filteredDocuments as document}
				<div
					class="p-3 border border-gray-200 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
					on:click={() => handleDocumentClick(document)}
					role="button"
					tabindex="0"
					on:keydown={(e) => e.key === 'Enter' && handleDocumentClick(document)}
				>
					<div class="flex items-start space-x-3">
						<div class="text-lg flex-shrink-0 mt-0.5">
							{getDocumentIcon(document.type)}
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center justify-between">
								<h4 class="text-sm font-medium text-gray-900 dark:text-white truncate">
									{document.title}
								</h4>
								<span class="text-xs px-2 py-1 rounded-full {getStatusColor(document.category)}">
									{$i18n.t(document.category)}
								</span>
							</div>
							<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
								<div class="flex items-center justify-between">
									<span>{$i18n.t('By')} {document.uploadedBy}</span>
									<span>{new Date(document.uploadDate).toLocaleDateString()}</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>

<!-- Upload Modal -->
{#if showUploadModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-96 max-w-[90vw]">
			<h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
				{uploadType === 'local' ? $i18n.t('Upload Document') : $i18n.t('Import from Google Drive')}
			</h3>
			
			{#if uploadType === 'local'}
				<!-- Local Upload UI -->
				<div class="mb-4">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.t('Select document')}
					</label>
					<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-md p-4 text-center cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
						<input type="file" class="hidden" id="document-upload" accept=".txt,.md,.pdf,.doc,.docx" />
						<label for="document-upload" class="cursor-pointer">
							<DocumentIcon className="w-8 h-8 mx-auto mb-2 text-gray-400" />
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{$i18n.t('Click to browse or drag and drop')}
							</p>
							<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
								{$i18n.t('Supported formats: PDF, TXT, MD, DOC, DOCX')}
							</p>
						</label>
					</div>
				</div>
				
				<div class="mb-4">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.t('Category')}
					</label>
					<select class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
						{#each categories.filter(c => c.value !== 'all') as category}
							<option value={category.value}>{$i18n.t(category.label)}</option>
						{/each}
					</select>
				</div>
			{:else}
				<!-- Google Drive Import UI -->
				<div class="mb-4 text-center">
					<svg class="w-12 h-12 mx-auto mb-3 text-green-600" viewBox="0 0 24 24" fill="currentColor">
						<path d="M14.9 9.6L9 3.8l1.8-3.1c.2-.2.5-.2.8 0l8.5 14.6H24l-9.1-5.7z" />
						<path d="M9 3.8L2.1 15.3 0 18.4l3.7 2.3c.2.1.5.1.7-.1l5.4-9.1L9 3.8z" />
						<path d="M14.9 20.7c.2.3.5.3.7.1l3.7-2.3-1.3-2.3H8.9L3.8 20.7h11.1z" />
					</svg>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
						{$i18n.t('Click the button below to open Google Drive and select a document to import. Only text-based documents are supported.')}
					</p>
					<div class="mb-4">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Category')}
						</label>
						<select class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
							{#each categories.filter(c => c.value !== 'all') as category}
								<option value={category.value}>{$i18n.t(category.label)}</option>
							{/each}
						</select>
					</div>
				</div>
			{/if}

			<div class="flex justify-end space-x-2">
				<button
					on:click={() => showUploadModal = false}
					class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					on:click={() => {
						if (uploadType === 'google-drive') {
							handleGoogleDriveImport();
						} else {
							// Handle local file upload
							showUploadModal = false;
							dispatch('documentUpload');
						}
					}}
					class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md"
				>
					{uploadType === 'local' ? $i18n.t('Upload') : $i18n.t('Import')}
				</button>
			</div>
		</div>
	</div>
{/if}

