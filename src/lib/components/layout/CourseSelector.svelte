<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { user } from '$lib/stores';
	
	const i18n = getContext('i18n');
	
	let courses = [];
	let selectedCourse = null;
	let isOpen = false;
	let loading = true;
	
	onMount(async () => {
		// For now, we'll just simulate loading courses
		// In a real implementation, you would fetch courses from an API
		await new Promise(resolve => setTimeout(resolve, 1000));
		
		// Simulate some courses for demo
		if ($user?.role === 'teacher' || $user?.role === 'admin') {
			courses = [
				{ id: 1, name: 'Sample Course 1', role: 'teacher' },
				{ id: 2, name: 'Sample Course 2', role: 'teacher' }
			];
		} else if ($user?.role === 'student') {
			courses = [
				{ id: 1, name: 'Enrolled Course 1', role: 'student' },
				{ id: 2, name: 'Enrolled Course 2', role: 'student' }
			];
		}
		
		if (courses.length > 0) {
			selectedCourse = courses[0];
		}
		
		loading = false;
	});
	
	const handleCourseSelect = (course) => {
		selectedCourse = course;
		isOpen = false;
	};
	
	const handleCreateCourse = () => {
		// Navigate to course creation
		isOpen = false;
	};
</script>

<div class="px-1.5 mb-3">
	<div class="relative">
		<button
			class="w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg
			       bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700
			       text-gray-700 dark:text-gray-300 transition-colors"
			on:click={() => isOpen = !isOpen}
			disabled={loading}
		>
			<div class="flex items-center space-x-2 flex-1 min-w-0">
				<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
				</svg>
				<span class="truncate">
					{#if loading}
						{$i18n.t('Loading courses...')}
					{:else if selectedCourse}
						{selectedCourse.name}
					{:else if courses.length === 0}
						{$i18n.t('No courses')}
					{:else}
						{$i18n.t('Select course')}
					{/if}
				</span>
			</div>
			{#if !loading}
				<svg class="w-4 h-4 transition-transform {isOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
				</svg>
			{/if}
		</button>

		{#if isOpen && !loading}
			<div class="absolute top-full left-0 right-0 mt-1 z-50 
			           bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
			           rounded-lg shadow-lg max-h-64 overflow-y-auto">
				
				{#if courses.length === 0}
					<div class="px-3 py-6 text-center text-gray-500 dark:text-gray-400 text-sm">
						<svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
						</svg>
						<p>{$i18n.t('No courses available')}</p>
						{#if $user?.role === 'teacher' || $user?.role === 'admin'}
							<button
								class="mt-2 text-blue-500 hover:text-blue-600 text-xs font-medium flex items-center justify-center space-x-1"
								on:click={handleCreateCourse}
							>
								<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
								</svg>
								<span>{$i18n.t('Create course')}</span>
							</button>
						{/if}
					</div>
				{:else}
					{#each courses as course}
						<button
							class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700
							       flex items-center space-x-2 text-sm
							       {selectedCourse?.id === course.id ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}"
							on:click={() => handleCourseSelect(course)}
						>
							<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
							</svg>
							<span class="truncate">{course.name}</span>
						</button>
					{/each}
					
					{#if $user?.role === 'teacher' || $user?.role === 'admin'}
						<div class="border-t border-gray-200 dark:border-gray-700 mt-1">
							<button
								class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700
								       flex items-center space-x-2 text-sm text-blue-500 hover:text-blue-600"
								on:click={handleCreateCourse}
							>
								<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
								</svg>
								<span>{$i18n.t('Create new course')}</span>
							</button>
						</div>
					{/if}
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- Click outside to close -->
{#if isOpen}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed inset-0 z-40"
		on:click={() => isOpen = false}
	></div>
{/if}