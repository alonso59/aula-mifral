<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { selectedCourse, userCourses, user } from '$lib/stores';
	import { getUserCourses } from '$lib/apis/courses';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import type { Course } from '$lib/types/course';

	const i18n = getContext('i18n');

	let loading = false;

	onMount(async () => {
		await loadUserCourses();
	});

	const loadUserCourses = async () => {
		if (!$user) return;
		
		loading = true;
		try {
			const courses = await getUserCourses(localStorage.getItem('token'));
			userCourses.set(courses || []);
		} catch (error) {
			console.error('Failed to load user courses:', error);
			userCourses.set([]);
		} finally {
			loading = false;
		}
	};

	const selectCourse = (course: Course) => {
		selectedCourse.set(course);
		// Navigate to course-aware chat
		goto(`/course/${course.id}/chat`);
	};

	const createNewChat = () => {
		if ($selectedCourse) {
			goto(`/course/${$selectedCourse.id}/chat`);
		} else {
			goto('/');
		}
	};
</script>

<div class="course-selector px-4 py-4 border-b border-gray-200 dark:border-gray-700">
	<div class="flex items-center justify-between mb-3">
		<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">
			{$i18n.t('Course')}
		</h3>
		
		{#if $selectedCourse}
			<button
				on:click={createNewChat}
				class="px-1.5 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition-colors"
				title={$i18n.t('New Course Chat')}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-4">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-500"></div>
		</div>
	{:else if $userCourses.length === 0}
		<div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
			{$i18n.t('No courses available')}
		</div>
	{:else}
		<div class="space-y-2">
			{#if $selectedCourse}
				<div class="px-3 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 border-blue-300 bg-blue-50 dark:border-blue-600 dark:bg-blue-900">
					<div class="course-info">
						<h4 class="font-medium text-sm text-blue-900 dark:text-blue-100">{$selectedCourse.name}</h4>
						<p class="text-xs text-gray-500 dark:text-gray-400">
							{$selectedCourse.description || $i18n.t('No description')}
						</p>
					</div>
					<div class="course-actions">
						<button
							on:click={() => selectedCourse.set(null)}
							class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
							title={$i18n.t('Exit Course')}
						>
							{$i18n.t('Exit')}
						</button>
					</div>
				</div>
			{:else}
				<select
					class="w-full px-2 py-2 text-sm border border-gray-300 rounded-lg bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white"
					on:change={(e) => {
						const courseId = e.target.value;
						if (courseId) {
							const course = $userCourses.find(c => c.id === courseId);
							if (course) selectCourse(course);
						}
					}}
				>
					<option value="">{$i18n.t('Select a course...')}</option>
					{#each $userCourses as course}
						<option value={course.id}>{course.name}</option>
					{/each}
				</select>
			{/if}
		</div>
	{/if}
</div>

