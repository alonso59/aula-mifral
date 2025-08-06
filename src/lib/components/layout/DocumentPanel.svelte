<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user, showDocumentPanel, selectedCourse } from '$lib/stores';
	import { getSessionUser } from '$lib/apis/auths';
	import { getCourseDocuments } from '$lib/apis/courses';
	import DocumentList from './DocumentPanel/DocumentList.svelte';
	import CourseInfo from './DocumentPanel/CourseInfo.svelte';
	import StudentSubmissions from './DocumentPanel/StudentSubmissions.svelte';
	import { fade, fly } from 'svelte/transition';

	const i18n = getContext('i18n');

	let documents = [];
	let courseData = null;

	// Role-based panel visibility
	$: canViewDocuments = $user?.role === 'teacher' || $user?.role === 'student' || $user?.role === 'admin' || $user?.role === 'user';
	$: canManageDocuments = $user?.role === 'teacher' || $user?.role === 'admin';
	$: canSubmitCode = $user?.role === 'student';
	
	// Reactive loading when course changes
	$: if ($selectedCourse && canViewDocuments) {
		loadDocuments();
		courseData = $selectedCourse;
	}
	
	$: {
		console.log('DocumentPanel - User role:', $user?.role);
		console.log('DocumentPanel - Can view documents:', canViewDocuments);
		console.log('DocumentPanel - Show document panel:', $showDocumentPanel);
		console.log('DocumentPanel - Selected course:', $selectedCourse);
	}

	onMount(async () => {
		console.log('DocumentPanel - onMount executed');
		console.log('User role at mount:', $user?.role);
		console.log('showDocumentPanel at mount:', $showDocumentPanel);
		console.log('selectedCourse at mount:', $selectedCourse);
		
		// Load documents based on user role and selected course
		if (canViewDocuments && $selectedCourse) {
			await loadDocuments();
		}
	});

	const loadDocuments = async () => {
		if (!$selectedCourse) {
			documents = [];
			return;
		}

		try {
			const courseDocuments = await getCourseDocuments(localStorage.getItem('token'), $selectedCourse.id);
			documents = courseDocuments || [];
		} catch (error) {
			console.warn('Error loading documents (course API may not be implemented):', error);
			// Set empty documents as fallback to prevent further errors
			documents = [];
		}
	};

	const togglePanel = () => {
		showDocumentPanel.set(!$showDocumentPanel);
	};
</script>

{#if $showDocumentPanel && canViewDocuments}
	<div 
		class="flex-shrink-0 w-80 bg-white dark:bg-gray-850 border-r border-gray-200 dark:border-gray-700 h-full overflow-y-auto"
		transition:fly={{ x: 300, duration: 300 }}
	>
		<!-- Panel Header -->
		<div class="p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
					{$selectedCourse ? $selectedCourse.name : $i18n.t('Course Materials')}
				</h2>
				<button
					on:click={togglePanel}
					class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					title={$i18n.t('Hide panel')}
				>
					<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Panel Content -->
		<div class="flex flex-col h-full">
			<!-- Course Information Section -->
			<div class="p-4 border-b border-gray-200 dark:border-gray-700">
				<CourseInfo {courseData} />
			</div>

			<!-- Documents Section -->
			{#if canViewDocuments}
				<div class="flex-1 p-4">
					<DocumentList 
						{documents} 
						{canManageDocuments}
						on:documentSelected={(event) => {
							// Handle document selection
							console.log('Document selected:', event.detail);
						}}
						on:documentUpload={() => {
							loadDocuments();
						}}
					/>
				</div>
			{/if}

			<!-- Student Submissions Section (for teachers and admins) -->
			{#if $user?.role === 'teacher' || $user?.role === 'admin'}
				<div class="p-4 border-t border-gray-200 dark:border-gray-700">
					<StudentSubmissions />
				</div>
			{/if}

			<!-- Student Code Submission Area -->
			{#if canSubmitCode}
				<div class="p-4 border-t border-gray-200 dark:border-gray-700">
					<div class="space-y-3">
						<h3 class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Submit Code for Review')}
						</h3>
						<textarea
							class="w-full h-24 p-3 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							placeholder={$i18n.t('Paste your Verilog code here...')}
						></textarea>
						<button
							class="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
						>
							{$i18n.t('Submit for Review')}
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- Toggle Button (when panel is hidden) -->
{#if !$showDocumentPanel && canViewDocuments}
	<button
		on:click={togglePanel}
		class="fixed left-4 top-1/2 transform -translate-y-1/2 z-40 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-r-md shadow-lg transition-colors"
		title={$i18n.t('Show course materials')}
		transition:fade={{ duration: 200 }}
	>
		<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
		</svg>
	</button>
{/if}

<style>
	/* Custom scrollbar for the panel */
	.overflow-y-auto::-webkit-scrollbar {
		width: 6px;
	}
	
	.overflow-y-auto::-webkit-scrollbar-track {
		background: transparent;
	}
	
	.overflow-y-auto::-webkit-scrollbar-thumb {
		background-color: rgba(156, 163, 175, 0.5);
		border-radius: 3px;
	}
	
	.overflow-y-auto::-webkit-scrollbar-thumb:hover {
		background-color: rgba(156, 163, 175, 0.7);
	}
</style>

